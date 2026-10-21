#!/usr/bin/env python3
"""完成第二轮独立报告、三票原文校验、跨轮探索性比较与对照案例。"""
import collections,datetime,json,random,statistics,sys
from pathlib import Path
import multilingual as m,report as first_report,bench
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256,parse_stream
OUT=ROOT/'tmp/archive-multilingual'
def read(path):return json.loads(path.read_text())
def cross_bootstrap(new,old,draws=10000,seed=20261021):
 if not new or not old:return None
 rng=random.Random(seed);vals=sorted(sum(rng.choice(new) for _ in new)/len(new)-sum(rng.choice(old) for _ in old)/len(old) for _ in range(draws))
 return {'estimate':statistics.mean(new)-statistics.mean(old),'ci95':[vals[int(draws*.025)],vals[int(draws*.975)]],'new_n':len(new),'old_n':len(old),'draws':draws,'seed':seed}
def bounds(table,ids,a,b):return first_report.contrast_bounds(table,ids,[(b,1),(a,-1)])
def validate_votes(out):
 mf=read(out/'manifest.json');receipt=read(out/'grading/receipt.json');blind=load_jsonl(out/'grading/blind.jsonl');ids={r['id'] for r in blind}
 if len(ids)!=len(blind) or receipt['blind_sha256']!=sha256(out/'grading/blind.jsonl') or receipt['mapping_sha256']!=sha256(out/'grading/mapping.json'):raise BenchError('匿名判分材料不完整或已变化')
 hashes={};counts={}
 for judge in ['claude','deepseek']:
  rows=load_jsonl(out/'jsonl/grades'/(judge+'.jsonl'))
  if len(rows)!=len(ids) or {r['id'] for r in rows}!=ids:raise BenchError('API评分缺失或重复')
  for r in rows:
   raw=out/'grading/raw'/judge/(r['id']+'.jsonl')
   if sha256(raw)!=r['raw_sha256']:raise BenchError('API评分原文散列不同')
   events,final=parse_stream(raw.read_text(),allow_structured=True);bench.verify_events(events,{'search':'none','structured_output':True})
   if any(e.get('model')!=mf['config']['judges'][judge] for e in events if e.get('type')=='system' and e.get('subtype')=='init'):raise BenchError('API判分模型不同')
   value=final.get('structured_output') or json.loads(final['result'])
   if value!={k:r[k] for k in ['verdict','reason']}:raise BenchError('API评分记录与原文不同')
   hashes[str(raw.relative_to(out))]=sha256(raw)
  counts[judge]=dict(collections.Counter(r['verdict'] for r in rows))
 third=read(out/'grading/independent-receipt.json');rows=load_jsonl(out/'jsonl/grades/independent.jsonl')
 if len(rows)!=len(ids) or {r['id'] for r in rows}!=ids or third['source_blind_sha256']!=sha256(out/'grading/blind.jsonl') or third['review_sha256']!=sha256(out/'jsonl/grades/independent.jsonl'):raise BenchError('第三票覆盖或散列不同')
 counts['independent']=dict(collections.Counter(r['verdict'] for r in rows))
 write_json(out/'grading/validation-receipt.json',{'api_grade_raws_verified':len(hashes),'all_vote_records':len(ids)*3,'source_blind_sha256':sha256(out/'grading/blind.jsonl'),'file_sha256':hashes,'votes':counts})
 return counts
