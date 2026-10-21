#!/usr/bin/env python3
"""用户授权的独立AI单票报告；保留冻结作答文件，复用原统计公式。"""
import collections,datetime,json,sys
from pathlib import Path
from unittest.mock import patch
import multilingual as m,multilingual_report as old,report as first
from common import ROOT,BenchError,load_jsonl,sha256,write_json,write_text,dumps
OUT=ROOT/'tmp/archive-multilingual'

def resolve_single(out):
 policy=m.read(out/'grading/policy.json');rec=m.read(out/'grading/receipt.json');third=m.read(out/'grading/independent-receipt.json')
 if policy['method']!='single_independent_ai_live_blind' or policy['api_judges_enabled']!=[]:raise BenchError('非用户授权的独立单票策略')
 blind=load_jsonl(out/'grading/blind.jsonl');mapping=m.read(out/'grading/mapping.json');rows=load_jsonl(out/'jsonl/grades/independent.jsonl');index={r['id']:r for r in rows}
 if not rec['source_complete'] or len(blind)!=1200 or len(mapping)!=1200 or len(rows)!=1200 or len(index)!=1200 or {r['id'] for r in blind}!=set(mapping) or set(index)!=set(mapping):raise BenchError('正式匿名评分覆盖不足')
 if rec['blind_sha256']!=sha256(out/'grading/blind.jsonl') or rec['mapping_sha256']!=sha256(out/'grading/mapping.json') or third['source_blind_sha256']!=rec['blind_sha256'] or third['review_sha256']!=sha256(out/'jsonl/grades/independent.jsonl') or third.get('votes_per_answer')!=1 or not third.get('complete'):raise BenchError('单票凭据不符')
 inputs=m.read(out/'grading/independent-input/receipt.json');combined=[];original_combined=[]
 if not inputs['source_complete'] or inputs['source_blind_sha256']!=rec['blind_sha256']:raise BenchError('分批来源不是完整最终匿名材料')
 for part in inputs['parts']:
  source=out/part['path'];p=out/'grading/independent-output'/source.name;proof=m.read(p.with_suffix('.receipt.json'));batch=load_jsonl(p)
  if part['sha256']!=sha256(source) or proof['input_sha256']!=sha256(source) or proof['output_sha256']!=sha256(p) or proof['records']!=len(batch):raise BenchError('独立批次原文凭据不符')
  original=load_jsonl(source)
  if len({r['id'] for r in batch})!=len(batch) or {r['id'] for r in batch}!={r['id'] for r in original}:raise BenchError('独立批次ID覆盖不符')
  combined+=batch;original_combined+=original
 if original_combined!=blind:raise BenchError('匿名分批与完整匿名材料不同')
 if combined!=rows:raise BenchError('合并评分与独立批次原文不符')
 qs={q['id']:q for q in load_jsonl(m.QFILE)};resolved=[];pending=[];blind_index={r['id']:r for r in blind}
 for oid,meta in mapping.items():
  if sha256(out/'runs'/meta['group']/(meta['question_id']+'.json'))!=meta['run_sha256']:raise BenchError('已评分作答变化')
  row=index[oid];v=row['verdict']
  if v not in ['correct','incorrect','uncertain'] or not isinstance(row.get('reason'),str) or not row['reason'].strip():raise BenchError('独立评分格式无效')
  if v=='uncertain':pending.append(dict(blind_index[oid],judges={'independent':row},source_urls=qs[meta['question_id']]['source_urls']))
  else:resolved.append(dict(meta,id=oid,correct=v=='correct',votes={'independent':v},method='independent_ai_single',human=False))
 write_text(out/'grading/independent-resolved.jsonl',''.join(dumps(r)+'\n' for r in resolved));write_text(out/'grading/independent-needs-review.jsonl',''.join(dumps(r)+'\n' for r in pending))
 return resolved,pending

