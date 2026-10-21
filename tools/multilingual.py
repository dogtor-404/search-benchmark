#!/usr/bin/env python3
"""独立的第二轮运行、匿名判分和统计入口；复用第一轮工具与提示词。"""
import argparse,collections,concurrent.futures,datetime,fcntl,json,random,subprocess,sys,threading,uuid
from pathlib import Path
import bench,baseline,grade,resources,analyze,search_run,report
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256
from build_multilingual import LANGS,SEED
QFILE=ROOT/'questions/multilingual.jsonl'
INSTRUCTION=grade.INSTRUCTION+' 回答使用什么语言不影响对错；只看是否与标准答案或别名表达同一事实或实体。允许正确译名、音译和文字变体。'
def read(path):return json.loads(path.read_text())
def questions(phase):
 qs=load_jsonl(QFILE)
 count=collections.Counter(q['lang'] for q in qs)
 pilot_only=phase=='pilot' and count==collections.Counter({l:1 for l in LANGS})
 if not pilot_only and count!=collections.Counter({l:20 for l in LANGS}):raise BenchError('多语种配额不符')
 if len({q['id'] for q in qs})!=len(qs) or len({q['question'] for q in qs})!=len(qs):raise BenchError('题目重复')
 if any(q['review']['status']!='verified' or not q['source_urls'] for q in qs):raise BenchError('尚未审核的题目')
 if phase=='full' or pilot_only:return qs
 chosen=[]
 for lang in LANGS:
  pool=[q for q in qs if q['lang']==lang];random.Random(f'{SEED}:pilot:{lang}').shuffle(pool);chosen.append(pool[0])
 return chosen
def check_run(out,g,q,cfg):
 return baseline.validate_cached(out,g,q['id'],cfg) if cfg['groups'][g]['search']=='none' else search_run.validate_search_result(out,g,q,cfg)
