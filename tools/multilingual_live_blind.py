#!/usr/bin/env python3
"""用户改为独立AI单票后，边作答边发布不可变的匿名百题评分包。"""
import argparse,datetime,fcntl,json,os,random,sys,uuid
from pathlib import Path
import multilingual as m
from common import ROOT,BenchError,load_jsonl,write_json,write_text,sha256,dumps
OUT=ROOT/'tmp/archive-multilingual'
STAGING=Path(os.environ.get('SEARCH_BENCHMARK_GRADING_DIR', str(ROOT/'tmp/independent-grading'))).expanduser()

def publish(out=OUT,batch_size=100):
 manifest=m.read(out/'manifest.json');qfile=ROOT/manifest['question_file']
 if sha256(qfile)!=manifest['question_sha256']:raise BenchError('题库漂移')
 questions={q['id']:q for q in load_jsonl(qfile)}
 directory=out/'grading';directory.mkdir(parents=True,exist_ok=True)
 with (directory/'live-blind.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise BenchError('匿名发布器已在运行') from None
  path=directory/'blind.jsonl';mapping_path=directory/'mapping.json'
  existing=load_jsonl(path) if path.exists() else [];mapping=m.read(mapping_path) if mapping_path.exists() else {}
  ids={r['id'] for r in existing}
  if len(ids)!=len(existing) or ids!=set(mapping):raise BenchError('匿名记录与映射不符')
  claimed={(r['group'],r['question_id']) for r in mapping.values()}
  if len(claimed)!=len(mapping):raise BenchError('同一作答重复匿名化')
  for value in mapping.values():
   if sha256(out/'runs'/value['group']/(value['question_id']+'.json'))!=value['run_sha256']:raise BenchError('已评分作答发生变化')
  expected={(g,q) for g in manifest['all_groups'] for q in manifest['question_ids']}
  if not claimed<=expected:raise BenchError('匿名记录包含非本轮作答')
  candidates=[]
  for g,qid in sorted(expected-claimed):
   p=out/'runs'/g/(qid+'.json')
   if p.exists() and m.read(p).get('status')=='ok':candidates.append((g,qid))
  random.Random(f'20261021:live:{len(existing)}').shuffle(candidates)
  available_total=len(existing)+len(candidates)
  small_tail=batch_size==100 and len(expected)==1200
  publish_total=(available_total//batch_size)*batch_size if not small_tail or available_total<1100 else 1100+((available_total-1100)//20)*20
  if available_total==len(expected):publish_total=available_total
  take=publish_total-len(existing)
  additions=[]
  for g,qid in candidates[:take]:
   q=questions[qid];r=m.check_run(out,g,q,manifest['config']);oid=uuid.uuid4().hex
   additions.append({'id':oid,'question':q['question'],'reference_answer':q['answer'],'aliases':q['aliases'],'candidate_answer':r['answer']})
   mapping[oid]={'group':g,'question_id':qid,'run_sha256':sha256(out/'runs'/g/(qid+'.json'))}
  rows=existing+additions;parts=[]
  offset=0;batch_number=0
  while offset<len(rows):
   size=20 if small_tail and offset>=1100 else batch_size
   batch=rows[offset:offset+size];p=directory/'independent-input'/f'batch-{batch_number:02d}.jsonl';value=''.join(dumps(r)+'\n' for r in batch)
   if p.exists() and p.read_text()!=value:raise BenchError('已发布匿名批次变化')
   if not p.exists():write_text(p,value)
   parts.append({'batch':batch_number,'records':len(batch),'path':str(p.relative_to(out)),'sha256':sha256(p)})
   offset+=len(batch);batch_number+=1
  if additions or not path.exists():
   write_text(path,''.join(dumps(r)+'\n' for r in rows));write_json(mapping_path,mapping)
  complete=len(rows)==len(expected)
  write_json(directory/'receipt.json',{'blind_sha256':sha256(path),'mapping_sha256':sha256(mapping_path),'instruction':m.INSTRUCTION,'schema':m.grade.SCHEMA,'source_complete':complete,'records':len(rows),'expected_records':len(expected),'method':'single_independent_ai_live_blind'})
  write_json(directory/'independent-input/receipt.json',{'source_blind_sha256':sha256(path),'source_complete':complete,'records':len(rows),'parts':parts,'policy':'仅独立AI单票；每ID唯一评分；只读分配的匿名包，不读映射、其他评分、实验材料或联网。'})
  write_json(out/'pipeline/status.json',{'stage':'independent_live_grading','published_blind_records':len(rows),'target':len(expected),'source_complete':complete,'updated_at':datetime.datetime.now().astimezone().isoformat()})
  return {'published':len(rows),'new_records':len(additions),'available_unpublished':len(candidates)-len(additions),'source_complete':complete,'batches':len(parts)}

def merge(out=OUT,staging=STAGING):
 receipt=m.read(out/'grading/independent-input/receipt.json');combined=[];parts=[];missing=[]
 for part in receipt['parts']:
  name=Path(part['path']).name;source=out/part['path'];result=staging/name;proof=result.with_suffix('.receipt.json')
  if sha256(source)!=part['sha256']:raise BenchError('匿名批次变化')
  if not result.exists() or not proof.exists():missing.append(part['batch']);continue
  rows=load_jsonl(result);original=load_jsonl(source);pr=m.read(proof)
  if len(rows)!=len(original) or len({r['id'] for r in rows})!=len(rows) or {r['id'] for r in rows}!={r['id'] for r in original}:raise BenchError('独立评分覆盖不符')
  if pr['input_sha256']!=sha256(source) or pr['output_sha256']!=sha256(result) or pr['records']!=len(rows) or pr.get('human') is not False:raise BenchError('独立评分凭据不符')
  for r in rows:
   if r.get('verdict') not in ['correct','incorrect','uncertain'] or not isinstance(r.get('reason'),str) or not r['reason'].strip():raise BenchError('独立评分格式无效')
  for src in [result,proof]:
   dst=out/'grading/independent-output'/src.name
   if dst.exists() and sha256(dst)!=sha256(src):raise BenchError('已接受评分变化')
   if not dst.exists():write_text(dst,src.read_text())
  parts.append({'batch':part['batch'],'records':len(rows),'input_sha256':sha256(source),'output_sha256':sha256(result),'receipt_sha256':sha256(proof)})
  combined+=rows
 if len({r['id'] for r in combined})!=len(combined):raise BenchError('不同批次重复评分ID')
 target=out/'jsonl/grades/independent.jsonl';write_text(target,''.join(dumps(r)+'\n' for r in combined))
 complete=receipt['source_complete'] and not missing and len(combined)==1200
 status={'source_blind_sha256':sha256(out/'grading/blind.jsonl'),'review_sha256':sha256(target),'records':len(combined),'reviewer':'independent_codex_ai','human':False,'votes_per_answer':1,'parts':parts,'missing_batches':missing,'complete':complete}
 write_json(out/'grading/independent-progress.json',status)
 if complete:write_json(out/'grading/independent-receipt.json',status)
 return {'graded':len(combined),'published':receipt['records'],'missing_batches':missing,'complete':complete}

if __name__=='__main__':
 try:
  parser=argparse.ArgumentParser();parser.add_argument('action',choices=['publish','merge'],nargs='?',default='publish');args=parser.parse_args()
  print(dumps(publish() if args.action=='publish' else merge()))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('匿名发布停止：'+str(e),file=sys.stderr);sys.exit(1)