def price_estimate(summary):
 rates={'D0':(.15,.003,.60),'D2':(.15,.003,.60),'D0_prime':(.66,.022,1.98),'D2_prime':(.66,.022,1.98)};groups={};total=0.0
 for g,(miss,hit,output) in rates.items():
  r=summary['groups'][g]['resources'];n=r['n'];value=n*(r['mean_main_reported_input_tokens']*miss+r['mean_main_cache_read_tokens']*hit+r['mean_main_output_tokens']*output)/1e6;groups[g]=value;total+=value
 return {'source':'https://api-docs.deepseek.com/quick_start/pricing/?model_version=DeepSeek-V4-Pro-0813','rates_retrieved_on':'2026-10-21','currency':'USD','model_estimate_all_offpeak':total,'model_estimate_all_peak':total*2,'model_offpeak_by_group':groups,'api_judging_cost_usd':0,'note':'reported input暂按未缓存输入，cacheRead另按命中价；兼容接口缓存映射未核实，可能重叠。峰谷端点只描述同一用量在两种单价下的估值，不是账单或硬上限。现有Claude/Codex订阅费、无效次模型用量、服务端未上报内部用量另计。'}

def outside_peak_clock(start,end):
 zone=datetime.timezone(datetime.timedelta(hours=8));a=datetime.datetime.fromisoformat(start).astimezone(zone);b=datetime.datetime.fromisoformat(end).astimezone(zone)
 if b<a:raise BenchError('调用时段倒置')
 if a.date()!=b.date():return False
 # 保守地只认每天都明确处于低峰的钟点，不猜测假期；False表示不能据此证明低峰。
 return b.time()<datetime.time(9) or a.time()>=datetime.time(18) or (a.time()>=datetime.time(12) and b.time()<datetime.time(14))

def observed_tariff(out,summary,invalid):
 periods=[];missing=[];invalid_model=0;rates={'deepseek-flash':(.15,.003,.60),'deepseek-v4-pro':(.66,.022,1.98)}
 for g in ['D0','D2','D0_prime','D2_prime']:
  for qid in summary['question_ids']:
   p=out/'audit'/g/qid/'dispatch.json';r=m.read(p)
   if not r.get('started_at') or not r.get('finished_at'):missing.append(str(p.relative_to(out)));continue
   periods.append({'source':str(p.relative_to(out)),'started_at':r['started_at'],'finished_at':r['finished_at'],'sha256':sha256(p)})
 manifest=m.read(out/'manifest.json')
 for attempt in invalid:
  group=manifest['config']['groups'][attempt['group']]
  if group['provider']!='deepseek':continue
  parent=(out/attempt['review']).parent;review=m.read(parent/'review.json');usage=review.get('model_usage_from_raw_final')
  if usage is None:
   events=[json.loads(line) for line in (parent/'raw.jsonl').read_text().splitlines() if line.strip()];usage=next((e.get('modelUsage') for e in reversed(events) if e.get('type')=='result'),None)
  model=group['model'];u=(usage or {}).get(model)
  if u is None:missing.append(str(parent.relative_to(out))+'/modelUsage');continue
  miss,hit,output=rates[model];value=((u['inputTokens']+u['cacheCreationInputTokens'])*miss+u['cacheReadInputTokens']*hit+u['outputTokens']*output)/1e6;invalid_model+=value;attempt['model_offpeak_tariff_proxy_usd']=value
  p=parent/'audit/dispatch.json';r=m.read(p)
  if not r.get('started_at') or not r.get('finished_at'):missing.append(str(p.relative_to(out)));continue
  periods.append({'source':str(p.relative_to(out)),'started_at':r['started_at'],'finished_at':r['finished_at'],'sha256':sha256(p)})
 known_low=not missing and all(outside_peak_clock(p['started_at'],p['finished_at']) for p in periods);fees=summary['costs']['valid_search_estimate_usd']+summary['costs']['invalid_search_estimate_usd'];valid_model=summary['costs']['tariff_estimate']['model_estimate_all_offpeak'];zone=datetime.timezone(datetime.timedelta(hours=8))
 return {'all_observed_model_intervals_provably_offpeak':known_low,'valid_model_answer_records':480,'invalid_model_tariff_proxy_all_offpeak_usd':invalid_model,'model_plus_search_proxy_usd_at_observed_times':valid_model+invalid_model+fees if known_low else None,'missing_proof':missing,'first_model_started_at_beijing':min(datetime.datetime.fromisoformat(p['started_at']).astimezone(zone).isoformat() for p in periods),'last_model_finished_at_beijing':max(datetime.datetime.fromisoformat(p['finished_at']).astimezone(zone).isoformat() for p in periods),'interval_proofs':periods,'note':'包含有效DeepSeek模型用量、可恢复的无效次DeepSeek模型用量和已确认成功Search估值；兼容缓存映射仍未核实，是公开单价用量估值，不是账户扣款或账单。'}

