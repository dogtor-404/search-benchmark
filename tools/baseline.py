#!/usr/bin/env python3
"""四个不搜索组的题库诊断；复用试跑，不启动搜索组或正式全量。"""
import argparse,collections,concurrent.futures,datetime,fcntl,json,subprocess,sys,threading
from pathlib import Path
import bench,grade
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256,check_secret,parse_stream
GROUPS=['0','D0','0_prime','D0_prime']
OUT=ROOT/'tmp/baseline'
SOURCE=ROOT/'tmp/pilot'

def read_json(path):return json.loads(path.read_text())
def copy_checked(source,target):
 text=source.read_text();check_secret(text)
 if target.exists():
  if target.read_text()!=text:raise BenchError('复用目标与来源不同，拒绝覆盖。')
 else:write_text(target,text)

def validate_cached(source,gid,qid,cfg):
 meta=source/'runs'/gid/(qid+'.json');r=read_json(meta)
 if r.get('status')!='ok' or r.get('group')!=gid or r.get('question_id')!=qid or r.get('model')!=cfg['groups'][gid]['model']:raise BenchError('复用作答的状态、分组或模型不符。')
 if r.get('search_calls')!=0 or r.get('search_attempts',0)!=0 or r.get('tools') or r.get('searches'):raise BenchError('不搜索组的复用记录包含工具或搜索。')
 raw=source/'jsonl'/gid/(qid+'.jsonl')
 if r.get('raw')!=str(raw.relative_to(source)):raise BenchError('复用原始输出路径不符。')
 stdout=raw.read_text();check_secret(stdout);events,final=parse_stream(stdout);bench.verify_events(events,cfg['groups'][gid])
 if final['result']!=r['answer']:raise BenchError('原始回答与运行记录不同。')
 return r

