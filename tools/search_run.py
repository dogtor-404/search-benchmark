#!/usr/bin/env python3
"""复用已冻结的400份不搜索基线，补跑六个搜索组的正式100题。"""
import argparse,concurrent.futures,datetime,fcntl,json,subprocess,sys,threading
from pathlib import Path
import baseline,bench,grade
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256,parse_stream,check_secret
OUT=ROOT/'tmp/archive';SOURCE=ROOT/'tmp/baseline'
SEARCH_GROUPS=['A','B','D2','A_prime','B_prime','D2_prime']

def read_json(path):return json.loads(path.read_text())
def validate_source(source,questions,cfg,version):
 m=read_json(source/'manifest.json');record=read_json(source/'baseline-record.json')
 if m['all_groups']!=baseline.GROUPS or m['question_ids']!=[q['id'] for q in questions]:raise BenchError('baseline 题目或分组不符。')
 if m['question_sha256']!=sha256(ROOT/'questions/questions.jsonl') or m['config_sha256']!=sha256(bench.CONFIG) or m['config']!=cfg or m['claude_code_version']!=version:raise BenchError('baseline 与当前题库、配置或 CLI 不一致。')
 if record['question_sha256']!=m['question_sha256'] or record['config_sha256']!=m['config_sha256']:raise BenchError('baseline 快照与复现清单不符。')
 for relative,digest in record['file_sha256'].items():
  path=source/relative
  if not path.is_file() or sha256(path)!=digest:raise BenchError('baseline 原始文件校验失败，拒绝复用。')
 reused={}
 for g in baseline.GROUPS:
  for q in questions:
   baseline.validate_cached(source,g,q['id'],cfg)
   reused[g+'/'+q['id']]={'run_sha256':sha256(source/'runs'/g/(q['id']+'.json')),'raw_sha256':sha256(source/'jsonl'/g/(q['id']+'.jsonl'))}
 return reused

