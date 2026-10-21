#!/usr/bin/env python3
"""正式轮独立单票流水线：发布匿名包、校验agent输出，全部齐备再报告。"""
import datetime,fcntl,json,subprocess,sys,time
import multilingual_live_blind as live
from common import ROOT,BenchError,write_json,dumps
OUT=live.OUT

def status(stage,**extra):
 write_json(OUT/'pipeline/status.json',dict(stage=stage,updated_at=datetime.datetime.now().astimezone().isoformat(),**extra))

def main():
 (OUT/'pipeline').mkdir(parents=True,exist_ok=True)
 with (OUT/'pipeline/independent.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('独立评分流水线已在运行') from None
  policy=json.loads((OUT/'grading/policy.json').read_text())
  if policy['api_judges_enabled']!=[] or policy['independent_votes_per_answer']!=1:raise BenchError('用户评分策略不符')
  previous=None
  while True:
   rows=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*/*.json')];bad=[{'group':r.get('group'),'question_id':r.get('question_id'),'error':r.get('error')} for r in rows if r.get('status')!='ok']
   if bad:status('answer_failure_needs_review',valid=len(rows)-len(bad),failed=bad);raise BenchError('作答技术故障，先检查归档；已有独立评分保留')
   published=live.publish();graded=live.merge();value={'valid_answers':len(rows),'target_answers':1200,'published':published['published'],'graded':graded['graded'],'missing_batches':graded['missing_batches'],'source_complete':published['source_complete']}
   status('answering_and_independent_grading',**value)
   if value!=previous:print(dumps(value),flush=True);previous=value
   if graded['complete']:
    status('building_independent_report',**value)
    subprocess.run([sys.executable,'tools/multilingual_single_report.py'],cwd=ROOT,check=True)
    status('independent_report_ready',**value);return
   time.sleep(20)

if __name__=='__main__':
 try:main()
 except (BenchError,ValueError,KeyError,FileNotFoundError,subprocess.CalledProcessError) as e:print('独立流水线停止：'+str(e),file=sys.stderr);sys.exit(1)
