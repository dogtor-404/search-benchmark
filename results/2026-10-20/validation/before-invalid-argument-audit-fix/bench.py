#!/usr/bin/env python3
"""十组基准运行器。默认离线计划；只有 run --execute 才调用模型。"""
import argparse,collections,datetime,fcntl,json,os,random,re,signal,subprocess,sys,time
from pathlib import Path
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256,keychain_key,clean_env,parse_stream,check_secret
CONFIG=ROOT/'tools/config.json'
NEWS_WINDOW_DAYS=30
EXPECTED={'simpleqa_verified':25,'chinese_simpleqa':25,'frames':15,'custom':25,'news':10}

def validate(questions,strict=False,today=None):
 issues=[];ids=set();texts=set();counts=collections.Counter()
 today=today or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
 for q in questions:
  qid=q.get('id','?')
  for k in ['id','set','lang','question','answer','aliases','source_urls']:
   if k not in q:issues.append(f'{qid}: 缺少 {k}')
  if qid in ids:issues.append(f'{qid}: 重复 id')
  ids.add(qid);counts[q.get('set')]+=1
  text=q.get('question','').strip()
  if not text or text in texts:issues.append(f'{qid}: 题目空白或重复')
  texts.add(text)
  if not isinstance(q.get('answer'),str) or not q['answer'].strip():issues.append(f'{qid}: 标准答案为空')
  if not isinstance(q.get('aliases'),list):issues.append(f'{qid}: aliases 必须是数组')
  urls=q.get('source_urls',[])
  if not urls or any(not isinstance(u,str) or not re.match(r'^https?://[^/]+',u) for u in urls):issues.append(f'{qid}: 来源无效')
  if q.get('set')=='frames' and q.get('provenance',{}).get('wiki_count') not in (2,3):issues.append(f'{qid}: FRAMES 不是两三篇文章题')
  if q.get('set')=='custom' and (len(set(urls))<2 or not q.get('provenance',{}).get('published_video')):issues.append(f'{qid}: 自有题缺两源或发布证据')
  if strict and q.get('review',{}).get('status')!='verified':issues.append(f'{qid}: 尚未核实')
  if q.get('set')=='news':
   try:
    d=datetime.date.fromisoformat(q['event_date'])
    if strict and not 0<=(today-d).days<=NEWS_WINDOW_DAYS:issues.append(f'{qid}: 新闻超出运行前最近 {NEWS_WINDOW_DAYS} 天，或事件日期在未来')
   except (KeyError,ValueError):issues.append(f'{qid}: 新闻缺少有效事件日期')
 if dict(counts)!=EXPECTED:issues.append(f'题数不符合方案：{dict(counts)}；应为 {EXPECTED}')
 return issues

def validate_models(cfg):
 issues=[]
 for model in sorted({g['model'] for g in cfg['groups'].values()}):
  if not cfg['model_versions'].get(model):issues.append(model+': 缺少版本记录')
  if not cfg['version_sources'].get(model):issues.append(model+': 缺少模型版本的来源')
 return issues

def select(questions,phase):
 if phase=='full':return questions
 selected=[]
 for name,n in [('simpleqa_verified',2),('chinese_simpleqa',2),('frames',2),('custom',3),('news',1)]:
  pool=[q for q in questions if q['set']==name];random.Random(f'20261020:pilot:{name}').shuffle(pool);selected+=pool[:n]
 return selected

def command(group,cfg):
 cmd=['claude','-p','--output-format','stream-json','--verbose','--no-session-persistence','--model',group['model'],'--setting-sources','project,local','--strict-mcp-config','--disable-slash-commands','--no-chrome']
 if group['search']=='claude':cmd+=['--tools','WebSearch','--allowedTools','WebSearch','--mcp-config','tools/empty-mcp.json','--settings','tools/native-search-settings.json']
 elif group['search']=='deepseek':cmd+=['--tools','','--mcp-config','tools/deepseek-search.json','--allowedTools','mcp__deepseek-search__search']
 else:cmd+=['--tools','','--mcp-config','tools/empty-mcp.json']
 return cmd

