"""共享数据读写、凭据保护与进程隔离。"""
import hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SECRET_PATTERN=re.compile(r'(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,})',re.I)
class BenchError(Exception):pass

def load_jsonl(path):
 return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]
def dumps(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)
def check_secret(text,secrets=()):
 if any(s and s in text for s in secrets) or SECRET_PATTERN.search(text):raise BenchError('输出疑似包含凭据，已阻止写盘；未记录敏感内容。')
def write_json(path,value,secrets=()):write_text(path,dumps(value)+'\n',secrets)
def write_text(path,text,secrets=()):
 check_secret(text,secrets);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.writing-')
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'w') as f:f.write(text)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def keychain_key():
 p=subprocess.run(['security','find-generic-password','-s','DEEPSEEK_API_KEY','-w'],capture_output=True,text=True)
 if p.returncode:raise BenchError('无法从 macOS 钥匙串读取 DEEPSEEK_API_KEY。')
 key=p.stdout.strip()
 if not key:raise BenchError('钥匙串里的 DeepSeek key 为空。')
 return key

def clean_env():
 env=os.environ.copy()
 for k in list(env):
  if k.startswith(('ANTHROPIC_','CLAUDE','BENCH_','VSCODE','CURSOR','WINDSURF','JETBRAINS','IDEA_','PYCHARM','WEBSTORM','GOLAND','CLION','FLEET_','ZED_')) or k in ('DEEPSEEK_API_KEY','ELECTRON_RUN_AS_NODE','NODE_OPTIONS','GIT_ASKPASS','SSH_ASKPASS','INSIDE_EMACS'):
   env.pop(k,None)
 if env.get('TERM_PROGRAM','').lower() in ('vscode','cursor','windsurf','zed'):
  for k in ('TERM_PROGRAM','TERM_PROGRAM_VERSION','TERM_SESSION_ID'):env.pop(k,None)
 # 只注入基准自己需要的设置，网络代理和系统 PATH 保留。
 env['CLAUDE_CODE_DISABLE_AUTO_MEMORY']='1'
 return env

def parse_stream(text,allow_structured=False,allowed_budget_denial_ids=()):
 try:events=[json.loads(l) for l in text.splitlines() if l.strip()]
 except (ValueError,TypeError):raise BenchError('Claude 输出不是合法的 stream-json。') from None
 results=[e for e in events if e.get('type')=='result']
 if len(results)!=1:raise BenchError('Claude 没有产生唯一的最终结果。')
 final=results[0]
 if final.get('is_error') or final.get('subtype') not in (None,'success'):raise BenchError('Claude 报告调用失败。')
 for denial in final.get('permission_denials',[]):
  if denial.get('tool_name')!='WebSearch' or not denial.get('tool_use_id') or denial['tool_use_id'] not in allowed_budget_denial_ids:
   raise BenchError('本题有非预算导致的工具权限拒绝，需要检查后重跑。')
 answer=final.get('result')
 if (not isinstance(answer,str) or not answer.strip()) and not (allow_structured and isinstance(final.get('structured_output'),dict)):raise BenchError('最终答案为空。')
 return events,final
