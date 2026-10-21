#!/usr/bin/env python3
"""本次授权运行的顺序流水线；不重试故障，等待完整作答后自动启动评分。"""
import datetime,json,subprocess,sys,time
from pathlib import Path
from common import ROOT,BenchError,load_jsonl,write_json,write_text,sha256,dumps
OUT=ROOT/'tmp/archive-multilingual'
def state(stage,**extra):
 write_json(OUT/'pipeline/status.json',{'stage':stage,'updated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),**extra})
def split_blind():
 blind=OUT/'grading/blind.jsonl';rows=load_jsonl(blind);parts=[]
 if len(rows)!=1200 or len({r['id'] for r in rows})!=1200:raise BenchError('正式匿名包不是1200个不同ID')
 for i in range(12):
  p=OUT/'grading/independent-input'/f'batch-{i:02d}.jsonl';value=''.join(dumps(r)+'\n' for r in rows[i*100:(i+1)*100])
  if p.exists() and p.read_text()!=value:raise BenchError('独立评分分批材料变化')
  if not p.exists():write_text(p,value)
  parts.append({'batch':i,'records':100,'path':str(p.relative_to(OUT)),'sha256':sha256(p)})
 write_json(OUT/'grading/independent-input/receipt.json',{'source_blind_sha256':sha256(blind),'records':len(rows),'parts':parts,'policy':'第三票按匿名ID分批，每份答案仅1张独立AI票；不可读映射、其他评分或联网。'})
def main():
 manifest=json.loads((OUT/'manifest.json').read_text());expected=len(manifest['question_ids'])*len(manifest['all_groups'])
 if expected!=1200:raise BenchError('正式作答目标不符')
 while True:
  paths=list((OUT/'runs').glob('*/*.json'));rows=[json.loads(p.read_text()) for p in paths];bad=[{'group':r.get('group'),'question_id':r.get('question_id'),'error':r.get('error')} for r in rows if r.get('status')!='ok']
  if bad:state('answer_failure_needs_review',valid=len(rows)-len(bad),target=expected,failed=bad);raise BenchError('作答存在故障，流水线停止自动后续阶段，须先检查归档')
  state('answering',valid=len(rows),target=expected)
  if len(rows)==expected:break
  time.sleep(20)
 state('preparing_blind_package',valid=expected,target=expected)
 subprocess.run([sys.executable,'tools/multilingual.py','grade-prepare','--phase','full'],cwd=ROOT,check=True)
 split_blind()
 write_json(OUT/'grading/policy.json',{'authorized_user_message':'开始','method':'三位AI逐份匿名评分，至少两张相同二元票才裁决；无多数待核','language_policy':'回答语言不影响事实等价判断','independent_policy':'第三位Codex AI可分批，匿名ID唯一覆盖，只读独立材料，不读映射或他人评分，不联网','parallel_workers_per_api_judge':4,'input_sha256':sha256(OUT/'grading/blind.jsonl'),'tool_sha256':{n:sha256(ROOT/'tools'/n) for n in ['grade.py','multilingual_grade_parallel.py','multilingual_pipeline.py','multilingual.py','bench.py','common.py']}})
 state('grading',valid=expected,blind_records=1200,api_judges=['claude','deepseek'],independent_ready=True)
 processes={};logs={}
 for judge in ['claude','deepseek']:
  log=OUT/'pipeline'/(judge+'-grading.log');log.parent.mkdir(parents=True,exist_ok=True);logs[judge]=log.open('a')
  processes[judge]=subprocess.Popen([sys.executable,'-u','tools/multilingual_grade_parallel.py','--phase','full','--judge',judge,'--workers','4','--execute','--quota-confirmed'],cwd=ROOT,stdout=logs[judge],stderr=subprocess.STDOUT)
 try:
  while any(p.poll() is None for p in processes.values()):
   counts={j:len(load_jsonl(OUT/'jsonl/grades'/(j+'.jsonl'))) if (OUT/'jsonl/grades'/(j+'.jsonl')).exists() else 0 for j in ['claude','deepseek','independent']}
   state('grading',valid=expected,grade_counts=counts,api_exit_codes={j:p.poll() for j,p in processes.items()},independent_ready=True)
   time.sleep(20)
 finally:
  for log in logs.values():log.close()
 failures={j:p.returncode for j,p in processes.items() if p.returncode}
 if failures:state('grade_failure_needs_review',failures=failures);raise BenchError('评分调用有故障；已保留原文，不自动重试')
 state('awaiting_independent_votes',api_grade_records=2400)
 while not (OUT/'grading/independent-receipt.json').exists():time.sleep(20)
 subprocess.run([sys.executable,'tools/multilingual.py','report','--phase','full'],cwd=ROOT,check=True)
 state('base_report_ready',report='analysis/report.md')
 print(dumps({'stage':'base_report_ready','report':str(OUT/'analysis/report.md')}))
if __name__=='__main__':
 try:main()
 except (BenchError,subprocess.CalledProcessError,ValueError,KeyError,FileNotFoundError) as e:
  print('流水线停止：'+str(e),file=sys.stderr);sys.exit(1)