def prompt(q,group,cfg):return cfg['baseline_prompt' if group['search']=='none' else 'search_prompt']+'\n\n'+q['question']

def verify_events(events,group):
 expected={'WebSearch'} if group['search']=='claude' else {'mcp__deepseek-search__search'} if group['search']=='deepseek' else set()
 if group.get('structured_output'):expected.add('StructuredOutput')
 calls=[];observed=[];searches=[];tool_ids={}
 for e in events:
  if e.get('type')=='system' and e.get('subtype')=='init':
   observed=e.get('tools',[])
   if set(observed)-expected:raise BenchError('初始化暴露了本组以外的工具，本题无效。')
  for block in e.get('message',{}).get('content',[]) if isinstance(e.get('message',{}).get('content'),list) else []:
   if block.get('type')=='tool_use':
    if block.get('name') not in expected:raise BenchError('检测到未授权工具，本题无效。')
    calls.append(block['name']);tool_ids[block.get('id')]=block['name']
   if block.get('type')=='tool_result' and tool_ids.get(block.get('tool_use_id'))=='WebSearch':
    content=block.get('content',[]);links=[]
    for item in content if isinstance(content,list) else []:
     if isinstance(item,dict) and item.get('type')=='text':
      text=item.get('text','')
      # Claude Code WebSearch 的 Links: [{title,url}, ...]；不从答案引用猜排名。
      match=re.search(r'Links:\s*(\[.*?\])',text,re.S)
      if match:
       try:links=json.loads(match.group(1))
       except ValueError:pass
    searches.append({'tool_use_id':block.get('tool_use_id'),'is_error':bool(block.get('is_error')),'results':links,'ranking_observable':bool(links)})
 if not any(e.get('type')=='system' and e.get('subtype')=='init' for e in events):raise BenchError('缺少初始化事件，无法核验工具隔离。')
 return calls,searches,observed

def audit_searches(events,group,aux,native_results):
 """只认可本地预算账本证明的正常拒绝；不把实际第六次搜索放行。"""
 calls=[b for e in events for b in (e.get('message',{}).get('content',[]) if isinstance(e.get('message',{}).get('content'),list) else []) if b.get('type')=='tool_use']
 if group['search']=='none':return [],[]
 path=aux/('native-attempts.jsonl' if group['search']=='claude' else 'search.jsonl')
 records=load_jsonl(path) if path.exists() else []
 if len(records)!=len(calls):raise BenchError('搜索尝试与审计记录不一致。')
 allowed_status='allowed' if group['search']=='claude' else 'ok'
 denied=[r for r in records if r.get('status')=='budget_exhausted']
 actual=[r for r in records if r.get('status')!='budget_exhausted']
 if len(actual)>5 or (denied and len(actual)!=5):raise BenchError('预算审计不符：实际搜索超限或过早拒绝。')
 if any(r.get('status')!=allowed_status for r in actual):raise BenchError('存在真实搜索失败或审计错误。')
 if sorted(r.get('call',0) for r in actual)!=list(range(1,len(actual)+1)):raise BenchError('实际搜索编号不连续。')
 if any(r.get('billable') or r.get('results') or r.get('call') is not None for r in denied):raise BenchError('预算拒绝不应执行或计费。')
 if group['search']=='deepseek':
  if collections.Counter(r.get('query') for r in records)!=collections.Counter(c.get('input',{}).get('query') for c in calls):raise BenchError('搜索 query 与审计记录不匹配。')
  return actual,denied
 ids=[c.get('id') for c in calls];record_ids=[r.get('tool_use_id') for r in records]
 if not all(ids) or len(set(ids))!=len(ids) or set(ids)!=set(record_ids) or len(set(record_ids))!=len(records):raise BenchError('原生搜索调用 ID 与预算记录不一致。')
 inputs={c['id']:c.get('input',{}).get('query') for c in calls}
 if any(r.get('query')!=inputs[r['tool_use_id']] for r in records):raise BenchError('原生搜索 query 与预算记录不一致。')
 results={r['tool_use_id']:r for r in native_results}
 searches=[]
 for r in actual:
  result=results.get(r['tool_use_id'])
  if result is None or result.get('is_error'):raise BenchError('原生搜索缺少返回结果或发生非预算错误。')
  searches.append(dict(result,call=r['call'],query=r['query'],status='ok'))
 return searches,denied