def paired_cases(out,manifest,qs,table):
 cases=[]
 for a,b in [('A','B'),('A_prime','B_prime')]:
  for qid in manifest['question_ids']:
   av=table.get((a,qid));bv=table.get((b,qid))
   if av==bv:continue
   case={'a':a,'b':b,'question_id':qid,'lang':qs[qid]['lang'],'question':qs[qid]['question'],'reference_answer':qs[qid]['answer'],'source_urls':qs[qid]['source_urls'],'runs':{}}
   for g,value in [(a,av),(b,bv)]:
    run=m.read(out/'runs'/g/(qid+'.json'));case['runs'][g]={'correct':value,'answer':run['answer'],'queries':[r.get('query') for r in run['searches']],'elapsed_seconds':run['elapsed_seconds'],'raw':run['raw']}
   cases.append(case)
 write_text(out/'analysis/paired-cases.jsonl',''.join(dumps(r)+'\n' for r in cases));chosen=[]
 for lang in m.LANGS:
  for side in ['a','b']:
   options=[r for r in cases if r['lang']==lang and r['runs'][r[side]]['correct']==1]
   if options and options[0] not in chosen:chosen.append(options[0])
 for r in cases:
  if len(chosen)>=12:break
  if r not in chosen:chosen.append(r)
 text=['# 同题搜索对照案例','','按语言与双方各自正确的方向选取，最多12例。只展示观察材料，不能从答错自动归因为索引缺失。完整差异见paired-cases.jsonl。']
 for r in chosen[:12]:
  text+=['','## '+r['question_id']+' / '+r['a']+' 对 '+r['b'],'','题目：'+r['question'],'','参考答案：'+r['reference_answer']]
  for g in [r['a'],r['b']]:
   v=r['runs'][g];label='待核' if v['correct'] is None else '正确' if v['correct'] else '错误';text+=['','### '+g+'：'+label,'','查询：'+'；'.join(x or '' for x in v['queries']),'',v['answer'],'',f'完整耗时{v["elapsed_seconds"]:.3f}秒；[原始输出](../{v["raw"]})。']
 write_text(out/'analysis/paired-cases.md','\n'.join(text)+'\n')