def prepare(out,source,questions,cfg,version):
 old=read_json(source/'manifest.json');qhash=sha256(ROOT/'questions/questions.jsonl')
 if old['question_sha256']!=qhash or old['config']!=cfg or old['claude_code_version']!=version:raise BenchError('试跑与当前题库、配置或 CLI 不一致，不能自动复用。')
 qids=[q['id'] for q in questions]
 if any(cfg['groups'][g]['search']!='none' for g in GROUPS):raise BenchError('诊断只能调用四个不搜索组。')
 cached={}
 for g in GROUPS:
  for qid in old['question_ids']:
   if qid not in qids:raise BenchError('试跑题不在当前题库。')
   validate_cached(source,g,qid,cfg)
   cached[g+'/'+qid]={'run_sha256':sha256(source/'runs'/g/(qid+'.json')),'raw_sha256':sha256(source/'jsonl'/g/(qid+'.jsonl'))}
 frozen={'phase':'baseline','purpose':'四个不搜索组的题库难度诊断，不含搜索组','question_sha256':qhash,'config_sha256':sha256(bench.CONFIG),'tool_sha256':{p.name:sha256(p) for p in sorted((ROOT/'tools').glob('*')) if p.suffix in ('.py','.json')},'python_version':sys.version,'claude_code_version':version,'config':cfg,'question_ids':qids,'all_groups':GROUPS,'seed':cfg['seed'],'source_manifest_sha256':sha256(source/'manifest.json'),'reused_pilot_runs':cached}
 target=out/'manifest.json'
 if target.exists():
  saved=read_json(target)
  if any(saved.get(k)!=v for k,v in frozen.items()):raise BenchError('诊断配置或复用来源已经变化，拒绝混用。')
 else:write_json(target,dict(frozen,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 for g in GROUPS:
  for qid in old['question_ids']:
   for folder,suffix in [('runs','.json'),('jsonl','.jsonl')]:copy_checked(source/folder/g/(qid+suffix),out/folder/g/(qid+suffix))
 return len(cached)

def run(out,source,questions,cfg,workers,timeout):
 (ROOT/'tmp').mkdir(exist_ok=True)
 with (ROOT/'tmp/run.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('已有作答运行器持有运行锁。') from None
  return run_locked(out,source,questions,cfg,workers,timeout)

def run_locked(out,source,questions,cfg,workers,timeout):
 version=subprocess.check_output(['claude','--version'],text=True).strip();reused=prepare(out,source,questions,cfg,version)
 print(dumps({'reused_pilot_runs':reused,'target_runs':len(questions)*len(GROUPS),'workers':workers}),flush=True)
 stop=threading.Event();print_lock=threading.Lock()
 def one_group(g):
  try:
   for q in questions:
    if stop.is_set():return
    meta=out/'runs'/g/(q['id']+'.json')
    if meta.exists():
     if read_json(meta).get('status')=='ok':continue
     raise BenchError('已有失败记录，须先检查并归档，不能覆盖。')
    r=bench.execute_one(q,g,cfg['groups'][g],cfg,out,timeout)
    with print_lock:print(dumps({k:r[k] for k in ['group','question_id','status','elapsed_seconds']}),flush=True)
    if r['status']!='ok':raise BenchError('诊断作答失败，停止启动后续题；已运行的题保留结果。')
  except BaseException:
   stop.set();raise
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  futures=[pool.submit(one_group,g) for g in GROUPS]
  for future in concurrent.futures.as_completed(futures):future.result()
 print(dumps({'complete':True,'groups':len(GROUPS),'questions':len(questions),'reused':reused}),flush=True)

def prepare_grades(out,source):
 if not (out/'grading/receipt.json').exists():grade.prepare(out)
 receipt=read_json(out/'grading/receipt.json')
 if receipt['blind_sha256']!=sha256(out/'grading/blind.jsonl') or receipt['mapping_sha256']!=sha256(out/'grading/mapping.json'):raise BenchError('诊断盲判包校验失败。')
 old_receipt=read_json(source/'grading/receipt.json')
 if old_receipt['blind_sha256']!=sha256(source/'grading/blind.jsonl') or old_receipt['mapping_sha256']!=sha256(source/'grading/mapping.json'):raise BenchError('试跑判分包已经变化。')
 if receipt['instruction']!=old_receipt['instruction'] or receipt['schema']!=old_receipt['schema']:raise BenchError('判分规则变化，不能复用旧判分。')
 mapping=read_json(out/'grading/mapping.json');oldmap=read_json(source/'grading/mapping.json');lookup={(m['group'],m['question_id']):oid for oid,m in oldmap.items()}
 blind={r['id']:r for r in load_jsonl(out/'grading/blind.jsonl')};oldblind={r['id']:r for r in load_jsonl(source/'grading/blind.jsonl')};reused={}
 for judge in ['claude','deepseek']:
  path=out/'jsonl/grades'/(judge+'.jsonl');rows=load_jsonl(path) if path.exists() else [];done={r['id']:r for r in rows}
  oldgrades={r['id']:r for r in load_jsonl(source/'jsonl/grades'/(judge+'.jsonl'))};count=0
  for oid,m in mapping.items():
   oldid=lookup.get((m['group'],m['question_id']))
   if oldid is None:continue
   if {k:v for k,v in blind[oid].items() if k!='id'}!={k:v for k,v in oldblind[oldid].items() if k!='id'} or m['run_sha256']!=oldmap[oldid]['run_sha256']:raise BenchError('新旧候选答案或题目不一致，不能复用判分。')
   row=oldgrades[oldid];raw=source/'grading/raw'/judge/(oldid+'.jsonl')
   if row.get('raw_sha256')!=sha256(raw):raise BenchError('试跑判分原始输出哈希不符。')
   events,final=parse_stream(raw.read_text(),allow_structured=True);bench.verify_events(events,{'search':'none','structured_output':True})
   verdict=final.get('structured_output') or json.loads(final['result'])
   if verdict!={k:row[k] for k in ['verdict','reason']}:raise BenchError('试跑判分与原始输出不一致。')
   copy_checked(raw,out/'grading/raw'/judge/(oid+'.jsonl'))
   replacement=dict(row,id=oid,reused_raw=True,reused_pilot_id=oldid)
   if oid in done and done[oid]!=replacement:raise BenchError('已有判分与复用记录不一致。')
   done[oid]=replacement;count+=1
  write_text(path,''.join(dumps(v)+'\n' for v in done.values()));reused[judge]=count
 receipt['grader_tool_sha256']={p.name:sha256(p) for p in [ROOT/'tools/baseline.py',ROOT/'tools/bench.py',ROOT/'tools/grade.py',ROOT/'tools/common.py']};receipt['reused_pilot_grades']=reused;write_json(out/'grading/receipt.json',receipt)
 print(dumps({'reused_grades':reused,'new_grades_per_judge':len(mapping)-min(reused.values())}),flush=True)

def report(out):
 resolved,pending=grade.resolve(out);m=read_json(out/'manifest.json');questions={q['id']:q for q in load_jsonl(ROOT/'questions/questions.jsonl')}
 table={(r['group'],r['question_id']):r['correct'] for r in resolved};groups={};buckets=collections.Counter();items=[];by_set={}
 for g in GROUPS:
  values=[table[g,q] for q in m['question_ids'] if (g,q) in table];groups[g]={'resolved':len(values),'correct':sum(values),'accuracy':sum(values)/len(values) if values else None}
 for qid in m['question_ids']:
  values=[table.get((g,qid)) for g in GROUPS]
  bucket='needs_review' if None in values else 'all_correct' if all(values) else 'all_incorrect' if not any(values) else 'mixed'
  buckets[bucket]+=1;name=questions[qid]['set'];by_set.setdefault(name,collections.Counter())[bucket]+=1
  items.append({'question_id':qid,'set':name,'bucket':bucket,'correct':dict(zip(GROUPS,values))})
 summary={'phase':'baseline','question_n':len(m['question_ids']),'groups':groups,'buckets':dict(buckets),'by_set':{k:dict(v) for k,v in by_set.items()},'needs_human':len(pending),'items':items}
 write_json(out/'analysis/summary.json',summary)
 lines=['# 四个不搜索组：题库难度诊断','','沿用原 100 题、原提示词与双模型盲判；复用试跑的 40 次作答和 80 次判分，其余单独补跑。四组并行只用于难度诊断，不据此比较耗时。','',f'待人工复核：{len(pending)} 条。'+('下表仅汇总已有一致判定；未复核不当错题。' if pending else '双模型已一致判定全部答案。'),'','| 组 | 已判题数 | 答对 | 答对率 |','|---|---:|---:|---:|']
 for g,r in groups.items():lines.append(f'| {g} | {r["resolved"]} | {r["correct"]} | {r["accuracy"]:.1%} |' if r['accuracy'] is not None else f'| {g} | 0 | 0 | 待判 |')
 labels={'all_correct':'四组都答对','mixed':'部分组答对','all_incorrect':'四组都答错','needs_review':'判分待复核'}
 lines+=['','| 题集 | 四组都答对 | 部分组答对 | 四组都答错 | 判分待复核 |','|---|---:|---:|---:|---:|']
 for name,counts in by_set.items():lines.append('| '+name+' | '+' | '.join(str(counts.get(b,0)) for b in labels)+' |')
 lines+=['','总计：'+'；'.join(f'{label} {buckets[b]} 题' for b,label in labels.items())+'。','','不搜索表现只能用于划分当前模型的题目难度；它不能单独说明搜索组的得分，也不能证明题目是否进入过训练集。保留全部题目，不依据搜索组胜负筛题。逐题分层见 summary.json；分歧原文见 ../grading/needs-human.jsonl。']
 write_text(out/'analysis/report.md','\n'.join(lines)+'\n');print(dumps({'buckets':dict(buckets),'needs_human':len(pending),'report':str(out/'analysis/report.md')}))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['run','grade-prepare','grade-run','report']);p.add_argument('--judge',choices=['claude','deepseek']);p.add_argument('--execute',action='store_true');p.add_argument('--quota-confirmed',action='store_true');p.add_argument('--workers',type=int,choices=[1,2,4],default=4);p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 cfg=read_json(bench.CONFIG);questions=load_jsonl(ROOT/'questions/questions.jsonl')
 issues=bench.validate(questions,strict=True)+bench.validate_models(cfg)
 if issues:raise BenchError('；'.join(issues))
 if a.action=='run':
  if not a.execute:print(dumps({'groups':GROUPS,'questions':len(questions),'reuse':40,'new_calls':360,'out':str(OUT),'workers':a.workers}));return
  if not a.quota_confirmed:raise BenchError('真实调用需要已有额度授权。')
  run(OUT,SOURCE,questions,cfg,a.workers,a.timeout)
 elif a.action=='grade-prepare':prepare_grades(OUT,SOURCE)
 elif a.action=='grade-run':
  if not a.judge:raise BenchError('请选择判分模型。')
  grade.run(OUT,a.judge,a.execute,a.quota_confirmed,a.timeout)
 else:report(OUT)
if __name__=='__main__':
 try:main()
 except (BenchError,ValueError,KeyError,FileNotFoundError,subprocess.TimeoutExpired) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