def cross_round(out,summary,qs,table):
 first=ROOT/'tmp/archive';fp=first/'grading/majority-resolved.jsonl';qfile=ROOT/'questions/questions.jsonl'
 if not fp.exists():return {'available':False,'reason':'第一轮多数票材料当前不在tmp/archive，未猜测结果位置'}
 mf=read(first/'manifest.json');oldqs={q['id']:q for q in load_jsonl(qfile)}
 if mf['question_sha256']!=sha256(qfile):raise BenchError('第一轮题库已漂移，不能引用旧结果')
 receipt_path=first/'analysis/report-receipt.json'
 if receipt_path.exists():
  rec=read(receipt_path)
  for name,digest in rec.get('files',{}).items():
   if sha256(first/'analysis'/name)!=digest:raise BenchError('第一轮报告与完成凭据不同')
 old={(r['group'],r['question_id']):int(r['correct']) for r in load_jsonl(fp)};result={'available':True,'source_majority_sha256':sha256(fp),'source_question_sha256':sha256(qfile),'comparisons':{}}
 for a,b in [('A','B'),('A_prime','B_prime')]:
  key=a+'__'+b;newids=summary['question_ids'];newbounds=bounds(table,newids,a,b);newcomplete=[q for q in newids if (a,q) in table and (b,q) in table];newvalues=[table[b,q]-table[a,q] for q in newcomplete];result['comparisons'][key]={}
  for lang in ['zh','en']:
   oldids=[qid for qid in mf['question_ids'] if oldqs[qid]['lang']==lang];ob=bounds(old,oldids,a,b);common=[q for q in oldids if (a,q) in old and (b,q) in old];values=[old[b,q]-old[a,q] for q in common]
   result['comparisons'][key][lang]={'first_n':len(oldids),'second_n':len(newids),'first_deepseek_minus_claude_bounds':ob,'second_deepseek_minus_claude_bounds':newbounds,'second_minus_first_bounds':[newbounds[0]-ob[1],newbounds[1]-ob[0]],'conditional_cross_bootstrap':cross_bootstrap(newvalues,values)}
 result['notes']=['跨轮是不同题集之间的探索性差异比较，语言、题型、难度和筛选条件同时变化，不能把变化单独归因为语言索引覆盖。','bootstrap分别按第一轮题与第二轮题抽样；只有共同已判样本进入条件区间，完整题集另给未决识别范围。未做多重比较校正。']
 return result