def prepare(out,source,questions,cfg,version):
 if [g for g,v in cfg['groups'].items() if v['search']!='none']!=SEARCH_GROUPS:raise BenchError('搜索分组与既定六组不同。')
 reused=validate_source(source,questions,cfg,version)
 frozen={'phase':'full','question_sha256':sha256(ROOT/'questions/questions.jsonl'),'config_sha256':sha256(bench.CONFIG),'tool_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'tools').glob('*')) if p.suffix in ('.py','.json')},'python_version':sys.version,'claude_code_version':version,'config':cfg,'question_ids':[q['id'] for q in questions],'all_groups':list(cfg['groups']),'seed':cfg['seed'],'baseline_record_sha256':sha256(source/'baseline-record.json'),'baseline_manifest_sha256':sha256(source/'manifest.json'),'reused_baseline_runs':reused,'new_search_groups':SEARCH_GROUPS,'pilot_search_results_reused':False}
 path=out/'manifest.json'
 if path.exists():
  saved=read_json(path)
  if any(saved.get(k)!=v for k,v in frozen.items()):raise BenchError('正式运行配置或复用来源变化，拒绝混用。')
 else:write_json(path,dict(frozen,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 for g in baseline.GROUPS:
  for q in questions:
   for folder,suffix in [('runs','.json'),('jsonl','.jsonl')]:baseline.copy_checked(source/folder/g/(q['id']+suffix),out/folder/g/(q['id']+suffix))
 return len(reused)

def validate_search_result(out,g,q,cfg):
 r=read_json(out/'runs'/g/(q['id']+'.json'))
 if r.get('status')!='ok' or r.get('group')!=g or r.get('question_id')!=q['id'] or r.get('model')!=cfg['groups'][g]['model']:raise BenchError('已有搜索题失败或不匹配，须先检查并归档，不能覆盖。')
 aux=out/'audit'/g/q['id'];ledger=aux/'native-attempts.jsonl';native=load_jsonl(ledger) if cfg['groups'][g]['search']=='claude' and ledger.exists() else []
 allowed={x.get('tool_use_id') for x in native if x.get('status')=='budget_exhausted'}
 raw=out/'jsonl'/g/(q['id']+'.jsonl');text=raw.read_text();check_secret(text);events,final=parse_stream(text,allowed_budget_denial_ids=allowed);calls,results,observed=bench.verify_events(events,cfg['groups'][g]);actual,denied=bench.audit_searches(events,cfg['groups'][g],aux,results)
 if final['result']!=r['answer'] or len(calls)!=r['search_attempts'] or len(actual)!=r['search_calls'] or len(denied)!=r['search_budget_denials'] or observed!=r['tools']:raise BenchError('已有搜索原始输出与记录或审计不同。')
 return r

def run(out,source,questions,cfg,workers,timeout):
 (ROOT/'tmp').mkdir(exist_ok=True)
 with (ROOT/'tmp/run.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('已有作答运行器持有运行锁。') from None
  version=subprocess.check_output(['claude','--version'],text=True).strip();reused=prepare(out,source,questions,cfg,version)
  print(dumps({'reused_baseline_runs':reused,'new_search_runs':len(questions)*len(SEARCH_GROUPS),'workers':workers}),flush=True)
  stop=threading.Event();print_lock=threading.Lock()
  def one_group(g):
   try:
    for q in questions:
     if stop.is_set():return
     path=out/'runs'/g/(q['id']+'.json')
     if path.exists():validate_search_result(out,g,q,cfg);continue
     dispatch={'group':g,'question_id':q['id'],'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':workers}
     write_json(out/'audit'/g/q['id']/'dispatch.json',dispatch)
     result=bench.execute_one(q,g,cfg['groups'][g],cfg,out,timeout)
     dispatch.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=result['status'],run_sha256=sha256(path));write_json(out/'audit'/g/q['id']/'dispatch.json',dispatch)
     with print_lock:print(dumps({k:result[k] for k in ['group','question_id','status','elapsed_seconds']}),flush=True)
     if result['status']!='ok':raise BenchError('搜索作答失败，已停止启动后续题；在途题会保留输出。')
   except BaseException:stop.set();raise
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   futures=[pool.submit(one_group,g) for g in SEARCH_GROUPS]
   for future in concurrent.futures.as_completed(futures):future.result()
  print(dumps({'complete':True,'groups':len(cfg['groups']),'questions':len(questions),'reused_baseline_runs':reused}),flush=True)

def prepare_grades(out,source):
 if not (out/'grading/receipt.json').exists():grade.prepare(out)
 receipt=read_json(out/'grading/receipt.json');old_receipt=read_json(source/'grading/receipt.json')
 for target,rec in [(out,receipt),(source,old_receipt)]:
  if rec['blind_sha256']!=sha256(target/'grading/blind.jsonl') or rec['mapping_sha256']!=sha256(target/'grading/mapping.json'):raise BenchError('新旧匿名包校验失败。')
 if receipt['instruction']!=old_receipt['instruction'] or receipt['schema']!=old_receipt['schema']:raise BenchError('判分规则不同，不能复用。')
 mapping=read_json(out/'grading/mapping.json');oldmap=read_json(source/'grading/mapping.json');lookup={(m['group'],m['question_id']):oid for oid,m in oldmap.items()};blind={r['id']:r for r in load_jsonl(out/'grading/blind.jsonl')};oldblind={r['id']:r for r in load_jsonl(source/'grading/blind.jsonl')};counts={}
 for judge in ['claude','deepseek']:
  path=out/'jsonl/grades'/(judge+'.jsonl');rows=load_jsonl(path) if path.exists() else [];done={r['id']:r for r in rows}
  if len(done)!=len(rows):raise BenchError('正式判分 ID 重复。')
  oldgrades={r['id']:r for r in load_jsonl(source/'jsonl/grades'/(judge+'.jsonl'))};n=0
  for oid,m in mapping.items():
   oldid=lookup.get((m['group'],m['question_id']))
   if oldid is None:continue
   if m['run_sha256']!=oldmap[oldid]['run_sha256'] or {k:v for k,v in blind[oid].items() if k!='id'}!={k:v for k,v in oldblind[oldid].items() if k!='id'}:raise BenchError('复用判分的题目、答案或运行记录不同。')
   row=oldgrades[oldid];raw=source/'grading/raw'/judge/(oldid+'.jsonl')
   if sha256(raw)!=row['raw_sha256']:raise BenchError('baseline 判分原文哈希不同。')
   events,final=parse_stream(raw.read_text(),allow_structured=True);bench.verify_events(events,{'search':'none','structured_output':True});verdict=final.get('structured_output') or json.loads(final['result'])
   if verdict!={k:row[k] for k in ['verdict','reason']}:raise BenchError('baseline 判分与原文不同。')
   baseline.copy_checked(raw,out/'grading/raw'/judge/(oid+'.jsonl'))
   replacement=dict(row,id=oid,reused_raw=True,reused_from={'phase':'baseline','id':oldid})
   if oid in done and done[oid]!=replacement:raise BenchError('已有正式判分与复用来源不同。')
   done[oid]=replacement;n+=1
  write_text(path,''.join(dumps(r)+'\n' for r in done.values()));counts[judge]=n
 receipt.update(reused_baseline_grades=counts,baseline_record_sha256=sha256(source/'baseline-record.json'),grader_tool_sha256={p.name:sha256(p) for p in [ROOT/'tools/search_run.py',ROOT/'tools/bench.py',ROOT/'tools/grade.py',ROOT/'tools/common.py']});write_json(out/'grading/receipt.json',receipt)
 print(dumps({'reused_baseline_grades':counts,'new_grades_per_judge':len(mapping)-min(counts.values())}),flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['run','grade-prepare']);p.add_argument('--execute',action='store_true');p.add_argument('--quota-confirmed',action='store_true');p.add_argument('--pilot-approved',action='store_true');p.add_argument('--workers',type=int,choices=[1,2,4],default=4);p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 cfg=read_json(bench.CONFIG);questions=load_jsonl(ROOT/'questions/questions.jsonl');issues=bench.validate(questions,strict=True)+bench.validate_models(cfg)
 if issues:raise BenchError('；'.join(issues))
 if a.action=='grade-prepare':prepare_grades(OUT,SOURCE);return
 if not a.execute:print(dumps({'search_groups':SEARCH_GROUPS,'questions_per_group':len(questions),'new_search_calls':len(questions)*len(SEARCH_GROUPS),'reused_baseline_runs':len(questions)*len(baseline.GROUPS),'out':str(OUT),'workers':a.workers}));return
 if not (a.quota_confirmed and a.pilot_approved):raise BenchError('正式搜索需要已有额度及试跑授权。')
 run(OUT,SOURCE,questions,cfg,a.workers,a.timeout)
if __name__=='__main__':
 try:main()
 except (BenchError,ValueError,KeyError,FileNotFoundError,subprocess.TimeoutExpired) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