def execute_one(q,gid,group,cfg,out,timeout):
 raw=out/'jsonl'/gid/(q['id']+'.jsonl');meta=out/'runs'/gid/(q['id']+'.json');aux=out/'audit'/gid/q['id']
 if raw.exists() or meta.exists():raise BenchError('该题已有输出；请使用原运行的续跑，不覆盖原始记录。')
 env=clean_env();key=None
 if group['provider']=='deepseek' or group['search']=='deepseek':key=keychain_key()
 if group['provider']=='deepseek':env.update(ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic',ANTHROPIC_AUTH_TOKEN=key)
 if group['search']=='deepseek':env['BENCH_DEEPSEEK_KEY']=key;env['BENCH_SEARCH_LOG']=str(aux/'search.jsonl')
 env['BENCH_NATIVE_BUDGET']=str(aux/'native-count.txt')
 env['BENCH_NATIVE_AUDIT']=str(aux/'native-attempts.jsonl')
 cmd=command(group,cfg);start=time.monotonic()
 proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 timed_out=False
 try:stdout,stderr=proc.communicate(prompt(q,group,cfg),timeout=timeout)
 except (subprocess.TimeoutExpired,KeyboardInterrupt):
  os.killpg(proc.pid,signal.SIGTERM)
  try:stdout,stderr=proc.communicate(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
  timed_out=True
 # 整个输出先扫描再写盘，连失败输出也留在 tmp 下。
 check_secret(stdout+'\n'+stderr,(key,));write_text(raw,stdout,(key,));write_text(aux/'stderr.txt',stderr,(key,))
 result={'group':gid,'question_id':q['id'],'elapsed_seconds':round(time.monotonic()-start,3),'exit_code':proc.returncode,'status':'failed','raw':str(raw.relative_to(out))}
 try:
  if timed_out:raise BenchError('本题超时或被取消，进程组已终止。')
  if proc.returncode:raise BenchError('Claude 进程返回非零状态；请检查本题日志。')
  native_ledger=aux/'native-attempts.jsonl'
  native_records=load_jsonl(native_ledger) if group['search']=='claude' and native_ledger.exists() else []
  budget_ids={r.get('tool_use_id') for r in native_records if r.get('status')=='budget_exhausted' and r.get('tool_use_id')}
  events,final=parse_stream(stdout,allowed_budget_denial_ids=budget_ids);calls,searches,observed=verify_events(events,group)
  searches,budget_denials=audit_searches(events,group,aux,searches)
  result.update(status='ok',answer=final['result'],model=group['model'],observed_model=sorted({e.get('message',{}).get('model') for e in events if e.get('message',{}).get('model')}),tools=observed,search_calls=len(searches),search_attempts=len(calls),search_budget_denials=len(budget_denials),budget_denials=budget_denials,searches=searches,usage=final.get('usage'),model_usage=final.get('modelUsage'),reported_cost_usd=final.get('total_cost_usd'),search_cost_usd=sum(bool(s.get('billable')) for s in searches)*cfg['search_price_usd'] if group['search']=='deepseek' else 0,subscription=group['provider']=='claude')
 except BenchError as e:result['error']=str(e)
 write_json(meta,result,(key,));return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','preflight','plan','run']);p.add_argument('--phase',choices=['pilot','full'],default='pilot');p.add_argument('--execute',action='store_true');p.add_argument('--quota-confirmed',action='store_true');p.add_argument('--pilot-approved',action='store_true');p.add_argument('--groups',nargs='+');p.add_argument('--resume',action='store_true');p.add_argument('--timeout',type=int,default=600)
 args=p.parse_args();cfg=json.loads(CONFIG.read_text());questions=load_jsonl(ROOT/'questions/questions.jsonl');issues=validate(questions,strict=args.action=='preflight' or args.action=='run' and args.execute)
 if issues:
  print('\n'.join(issues));return 1
 chosen=select(questions,args.phase);groups=args.groups or list(cfg['groups'])
 if any(g not in cfg['groups'] for g in groups):raise BenchError('未知分组。')
 summary={'phase':args.phase,'questions_per_group':len(chosen),'groups':groups,'runs':len(chosen)*len(groups),'review':dict(collections.Counter(q.get('review',{}).get('status','pending') for q in questions))}
 if args.action=='check':print(dumps(summary));return 0
 if args.action=='preflight':
  missing=validate_models(cfg)
  print(dumps(dict(summary,news_window_days=NEWS_WINDOW_DAYS,ready=not missing,blocking=missing)));return int(bool(missing))
 if args.action=='plan' or not args.execute:
  print(dumps(summary))
  for gid in groups:print(dumps({'group':gid,'command':command(cfg['groups'][gid],cfg),'question_ids':[q['id'] for q in chosen]}))
  return 0
 if not args.quota_confirmed:raise BenchError('运行前必须由用户确认 Claude 周额度，再传 --quota-confirmed。')
 if args.phase=='full' and not args.pilot_approved:raise BenchError('全量运行前必须取得用户对试跑结果和预算的批准，再传 --pilot-approved。')
 model_issues=validate_models(cfg)
 if model_issues:raise BenchError('；'.join(model_issues))
 (ROOT/'tmp').mkdir(exist_ok=True)
 lock=(ROOT/'tmp/run.lock').open('a+')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise BenchError('已有测试运行器持有运行锁。') from None
 version=subprocess.check_output(['claude','--version'],text=True).strip()
 out=ROOT/('tmp/pilot' if args.phase=='pilot' else 'tmp/archive');manifest=out/'manifest.json'
 frozen={'phase':args.phase,'question_sha256':sha256(ROOT/'questions/questions.jsonl'),'config_sha256':sha256(CONFIG),'tool_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'tools').glob('*')) if p.suffix in ('.py','.json')},'python_version':sys.version,'claude_code_version':version,'config':cfg,'question_ids':[q['id'] for q in chosen],'all_groups':list(cfg['groups']),'seed':cfg['seed']}
 if manifest.exists():
  saved=json.loads(manifest.read_text())
  if not args.resume:raise BenchError('已有运行目录；续跑必须传 --resume。')
  if any(saved.get(k)!=v for k,v in frozen.items()):raise BenchError('运行配置、题库或 CLI 版本已变化，拒绝混用结果。')
 else:
  if args.resume:raise BenchError('没有可续跑的 manifest。')
  write_json(manifest,dict(frozen,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 for gid in groups:
  for q in chosen:
   mp=out/'runs'/gid/(q['id']+'.json')
   if args.resume and mp.exists():
    if json.loads(mp.read_text()).get('status')=='ok':continue
    raise BenchError(f'{gid}/{q["id"]}: 上次失败输出保留；请先人工检查并归档失败记录，不能静默覆盖。')
   result=execute_one(q,gid,cfg['groups'][gid],cfg,out,args.timeout);print(dumps({k:result[k] for k in ['group','question_id','status','elapsed_seconds']}),flush=True)
   if result['status']!='ok':raise BenchError('本题失败，暂停后续调用以免继续消耗额度。')
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