def build(out=OUT):
 mf=read(out/'manifest.json');m.QFILE=ROOT/mf['question_file']
 if sha256(m.QFILE)!=mf['question_sha256']:raise BenchError('正式题库发生变化')
 votes=validate_votes(out);m.build_report(out);summary=read(out/'analysis/summary.json');summary['question_ids']=mf['question_ids'];qs={q['id']:q for q in load_jsonl(m.QFILE)};rows=load_jsonl(out/'grading/majority-resolved.jsonl');table={(r['group'],r['question_id']):int(r['correct']) for r in rows};blind={r['id']:r for r in load_jsonl(out/'grading/blind.jsonl')};mapping=read(out/'grading/mapping.json');judges={j:{r['id']:r for r in load_jsonl(out/'jsonl/grades'/(j+'.jsonl'))} for j in ['claude','deepseek','independent']}
 mixed=[]
 for oid,meta in mapping.items():
  vv={j:judges[j][oid]['verdict'] for j in judges}
  if len(set(vv.values()))>1:mixed.append(dict(meta,id=oid,question=blind[oid]['question'],reference_answer=blind[oid]['reference_answer'],candidate_answer=blind[oid]['candidate_answer'],votes={j:{k:judges[j][oid][k] for k in ['verdict','reason']} for j in judges},source_urls=qs[meta['question_id']]['source_urls']))
 write_text(out/'analysis/vote-disagreements.jsonl',''.join(dumps(r)+'\n' for r in mixed));summary['vote_counts']=votes;summary['vote_disagreements']=len(mixed)
 invalid=[]
 for p in sorted((out/'failed-attempts').glob('*/*/*/review.json')):
  rv=read(p);ledger=p.parent/'audit/search.jsonl';rr=load_jsonl(ledger) if ledger.exists() else []
  invalid.append({'review':str(p.relative_to(out)),'group':rv.get('group'),'question_id':rv.get('question_id'),'billable_search_estimate':sum(bool(r.get('billable')) for r in rr)})
 gradecost={j:sum(r.get('reported_cost_usd') or 0 for r in judges[j].values()) for j in ['claude','deepseek']};summary['costs']={'valid_search_estimate_usd':sum(r['search_cost_usd'] for r in summary['groups'].values()),'invalid_search_estimate_usd':sum(r['billable_search_estimate'] for r in invalid)*mf['config']['search_price_usd'],'invalid_attempts':invalid,'model_nominal_cli_estimate_usd':{g:r['reported_model_nominal_usd'] for g,r in summary['groups'].items()},'grade_nominal_cli_estimate_usd':gradecost,'cash_note':'CLI名义估值不是Max订阅现金支出；DeepSeek costBasis未知，模型实际费用需对账。Search按冻结单价与非空成功次估值。'}
 for g,entry in summary['lifts'].items():
  baseline=entry['baseline'];complete=[q for q in mf['question_ids'] if (g,q) in table and (baseline,q) in table];values=[table[g,q]-table[baseline,q] for q in complete]
  entry['conditional_bootstrap']=m.analyze.bootstrap(values,seed=20261021) if values else None
 cross=cross_round(out,summary,qs,table);summary['cross_round']=cross;write_json(out/'analysis/full-summary.json',summary)
 cases=[]
 for a,b in [('A','B'),('A_prime','B_prime')]:
  for qid in mf['question_ids']:
   av=table.get((a,qid));bv=table.get((b,qid))
   if av==bv:continue
   data={'a':a,'b':b,'question_id':qid,'lang':qs[qid]['lang'],'question':qs[qid]['question'],'reference_answer':qs[qid]['answer'],'source_urls':qs[qid]['source_urls'],'runs':{}}
   for g,value in [(a,av),(b,bv)]:
    run=read(out/'runs'/g/(qid+'.json'));data['runs'][g]={'correct':value,'answer':run['answer'],'queries':[s.get('query') for s in run['searches']],'elapsed_seconds':run['elapsed_seconds'],'search_calls':run['search_calls'],'raw':run['raw']}
   cases.append(data)
 write_text(out/'analysis/paired-cases.jsonl',''.join(dumps(r)+'\n' for r in cases))
 chosen=[]
 for lang in m.LANGS:
  for direction in ['a','b']:
   options=[r for r in cases if r['lang']==lang and r['runs'][r[direction]]['correct']==1]
   if options:chosen.append(options[0])
 for r in cases:
  if len(chosen)>=12:break
  if r not in chosen:chosen.append(r)
 text=['# 多语种搜索：同题对照案例','','按语言与双方各自答对的方向优先选取，最多12例；完整差异保存在paired-cases.jsonl。只展示查询、回答和最终评分，不从答错自动推断“没搜到”或“索引缺失”。']
 for r in chosen[:12]:
  text+=['','## '+r['question_id']+' / '+r['a']+' 对 '+r['b'],'','题目：'+r['question'],'','参考答案：'+r['reference_answer']]
  for g in [r['a'],r['b']]:
   value=r['runs'][g];label='待核' if value['correct'] is None else '正确' if value['correct'] else '错误';text+=['','### '+g+'：'+label,'','查询：'+'；'.join(q or '' for q in value['queries']),'',f'完整作答耗时{value["elapsed_seconds"]:.3f}秒，实际搜索{value["search_calls"]}次。','',value['answer'],'','[原始输出](../'+value['raw']+')。']
 write_text(out/'analysis/paired-cases.md','\n'.join(text)+'\n')
 reportpath=out/'analysis/report.md';text=reportpath.read_text().replace('每种语言正确数（待核单列；试跑每种仅1题，不作排名）','每种语言正确数（待核单列；每种20题，只看得出很大差别）')
 text+='\n\n## 搜索相对同模型不搜索的提升\n\n范围计入未决项的不确定性，条件bootstrap只使用比较两组均已判定的共同题；95%区间按题重抽样10000次。\n\n| 搜索组 | 对照 | 全120题提升范围pp | 条件n | 条件提升与95%区间pp |\n|---|---|---:|---:|---:|\n'
 for g,v in summary['lifts'].items():
  boot=v['conditional_bootstrap'];n=boot['n'] if boot else 0;estimate='—' if not boot else f'{boot["estimate"]*100:.1f} [{boot["ci95"][0]*100:.1f}, {boot["ci95"][1]*100:.1f}]';text+=f'| {g} | {v["baseline"]} | {first_report.bounds_string(v["accuracy_lift_bounds"])} | {n} | {estimate} |\n'
 text+='\n## 搜索提升差与高低档对照\n\n| 对照 | 全120题差值范围pp | 条件n | 条件差与95%区间pp |\n|---|---:|---:|---:|\n'
 for label,v in summary['exploratory_contrasts'].items():
  boot=v['conditional_bootstrap'];n=boot['n'] if boot else 0;estimate='—' if not boot else f'{boot["estimate"]*100:.1f} [{boot["ci95"][0]*100:.1f}, {boot["ci95"][1]*100:.1f}]';note='；看不出区别' if boot and boot['ci95'][0]<=0<=boot['ci95'][1] else '';text+=f'| {label} | {first_report.bounds_string(v["all_question_bounds"])} | {n} | {estimate}{note} |\n'
 text+='\n两种搜索在同一Claude模型下的配对bootstrap：\n'
 for label,v in summary['comparisons'].items():
  boot=v['conditional_bootstrap']
  if boot:text+=f'- {label}：共同已判n={boot["n"]}，DeepSeek减Claude为{boot["estimate"]*100:.1f}pp，95%区间[{boot["ci95"][0]*100:.1f}, {boot["ci95"][1]*100:.1f}]pp。'+('看不出区别。' if boot['ci95'][0]<=0<=boot['ci95'][1] else '')+'\n'
 text+='\n## 三票完整性与费用\n\n'+f'三位AI共{len(mapping)*3}票；{len(mapping)-len(mixed)}份三位票一致，{len(mixed)}份有分歧。完整分歧与理由见[vote-disagreements.jsonl](vote-disagreements.jsonl)。AI多数票不是母语人工复核。\n\n'
 text+='有效DeepSeek Search估值$'+f'{summary["costs"]["valid_search_estimate_usd"]:.5f}'+'；已归档无效次中成功Search另估$'+f'{summary["costs"]["invalid_search_estimate_usd"]:.5f}'+'，不包含模型与判分实际费用。DeepSeek兼容CLI名义价格基础未知，不能当实际现金扣款。各组实际搜索次数、模型报告费用及判分名义估值见[完整汇总](full-summary.json)。\n'
 text+='\n## 返回资料量与token\n\n| 组 | 每题平均返回KB | 每次搜索平均KB | 平均主模型报告input | 平均主模型output |\n|---|---:|---:|---:|---:|\n'
 for g,r in summary['groups'].items():
  v=r['resources'];percall='—' if v['mean_returned_utf8_bytes_per_call'] is None else f'{v["mean_returned_utf8_bytes_per_call"]/1000:.2f}';text+=f'| {g} | {v["mean_returned_utf8_bytes_per_question"]/1000:.2f} | {percall} | {v["mean_main_reported_input_tokens"]:.0f} | {v["mean_main_output_tokens"]:.0f} |\n'
 text+='\nKB=1000个UTF-8字节，统计成功工具返回的模型可见文本，每个调用ID只计一次；不是HTTP流量，也不保证代表去重的资料量。input字段只列CLI原报告，缓存字段与Claude累计输入、辅助模型用量见[resources.json](resources.json)。DeepSeek兼容缓存合计含义未明确，不强行相加；未报告的服务端摘要内部token不按0计算。\n'
 text+='\n## 与第一轮中文、英文对照\n\n'
 if cross['available']:
  text+='差值为“DeepSeek搜索减Claude搜索”。两轮使用不同题集，语言、题型、难度同时变化；下表描述观察到的差异，不能单独归因为小语种索引覆盖。\n\n| 模型配对 | 第一轮语言 / n | 第一轮差值范围pp | 本轮六语种 / n | 本轮差值范围pp | 跨轮差值变化范围pp |\n|---|---|---:|---|---:|---:|\n'
  for pair,langs in cross['comparisons'].items():
   for lang,v in langs.items():text+=f'| {pair} | {lang} / {v["first_n"]} | {first_report.bounds_string(v["first_deepseek_minus_claude_bounds"])} | 六语种 / {v["second_n"]} | {first_report.bounds_string(v["second_deepseek_minus_claude_bounds"])} | {first_report.bounds_string(v["second_minus_first_bounds"])} |\n'
  text+='\n未决项不当错题；条件bootstrap区间与完整题集的未决范围分别保存在full-summary.json。未做多重比较校正，第一轮数字与文件不改。\n'
 else:text+=cross['reason']+'。\n'
 text+='\n## 同题案例与局限\n\n[12例以内的双方对照](paired-cases.md)；[全部配对差异](paired-cases.jsonl)。题目经过AI来源审核，非母语人工审核；上游部分引用来自中文、英文。来源URL前五命中是精确URL指标，不等于语义检索质量。完整作答耗时包含模型、搜索、生成与本地开销，时段、缓存、输出长度和故障续跑会影响速度；不是纯搜索接口延迟。模型知识与搜索资料处理共同影响最终正确率。\n'
 write_text(reportpath,text)
 write_json(out/'analysis/completion-receipt.json',{'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'answer_records':1200,'vote_records':3600,'majority_resolved':len(rows),'pending':summary['pending'],'manifest_sha256':sha256(out/'manifest.json'),'tool_sha256':sha256(ROOT/'tools/multilingual_report.py'),'files':{str(p.relative_to(out)):sha256(p) for p in [reportpath,out/'analysis/full-summary.json',out/'analysis/paired-cases.md',out/'analysis/paired-cases.jsonl',out/'analysis/vote-disagreements.jsonl',out/'grading/validation-receipt.json']}})
 return summary
if __name__=='__main__':
 try:
  result=build();print(dumps({'report':str(OUT/'analysis/report.md'),'pending':result['pending'],'answer_records':1200,'vote_records':3600}))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