def build(out=OUT):
 manifest=m.read(out/'manifest.json');m.QFILE=ROOT/manifest['question_file']
 if sha256(m.QFILE)!=manifest['question_sha256']:raise BenchError('正式题库变化')
 # 原统计函数只在当前报告进程中接受单票裁决；冻结作答文件与多数票函数本身均不修改。
 with patch.object(m,'resolve',resolve_single):m.build_report(out)
 summary=m.read(out/'analysis/summary.json');summary['question_ids']=manifest['question_ids'];summary['grading_method']='independent_ai_single';summary['vote_records']=1200
 rows=load_jsonl(out/'grading/independent-resolved.jsonl');table={(r['group'],r['question_id']):int(r['correct']) for r in rows};qs={q['id']:q for q in load_jsonl(m.QFILE)}
 votes=load_jsonl(out/'jsonl/grades/independent.jsonl');summary['vote_counts']={'independent':dict(collections.Counter(r['verdict'] for r in votes))}
 for g,entry in summary['lifts'].items():
  b=entry['baseline'];values=[table[g,q]-table[b,q] for q in manifest['question_ids'] if (g,q) in table and (b,q) in table];entry['conditional_bootstrap']=m.analyze.bootstrap(values,seed=20261021) if values else None
 summary['cross_round']=old.cross_round(out,summary,qs,table)
 if summary['cross_round'].get('available'):summary['cross_round']['notes'].append('第一轮多模型多数票，本轮用户改为独立AI单票，评分口径也变化；跨轮差不能只解释为搜索表现变化。')
 invalid=[]
 for p in sorted((out/'failed-attempts').glob('*/*/*/review.json')):
  rv=m.read(p);ledger=p.parent/'audit/search.jsonl';items=load_jsonl(ledger) if ledger.exists() else [];invalid.append({'review':str(p.relative_to(out)),'group':rv.get('group'),'question_id':rv.get('question_id'),'billable_search_estimate':sum(bool(r.get('billable')) for r in items)})
 summary['costs']={'valid_search_estimate_usd':sum(r['search_cost_usd'] for r in summary['groups'].values()),'invalid_search_estimate_usd':sum(r['billable_search_estimate'] for r in invalid)*manifest['config']['search_price_usd'],'invalid_attempts':invalid,'tariff_estimate':price_estimate(summary),'api_judging_calls':0}
 costs=summary['costs'];fees=costs['valid_search_estimate_usd']+costs['invalid_search_estimate_usd'];costs['tariff_estimate']['model_plus_search_estimate_usd']=[costs['tariff_estimate']['model_estimate_all_offpeak']+fees,costs['tariff_estimate']['model_estimate_all_peak']+fees];costs['observed_tariff_estimate']=observed_tariff(out,summary,invalid)
 paired_cases(out,manifest,qs,table);write_json(out/'analysis/full-summary.json',summary)
 path=out/'analysis/report.md';text=path.read_text().replace('三位AI匿名判分，语言不影响对错；至少两张相同二元票才裁决。','正式轮按用户后续指示，由独立Codex AI单票盲评，边作答边匿名发布评分；语言不影响对错，不确定项保留待核。没有调用Claude或DeepSeek评分，也没有三票多数判定。').replace('每种语言正确数（待核单列；试跑每种仅1题，不作排名）','每种语言正确数（待核单列；每种20题，只能看很大差别）')
 text+='\n## 搜索相对同模型不搜索的提升\n\n条件bootstrap只使用共同已判题，95%区间按题重抽样10000次；完整120题的未决范围另列。\n\n| 搜索组 | 对照 | 提升范围pp | 条件n | 条件提升与95%区间pp |\n|---|---|---:|---:|---:|\n'
 for g,e in summary['lifts'].items():
  b=e['conditional_bootstrap'];v='—' if not b else f'{b["estimate"]*100:.1f} [{b["ci95"][0]*100:.1f}, {b["ci95"][1]*100:.1f}]';text+=f'| {g} | {e["baseline"]} | {first.bounds_string(e["accuracy_lift_bounds"])} | {b["n"] if b else 0} | {v} |\n'
 text+='\n## 搜索提升差与高低档对照\n\n| 对照 | 完整题集范围pp | 条件n | 条件差与95%区间pp |\n|---|---:|---:|---:|\n'
 for label,e in summary['exploratory_contrasts'].items():
  b=e['conditional_bootstrap'];v='—' if not b else f'{b["estimate"]*100:.1f} [{b["ci95"][0]*100:.1f}, {b["ci95"][1]*100:.1f}]';text+=f'| {label} | {first.bounds_string(e["all_question_bounds"])} | {b["n"] if b else 0} | {v} |\n'
 text+='\n配对搜索正确率差（DeepSeek减Claude）的条件bootstrap：\n\n'
 for label,e in summary['comparisons'].items():
  b=e['conditional_bootstrap']
  if b:text+=f'- {label}：n={b["n"]}，差{b["estimate"]*100:.1f}pp，95%区间[{b["ci95"][0]*100:.1f}, {b["ci95"][1]*100:.1f}]pp。'+('看不出区别。' if b['ci95'][0]<=0<=b['ci95'][1] else '')+'\n'
 text+='\n## 评分方式与费用\n\n正式轮1200份答案、1200张独立AI评分票，每份仅一票。'+dumps(summary['vote_counts']['independent'])+'。盲评agent只获得匿名题目、参考答案、别名和候选回答；不读分组、运行过程或其他评分，不联网。1200个唯一ID与全部分批原文散列已核验。不确定项保留来源URL，见[待核列表](../grading/independent-needs-review.jsonl)。单票没有多模型一致性保障。六题试跑仍是原三票方案，不能直接把试跑分数变化当性能变化。\n\n'
 tariff=costs['tariff_estimate'];low,high=tariff['model_plus_search_estimate_usd'];text+=f'有效DeepSeek Search估值${costs["valid_search_estimate_usd"]:.5f}；归档无效次成功Search另估${costs["invalid_search_estimate_usd"]:.5f}。正式轮API评分调用为0。按实测有效作答token与[DeepSeek官方峰谷单价]({tariff["source"]})估算，模型与上述Search合计约${low:.2f}–{high:.2f}；这是同一用量全部按低峰或高峰价的估值，不是已扣款或硬上限。{tariff["note"]}CLI名义API估值不能当作现金支出。\n'
 observed=costs['observed_tariff_estimate']
 if observed['all_observed_model_intervals_provably_offpeak']:
  text+=f'\n本轮480份DeepSeek模型有效作答及可恢复的无效次模型调用，开始/结束均位于明确低峰钟点（北京时间{observed["first_model_started_at_beijing"]}至{observed["last_model_finished_at_beijing"]}）。因此按实际时段低峰单价，含已知无效次模型与成功Search的本轮估值为 **${observed["model_plus_search_proxy_usd_at_observed_times"]:.3f}**。无效次模型部分约${observed["invalid_model_tariff_proxy_all_offpeak_usd"]:.4f}已计入此数；仍不是账单，兼容缓存映射等限制不变。\n'
 text+='\n## 返回资料量与token\n\n| 组 | 每题返回KB | 每次搜索返回KB | 平均主模型reported input | 平均主模型output |\n|---|---:|---:|---:|---:|\n'
 for g,e in summary['groups'].items():
  r=e['resources'];call='—' if r['mean_returned_utf8_bytes_per_call'] is None else f'{r["mean_returned_utf8_bytes_per_call"]/1000:.2f}';text+=f'| {g} | {r["mean_returned_utf8_bytes_per_question"]/1000:.2f} | {call} | {r["mean_main_reported_input_tokens"]:.0f} | {r["mean_main_output_tokens"]:.0f} |\n'
 text+='\nKB=1000个UTF-8字节，是成功搜索tool_result中模型可见文本，每调用ID计一次；不是HTTP流量或去重资料量。缓存、辅助模型等原字段见resources.json，DeepSeek兼容缓存合计口径未知，不强行相加。output可能包含思考，不等于可见答案长度。\n'
 cross=summary['cross_round'];text+='\n## 与第一轮中文、英文的探索性对照\n\n两轮题集、语言、难度和评分方式同时变化：第一轮多模型多数，本轮独立AI单票。下表不能单独解释为小语种索引覆盖效果。\n'
 if cross['available']:
  text+='\n| 模型配对 | 第一轮语言/n | 第一轮DS减Claude范围pp | 本轮六语种/n | 本轮范围pp | 跨轮差值变化范围pp |\n|---|---|---:|---|---:|---:|\n'
  for pair,langs in cross['comparisons'].items():
   for lang,v in langs.items():text+=f'| {pair} | {lang}/{v["first_n"]} | {first.bounds_string(v["first_deepseek_minus_claude_bounds"])} | 六语种/{v["second_n"]} | {first.bounds_string(v["second_deepseek_minus_claude_bounds"])} | {first.bounds_string(v["second_minus_first_bounds"])} |\n'
 else:text+=cross['reason']+'。\n'
 text+='\n未决项不当错题；条件bootstrap只用于共同已判题，未做多重比较校正。完整作答耗时含模型、搜索与本地开销，不能当纯搜索延迟。原生搜索含摘要且部分排名不可观测；只测Search、不Fetch。来源URL精确命中不是语义质量。AI来源审核与独立AI评分都不是母语人工复核。\n\n[最多12例同题对照](paired-cases.md)，[全部差异](paired-cases.jsonl)。\n'
 write_text(path,text)
 write_json(out/'analysis/completion-receipt.json',{'generated_at':datetime.datetime.now().astimezone().isoformat(),'answer_records':1200,'vote_records':1200,'grading_method':'independent_ai_single','resolved':len(rows),'pending':summary['pending'],'manifest_sha256':sha256(out/'manifest.json'),'policy_sha256':sha256(out/'grading/policy.json'),'tool_sha256':sha256(ROOT/'tools/multilingual_single_report.py'),'files':{str(p.relative_to(out)):sha256(p) for p in [path,out/'analysis/full-summary.json',out/'analysis/paired-cases.md',out/'analysis/paired-cases.jsonl',out/'grading/independent-receipt.json',out/'grading/independent-resolved.jsonl',out/'grading/independent-needs-review.jsonl']}})
 return summary

if __name__=='__main__':
 try:
  s=build();print(dumps({'report':str(OUT/'analysis/report.md'),'answers':1200,'votes':1200,'pending':s['pending']}))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('单票报告停止：'+str(e),file=sys.stderr);sys.exit(1)
