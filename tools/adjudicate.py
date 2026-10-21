#!/usr/bin/env python3
"""按用户后续授权合并第三位独立盲审；保留原双判分与人工复核文件。"""
import argparse,collections,json,sys
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256
VERDICTS={'correct','incorrect','uncertain'}

def indexed(rows):
 result={}
 for r in rows:
  if not isinstance(r.get('id'),str) or r['id'] in result or r.get('verdict') not in VERDICTS or not isinstance(r.get('reason'),str) or not r['reason'].strip():raise BenchError('独立判分ID、类别或理由无效。')
  result[r['id']]=r
 return result

def checked_package(out):
 receipt=json.loads((out/'grading/receipt.json').read_text())
 for name in ['blind','mapping']:
  path=out/'grading'/('blind.jsonl' if name=='blind' else 'mapping.json')
  if receipt[name+'_sha256']!=sha256(path):raise BenchError('匿名判分包散列不同。')
 blind={r['id']:r for r in load_jsonl(out/'grading/blind.jsonl')};mapping=json.loads((out/'grading/mapping.json').read_text())
 if set(blind)!=set(mapping):raise BenchError('匿名包ID与映射不同。')
 return blind,mapping

def independent_votes(out,source):
 blind,mapping=checked_package(out);oldblind,oldmap=checked_package(source)
 manifest=json.loads((out/'manifest.json').read_text())
 if manifest['baseline_record_sha256']!=sha256(source/'baseline-record.json'):raise BenchError('baseline快照凭据变化。')
 record=json.loads((source/'baseline-record.json').read_text())
 for name in ['grading/agent-review.jsonl','grading/agent-receipt.json','grading/blind.jsonl','grading/mapping.json']:
  if record['file_sha256'].get(name)!=sha256(source/name):raise BenchError('baseline独立复核来源与快照不同。')
 oldpath=source/'grading/agent-review.jsonl';oldreceipt=json.loads((source/'grading/agent-receipt.json').read_text())
 if oldreceipt['review_sha256']!=sha256(oldpath) or oldreceipt['source_blind_sha256']!=sha256(source/'grading/blind.jsonl'):raise BenchError('baseline独立盲审凭据不同。')
 old=indexed(load_jsonl(oldpath));newpath=out/'grading/agent-review.jsonl';new=indexed(load_jsonl(newpath))
 if set(old)!=set(oldmap):raise BenchError('baseline独立盲审未完整覆盖。')
 lookup={(v['group'],v['question_id']):k for k,v in oldmap.items()}
 votes={};reused=0
 for oid,m in mapping.items():
  oldid=lookup.get((m['group'],m['question_id']))
  if oldid is not None:
   if m['run_sha256']!=oldmap[oldid]['run_sha256'] or {k:v for k,v in blind[oid].items() if k!='id'}!={k:v for k,v in oldblind[oldid].items() if k!='id'}:raise BenchError('独立复核复用材料不一致。')
   votes[oid]=dict(old[oldid],id=oid,reused_from={'phase':'baseline','id':oldid});reused+=1
  elif oid in new:votes[oid]=new[oid]
  else:raise BenchError('新增独立盲审尚未完整覆盖。')
 expected=set(mapping)-{oid for oid,m in mapping.items() if (m['group'],m['question_id']) in lookup}
 if set(new)!=expected:raise BenchError('新增独立盲审含遗漏、重复或无关ID。')
 input_path=out/'grading/agent-input.jsonl';input_receipt=json.loads((out/'grading/agent-input-receipt.json').read_text());inputs={r['id']:r for r in load_jsonl(input_path)}
 if input_receipt['sha256']!=sha256(input_path) or set(inputs)!=expected or any(inputs[x]!=blind[x] for x in inputs):raise BenchError('新增独立盲审输入与匿名包不一致。')
 target=out/'jsonl/grades/independent.jsonl';write_text(target,''.join(dumps(r)+'\n' for r in votes.values()))
 write_json(out/'grading/independent-receipt.json',{'role':'独立AI盲审，非人工','baseline_reused':reused,'new_records':len(new),'records':len(votes),'baseline_review_sha256':sha256(oldpath),'new_review_sha256':sha256(newpath),'input_sha256':sha256(input_path),'combined_sha256':sha256(target)})
 return votes

def majority(verdicts):
 c=collections.Counter(verdicts)
 for value in ['correct','incorrect']:
  if c[value]>=2:return value
 return None

def resolve(out,source):
 third=independent_votes(out,source);blind,mapping=checked_package(out)
 judges={name:indexed(load_jsonl(out/'jsonl/grades'/(name+'.jsonl'))) for name in ['claude','deepseek']};judges['independent']=third
 if any(set(rows)!=set(mapping) for rows in judges.values()):raise BenchError('判分尚未完整覆盖。')
 for name in ['claude','deepseek']:
  for oid,row in judges[name].items():
   if sha256(out/'grading/raw'/name/(oid+'.jsonl'))!=row['raw_sha256']:raise BenchError('正式判分原文散列不同。')
 resolved=[];review=[]
 for oid,m in mapping.items():
  if sha256(out/'runs'/m['group']/(m['question_id']+'.json'))!=m['run_sha256']:raise BenchError('作答结果与匿名包不同。')
  votes={name:rows[oid]['verdict'] for name,rows in judges.items()};v=majority(votes.values());dual=judges['claude'][oid]['verdict']==judges['deepseek'][oid]['verdict'] and judges['claude'][oid]['verdict']!='uncertain'
  if v:resolved.append(dict(m,id=oid,correct=v=='correct',votes=votes,method='ai_majority',resolution='dual_agreement' if dual else 'third_vote',human=False))
  else:review.append(dict(blind[oid],judges={name:rows[oid] for name,rows in judges.items()},verdict=None,reason='三票中没有两个相同的correct/incorrect，保留待核。'))
 write_text(out/'grading/majority-resolved.jsonl',''.join(dumps(r)+'\n' for r in resolved));write_text(out/'grading/majority-needs-review.jsonl',''.join(dumps(r)+'\n' for r in review))
 write_json(out/'grading/majority-receipt.json',{'method':'AI三票多数；只有至少两票correct或incorrect才裁决，其余待核','user_authorized_change':'用户在正式作答完成、双判启动后授权第三位独立agent及2比1裁决；新增口径单列，不改baseline与原双判结果。','tool_sha256':sha256(ROOT/'tools/adjudicate.py'),'resolved':len(resolved),'needs_review':len(review),'third_vote_resolved':sum(r['resolution']=='third_vote' for r in resolved),'majority_resolved_sha256':sha256(out/'grading/majority-resolved.jsonl'),'majority_needs_review_sha256':sha256(out/'grading/majority-needs-review.jsonl')})
 return resolved,review

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['resolve']);a=p.parse_args()
 resolved,review=resolve(ROOT/'tmp/archive',ROOT/'tmp/baseline');print(dumps({'majority_resolved':len(resolved),'needs_review':len(review)}))
if __name__=='__main__':
 try:main()
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
