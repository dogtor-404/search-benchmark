#!/usr/bin/env python3
"""按匿名ID并行调用原判分器；相同提示词与单题隔离，父进程统一合并。"""
import argparse,concurrent.futures,fcntl,json,subprocess,sys
from pathlib import Path
import grade,multilingual,bench
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256,parse_stream

def checked(path,judge):
 row=load_jsonl(path/'jsonl/grades'/(judge+'.jsonl'))
 if len(row)!=1:raise BenchError('单题判分记录不唯一')
 r=row[0];raw=path/'grading/raw'/judge/(r['id']+'.jsonl')
 if r['raw_sha256']!=sha256(raw):raise BenchError('单题判分原文散列不同')
 events,final=parse_stream(raw.read_text(),allow_structured=True)
 bench.verify_events(events,{'search':'none','structured_output':True})
 expected=json.loads((path/'manifest.json').read_text())['config']['judges'][judge]
 if any(e.get('model')!=expected for e in events if e.get('type')=='system' and e.get('subtype')=='init'):raise BenchError('单题判分模型不同')
 v=final.get('structured_output') or json.loads(final['result'])
 if v!={k:r[k] for k in ['verdict','reason']}:raise BenchError('单题评分与原文不同')
 return r,raw

def package(out,judge):
 manifest=json.loads((out/'manifest.json').read_text());receipt=json.loads((out/'grading/receipt.json').read_text());path=out/'grading/blind.jsonl'
 if receipt['blind_sha256']!=sha256(path) or receipt['instruction']!=multilingual.INSTRUCTION or receipt['schema']!=grade.SCHEMA:raise BenchError('匿名包或既定判分规则不同')
 rows=load_jsonl(path)
 if len({r['id'] for r in rows})!=len(rows):raise BenchError('匿名ID重复')
 return rows,manifest['config']['judges'][judge],receipt

def execute(out,judge,workers,timeout):
 (out/'grading').mkdir(parents=True,exist_ok=True)
 with (out/'grading'/('parallel-'+judge+'.lock')).open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('本判分员已有并行运行器') from None
  rows,model,receipt=package(out,judge);grade.INSTRUCTION=receipt['instruction']
  target=out/'jsonl/grades'/(judge+'.jsonl');done={}
  if target.exists():
   for r in load_jsonl(target):
    if r['id'] in done:raise BenchError('父判分记录ID重复')
    done[r['id']]=r
  ids={r['id'] for r in rows}
  if set(done)-ids:raise BenchError('已有无关评分ID')
  for oid,r in done.items():
   raw=out/'grading/raw'/judge/(oid+'.jsonl')
   if sha256(raw)!=r['raw_sha256']:raise BenchError('已有评分原文变化')
   events,final=parse_stream(raw.read_text(),allow_structured=True);bench.verify_events(events,{'search':'none','structured_output':True})
   if any(e.get('model')!=model for e in events if e.get('type')=='system' and e.get('subtype')=='init'):raise BenchError('已有判分模型不同')
   v=final.get('structured_output') or json.loads(final['result'])
   if v!={k:r[k] for k in ['verdict','reason']}:raise BenchError('已有评分与原文不符')
  frozen={'judge':judge,'model':model,'workers':workers,'blind_sha256':sha256(out/'grading/blind.jsonl'),'instruction':receipt['instruction'],'schema':receipt['schema'],'tool_sha256':{n:sha256(ROOT/'tools'/n) for n in ['grade.py','bench.py','common.py','multilingual_grade_parallel.py']}}
  policy=out/'grading'/('parallel-'+judge+'-receipt.json')
  if policy.exists() and json.loads(policy.read_text())!=frozen:raise BenchError('并行评分配置或工具变化')
  if not policy.exists():write_json(policy,frozen)
  todo=iter(r for r in rows if r['id'] not in done)
  def one(r):
   oid=r['id'];job=out/'grading/jobs'/judge/oid
   expected=dumps({'id':oid,'question':r['question'],'reference_answer':r['reference_answer'],'aliases':r['aliases'],'candidate_answer':r['candidate_answer']})+'\n'
   bp=job/'grading/blind.jsonl'
   if bp.exists():
    if bp.read_text()!=expected:raise BenchError('单题匿名材料变化')
   else:
    write_text(bp,expected);write_json(job/'manifest.json',{'config':{'judges':{judge:model}}})
    write_json(job/'grading/receipt.json',{'blind_sha256':sha256(bp),'instruction':receipt['instruction'],'schema':receipt['schema']})
   grade.run(job,judge,True,True,timeout)
   result,raw=checked(job,judge)
   if result['id']!=oid:raise BenchError('评分ID串题')
   return result,raw
  failure=None
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
   active={}
   def submit():
    try:r=next(todo)
    except StopIteration:return
    active[pool.submit(one,r)]=r['id']
   for _ in range(workers):submit()
   while active:
    finished,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
    for f in finished:
     oid=active.pop(f)
     try:
      result,raw=f.result();dest=out/'grading/raw'/judge/(oid+'.jsonl')
      if dest.exists() and dest.read_text()!=raw.read_text():raise BenchError('父原文已存在且不同，禁止覆盖')
      if not dest.exists():write_text(dest,raw.read_text())
      done[oid]=result;write_text(target,''.join(dumps(v)+'\n' for v in done.values()))
      print(dumps({'judge':judge,'done':len(done),'total':len(rows),'id':oid}),flush=True)
     except BaseException as e:
      failure=failure or e;print(dumps({'judge':judge,'failed_id':oid,'error_type':type(e).__name__,'new_jobs_stopped':True}),flush=True)
    if failure is None:
     for _ in finished:submit()
  if failure:raise failure
  if set(done)!=ids:raise BenchError('判分覆盖不完整')
  return len(done)

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','full'],default='full');p.add_argument('--judge',choices=['claude','deepseek'],required=True);p.add_argument('--workers',type=int,choices=[1,2,4],default=4);p.add_argument('--timeout',type=int,default=600);p.add_argument('--execute',action='store_true');p.add_argument('--quota-confirmed',action='store_true');a=p.parse_args()
 out=ROOT/('tmp/pilot-multilingual' if a.phase=='pilot' else 'tmp/archive-multilingual')
 rows,model,_=package(out,a.judge)
 if not a.execute:print(dumps({'judge':a.judge,'model':model,'records':len(rows),'workers':a.workers,'execute':False}));return
 if not a.quota_confirmed:raise BenchError('需既有额度授权')
 print(dumps({'complete':True,'judge':a.judge,'records':execute(out,a.judge,a.workers,a.timeout)}))
if __name__=='__main__':
 try:main()
 except (BenchError,ValueError,KeyError,FileNotFoundError,subprocess.TimeoutExpired) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