def run(out,qs,cfg,phase,workers,timeout):
 (ROOT/'tmp').mkdir(exist_ok=True)
 with (ROOT/'tmp/run.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('已有基准作答运行器持锁') from None
  version=subprocess.check_output(['claude','--version'],text=True).strip()
  frozen={'phase':phase,'round':'multilingual','question_sha256':sha256(QFILE),'question_file':str(QFILE.relative_to(ROOT)),'config_sha256':sha256(bench.CONFIG),'config':cfg,'seed':SEED,'question_ids':[q['id'] for q in qs],'all_groups':list(cfg['groups']),'claude_code_version':version,'python_version':sys.version,'tool_sha256':{p.name:sha256(p) for p in [ROOT/'tools'/n for n in ['multilingual.py','bench.py','common.py','deepseek_search.py','search_budget.py','deepseek-search.json','native-search-settings.json','empty-mcp.json']]},'workers':workers,'search_prompt_unchanged':True,'max_search_calls':5,'fetch_allowed':False,'pilot_records_reused':False}
  if (out/'manifest.json').exists():
   old=read(out/'manifest.json')
   if any(old.get(k)!=v for k,v in frozen.items()):raise BenchError('冻结的配置、题库、CLI或运行工具发生变化，禁止混跑')
  else:write_json(out/'manifest.json',dict(frozen,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  stop=threading.Event();printing=threading.Lock()
  def group(g):
   try:
    for q in qs:
     if stop.is_set():return
     p=out/'runs'/g/(q['id']+'.json')
     if p.exists():check_run(out,g,q,cfg);continue
     audit=out/'audit'/g/q['id']/'dispatch.json';dispatch={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':workers};write_json(audit,dispatch)
     r=bench.execute_one(q,g,cfg['groups'][g],cfg,out,timeout)
     write_json(audit,dict(dispatch,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=r['status'],run_sha256=sha256(p)))
     with printing:print(dumps({k:r[k] for k in ['group','question_id','status','elapsed_seconds']}),flush=True)
     if r['status']!='ok':raise BenchError('作答失败，停止派发；保留失败输出，先检查归档再续跑')
   except BaseException:stop.set();raise
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   futures=[pool.submit(group,g) for g in cfg['groups']]
   for f in concurrent.futures.as_completed(futures):f.result()
def prepare(out):
 m=read(out/'manifest.json');qs={q['id']:q for q in load_jsonl(QFILE)}
 if sha256(QFILE)!=m['question_sha256']:raise BenchError('题库已变')
 if (out/'grading/receipt.json').exists():return
 records=[];mapping={}
 for g in m['all_groups']:
  for qid in m['question_ids']:
   q=qs[qid];r=check_run(out,g,q,m['config']);oid=uuid.uuid4().hex
   records.append({'id':oid,'question':q['question'],'reference_answer':q['answer'],'aliases':q['aliases'],'candidate_answer':r['answer']})
   mapping[oid]={'group':g,'question_id':qid,'run_sha256':sha256(out/'runs'/g/(qid+'.json'))}
 random.Random(SEED).shuffle(records)
 write_text(out/'grading/blind.jsonl',''.join(dumps(r)+'\n' for r in records));write_json(out/'grading/mapping.json',mapping)
 write_json(out/'grading/receipt.json',{'blind_sha256':sha256(out/'grading/blind.jsonl'),'mapping_sha256':sha256(out/'grading/mapping.json'),'instruction':INSTRUCTION,'schema':grade.SCHEMA})
 print(dumps({'blind_records':len(records)}))
def majority(votes):
 counts=collections.Counter(votes)
 return next((v for v in ['correct','incorrect'] if counts[v]>=2),None)
def resolve(out):
 receipt=read(out/'grading/receipt.json');mapping=read(out/'grading/mapping.json');blind={r['id']:r for r in load_jsonl(out/'grading/blind.jsonl')}
 if receipt['blind_sha256']!=sha256(out/'grading/blind.jsonl') or receipt['mapping_sha256']!=sha256(out/'grading/mapping.json'):raise BenchError('匿名材料变化')
 judges={}
 for name in ['claude','deepseek','independent']:
  rows=load_jsonl(out/'jsonl/grades'/(name+'.jsonl'));index={r['id']:r for r in rows}
  if len(index)!=len(rows) or set(index)!=set(mapping):raise BenchError('判分缺失、重复或包含无关ID：'+name)
  for oid,row in index.items():
   if row['verdict'] not in ['correct','incorrect','uncertain'] or not row.get('reason'):raise BenchError('判分格式无效')
   if name!='independent' and row['raw_sha256']!=sha256(out/'grading/raw'/name/(oid+'.jsonl')):raise BenchError('判分原文变化')
  judges[name]=index
 third=read(out/'grading/independent-receipt.json')
 if third['source_blind_sha256']!=sha256(out/'grading/blind.jsonl') or third['review_sha256']!=sha256(out/'jsonl/grades/independent.jsonl'):raise BenchError('第三票凭据不符')
 qs={q['id']:q for q in load_jsonl(QFILE)};resolved=[];pending=[]
 for oid,m in mapping.items():
  if sha256(out/'runs'/m['group']/(m['question_id']+'.json'))!=m['run_sha256']:raise BenchError('作答材料变化')
  votes={name:rows[oid]['verdict'] for name,rows in judges.items()};v=majority(votes.values())
  if v:resolved.append(dict(m,id=oid,correct=v=='correct',votes=votes,method='ai_majority',human=False))
  else:pending.append(dict(blind[oid],judges={name:rows[oid] for name,rows in judges.items()},source_urls=qs[m['question_id']]['source_urls']))
 write_text(out/'grading/majority-resolved.jsonl',''.join(dumps(r)+'\n' for r in resolved));write_text(out/'grading/majority-needs-review.jsonl',''.join(dumps(r)+'\n' for r in pending))
 return resolved,pending
def build_report(out):
 resolved,pending=resolve(out);m=read(out/'manifest.json');cfg=m['config'];ids=m['question_ids'];gs=m['all_groups'];qs={q['id']:q for q in load_jsonl(QFILE)};table={(r['group'],r['question_id']):int(r['correct']) for r in resolved};scores=report.group_scores(resolved,ids,gs)
 resource=resources.run(out);rr={(g,q):check_run(out,g,qs[q],cfg) for g in gs for q in ids}
 summary={'phase':m['phase'],'n_questions':len(ids),'runs':len(rr),'pending':len(pending),'groups':{},'by_language':{},'comparisons':{},'lifts':{},'exploratory_contrasts':{}}
 for g in gs:
  runs=[rr[g,q] for q in ids];times=[r['elapsed_seconds'] for r in runs];hits=[analyze.source_hit(qs[q],rr[g,q]) for q in ids] if cfg['groups'][g]['search']!='none' else [];observed=[h for h in hits if h is not None]
  summary['groups'][g]=dict(scores[g],mean_seconds=sum(times)/len(times),median_seconds=__import__('statistics').median(times),p90_seconds=report.percentile90(times),mean_search_calls=sum(r['search_calls'] for r in runs)/len(runs),search_cost_usd=sum(r['search_cost_usd'] for r in runs),reported_model_nominal_usd=sum(r.get('reported_cost_usd') or 0 for r in runs),source_hit_at5=sum(observed)/len(observed) if observed else None,source_observable_n=len(observed),resources=resource[g])
 for lang in LANGS:
  lids=[q for q in ids if qs[q]['lang']==lang];summary['by_language'][lang]=report.group_scores([r for r in resolved if r['question_id'] in lids],lids,gs)
 for a,b in [('A','B'),('A_prime','B_prime')]:
  complete=[q for q in ids if (a,q) in table and (b,q) in table];vals=[table[b,q]-table[a,q] for q in complete]
  summary['comparisons'][a+'__'+b]={'difference_b_minus_a_bounds':report.contrast_bounds(table,ids,[(b,1),(a,-1)]),'complete_n':len(complete),'conditional_mcnemar':analyze.mcnemar([table[a,q] for q in complete],[table[b,q] for q in complete]),'conditional_bootstrap':analyze.bootstrap(vals,seed=SEED) if vals else None}
 for g,b in report.BASE.items():summary['lifts'][g]={'baseline':b,'accuracy_lift_bounds':report.contrast_bounds(table,ids,[(g,1),(b,-1)])}
 for label,terms in [('Sonnet提升-Flash提升',[('B',1),('0',-1),('D2',-1),('D0',1)]),('Opus提升-Pro提升',[('B_prime',1),('0_prime',-1),('D2_prime',-1),('D0_prime',1)]),('Claude DeepSeek搜索高档-中档',[('B_prime',1),('0_prime',-1),('B',-1),('0',1)]),('DeepSeek高档-中档',[('D2_prime',1),('D0_prime',-1),('D2',-1),('D0',1)]),('Claude原生搜索高档-中档',[('A_prime',1),('0_prime',-1),('A',-1),('0',1)])]:
  complete=[q for q in ids if all((g,q) in table for g,c in terms)];values=[sum(c*table[g,q] for g,c in terms) for q in complete]
  summary['exploratory_contrasts'][label]={'all_question_bounds':report.contrast_bounds(table,ids,terms),'conditional_bootstrap':analyze.bootstrap(values,seed=SEED) if values else None}
 lines=['# 多语种搜索：'+('六题试跑' if m['phase']=='pilot' else '120题正式测试'),'','十组使用相同原文题、原模型、原提示词；每题最多五次搜索、不抓网页。三位AI匿名判分，语言不影响对错；至少两张相同二元票才裁决。','',f'作答{len(rr)}份；待核{len(pending)}份。准确率范围是[已判对/N,(已判对+待核)/N]，不是置信区间。','','| 组 | 正确 | 错误 | 待核 | 准确率范围 | 平均秒 | 平均搜索次数 |','|---|---:|---:|---:|---:|---:|---:|']
 for g,s in summary['groups'].items():lines.append(f'| {g} | {s["correct"]} | {s["incorrect"]} | {s["pending"]} | {report.bounds_string(s["accuracy_bounds"])}% | {s["mean_seconds"]:.2f} | {s["mean_search_calls"]:.2f} |')
 lines+=['','两种搜索配对比较（DeepSeek减Claude）；有待核时检验仅适用于共同已判样本，不能当全体结论。']
 for key,v in summary['comparisons'].items():lines.append(f'- {key}：差值范围{report.bounds_string(v["difference_b_minus_a_bounds"])}个百分点；共同已判n={v["complete_n"]}，McNemar p={v["conditional_mcnemar"]["p_exact"]:.4f}。')
 lines+=['','每种语言正确数（待核单列；试跑每种仅1题，不作排名）：','','| 语言 | '+' | '.join(gs)+' |','|---|'+'---:|'*len(gs)]
 for lang,groups in summary['by_language'].items():lines.append('| '+lang+' | '+' | '.join(f'{s["correct"]}（待核{s["pending"]}）' for s in groups.values())+' |')
 search_fee=sum(s['search_cost_usd'] for s in summary['groups'].values());lines+=['',f'有效Search API估值合计 ${search_fee:.5f}。Claude名义API估值不等于订阅现金支出；DeepSeek模型实际扣款需账单核对。原始费用、耗时、返回字节量和token字段见summary.json与resources.json。来源URL命中率与网页语义正确率不同；原生搜索不暴露排名时记不可观测。','', '题目经过AI来源审核，非母语人工审核；部分原始MSQA来源为中文/英文，不能把这批题解释成纯本国语言索引覆盖实验。','']
 if m['phase']=='pilot':lines+=['试跑仅用于验证编码、工具和判分，六题不作胜负结论。全量120题是试跑题量的20倍：十组1200份作答、三位AI共3600票，保守Search费上限$1.80（4个DeepSeek搜索组×120题×5次×$0.00075），不含判分与模型费。正式运行须用户看过试跑后批准。']
 write_json(out/'analysis/summary.json',summary);write_text(out/'analysis/report.md','\n'.join(lines)+'\n');print(dumps({'report':str(out/'analysis/report.md'),'pending':len(pending)}))
def main():
 global QFILE
 p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','run','grade-prepare','grade-run','report']);p.add_argument('--phase',choices=['pilot','full'],default='pilot');p.add_argument('--execute',action='store_true');p.add_argument('--quota-confirmed',action='store_true');p.add_argument('--pilot-approved',action='store_true');p.add_argument('--workers',type=int,choices=[1,2,4],default=4);p.add_argument('--timeout',type=int,default=600);p.add_argument('--judge',choices=['claude','deepseek']);a=p.parse_args()
 if a.phase=='pilot' and (ROOT/'questions/multilingual-pilot.jsonl').exists():QFILE=ROOT/'questions/multilingual-pilot.jsonl'
 out=ROOT/('tmp/pilot-multilingual' if a.phase=='pilot' else 'tmp/archive-multilingual');cfg=read(bench.CONFIG);qs=questions(a.phase)
 if a.action=='plan' or a.action=='run' and not a.execute:print(dumps({'phase':a.phase,'runs':len(qs)*len(cfg['groups']),'question_ids':[q['id'] for q in qs],'out':str(out)}));return
 if a.action=='run':
  if not a.quota_confirmed:raise BenchError('需要既有额度授权')
  if a.phase=='full' and not a.pilot_approved:raise BenchError('用户看过本轮试跑与费用后才可批准全量')
  run(out,qs,cfg,a.phase,a.workers,a.timeout)
 elif a.action=='grade-prepare':prepare(out)
 elif a.action=='grade-run':
  if not a.judge:raise BenchError('缺判分员')
  grade.INSTRUCTION=INSTRUCTION;grade.run(out,a.judge,a.execute,a.quota_confirmed,a.timeout)
 else:build_report(out)
if __name__=='__main__':
 try:main()
 except (BenchError,FileNotFoundError,subprocess.TimeoutExpired) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
