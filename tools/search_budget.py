#!/usr/bin/env python3
"""Claude PreToolUse hook：锁住每题预算，并按 tool_use_id 留下拒绝凭据。"""
import fcntl,json,os,sys
from pathlib import Path
from common import BenchError,dumps,write_text
BUDGET_CODE='BENCH_SEARCH_BUDGET_EXHAUSTED'

def decide(event,path,audit_path=None):
 if event.get('tool_name')!='WebSearch':return 'deny','本组只允许 WebSearch。'
 if audit_path and not event.get('tool_use_id'):raise BenchError('缺少 tool_use_id。')
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+') as f:
  os.chmod(path,0o600);fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);s=f.read().strip();n=int(s or '0')
  denied=n>=5
  if not denied:
   f.seek(0);f.truncate();f.write(str(n+1));f.flush()
  if audit_path:
   p=Path(audit_path);old=p.read_text() if p.exists() else ''
   row={'tool_use_id':event['tool_use_id'],'query':event.get('tool_input',{}).get('query'),'status':'budget_exhausted' if denied else 'allowed','call':None if denied else n+1,'results':[],'billable':False}
   write_text(p,old+dumps(row)+'\n')
 if denied:return 'deny',BUDGET_CODE+'：已经达到每题五次搜索上限，请用已有信息作答。'
 return 'allow','搜索次数在上限内。'
if __name__=='__main__':
 try:d,r=decide(json.load(sys.stdin),os.environ['BENCH_NATIVE_BUDGET'],os.environ['BENCH_NATIVE_AUDIT'])
 except Exception:d,r='deny','搜索计数器或审计记录不可用，阻止调用。'
 print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':d,'permissionDecisionReason':r}},ensure_ascii=False))
