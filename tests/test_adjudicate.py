import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import adjudicate
from common import BenchError
class AdjudicateTests(unittest.TestCase):
 def test_binary_majority_with_abstention(self):
  for votes,result in [(('correct','incorrect','correct'),'correct'),(('incorrect','uncertain','incorrect'),'incorrect'),(('correct','correct','uncertain'),'correct'),(('correct','incorrect','uncertain'),None),(('uncertain','uncertain','correct'),None),(('uncertain',)*3,None)]:
   with self.subTest(votes=votes):self.assertEqual(adjudicate.majority(votes),result)
 def test_unanimous_and_dual_agreement(self):
  for value in ['correct','incorrect']:
   self.assertEqual(adjudicate.majority([value]*3),value)
   self.assertEqual(adjudicate.majority([value,value,'incorrect' if value=='correct' else 'correct']),value)
 def test_duplicate_or_invalid_votes_rejected(self):
  row={'id':'x','verdict':'correct','reason':'明确符合'}
  for rows in [[row,row],[dict(row,verdict='yes')],[dict(row,reason='')]]:
   with self.assertRaises(BenchError):adjudicate.indexed(rows)

class AdjudicationIntegrationTests(unittest.TestCase):
 def fixture(self,root):
  import json
  from common import write_json,write_text,dumps,sha256
  out=root/'new';source=root/'baseline'
  oldrow={'id':'old','question':'q','reference_answer':'a','aliases':[],'candidate_answer':'b'}
  newrow=dict(oldrow,id='new');fresh={'id':'fresh','question':'q2','reference_answer':'a2','aliases':[],'candidate_answer':'b2'}
  oldmap={'old':{'group':'0','question_id':'q','run_sha256':'placeholder'}}
  write_json(out/'runs/0/q.json',{'answer':'b'});write_json(out/'runs/A/q2.json',{'answer':'b2'})
  oldmap['old']['run_sha256']=sha256(out/'runs/0/q.json')
  mapping={'new':dict(oldmap['old']),'fresh':{'group':'A','question_id':'q2','run_sha256':sha256(out/'runs/A/q2.json')}}
  for p,rows,m in [(source,[oldrow],oldmap),(out,[newrow,fresh],mapping)]:
   write_text(p/'grading/blind.jsonl',''.join(dumps(x)+'\n' for x in rows));write_json(p/'grading/mapping.json',m);write_json(p/'grading/receipt.json',{'blind_sha256':sha256(p/'grading/blind.jsonl'),'mapping_sha256':sha256(p/'grading/mapping.json')})
  vote={'id':'old','verdict':'incorrect','reason':'明确矛盾'}
  write_text(source/'grading/agent-review.jsonl',dumps(vote)+'\n');write_json(source/'grading/agent-receipt.json',{'review_sha256':sha256(source/'grading/agent-review.jsonl'),'source_blind_sha256':sha256(source/'grading/blind.jsonl')})
  names=['grading/agent-review.jsonl','grading/agent-receipt.json','grading/blind.jsonl','grading/mapping.json']
  write_json(source/'baseline-record.json',{'file_sha256':{n:sha256(source/n) for n in names}});write_json(out/'manifest.json',{'baseline_record_sha256':sha256(source/'baseline-record.json')})
  write_text(out/'grading/agent-input.jsonl',dumps(fresh)+'\n');write_json(out/'grading/agent-input-receipt.json',{'sha256':sha256(out/'grading/agent-input.jsonl')})
  write_text(out/'grading/agent-review.jsonl',dumps({'id':'fresh','verdict':'uncertain','reason':'题意有歧义'})+'\n')
  for judge,values in [('claude',{'new':'correct','fresh':'correct'}),('deepseek',{'new':'incorrect','fresh':'incorrect'})]:
   rows=[]
   for oid,v in values.items():
    raw=out/'grading/raw'/judge/(oid+'.jsonl');write_text(raw,'unchanged raw\n');rows.append({'id':oid,'verdict':v,'reason':'原判分理由','raw_sha256':sha256(raw)})
   write_text(out/'jsonl/grades'/(judge+'.jsonl'),''.join(dumps(x)+'\n' for x in rows))
  return out,source,names
 def test_reuse_is_exact_and_no_binary_majority_stays_pending(self):
  import tempfile
  from common import sha256,load_jsonl
  with tempfile.TemporaryDirectory() as d:
   out,source,names=self.fixture(Path(d));before={n:sha256(source/n) for n in names}
   resolved,review=adjudicate.resolve(out,source)
   self.assertEqual(len(resolved),1);self.assertEqual(resolved[0]['id'],'new');self.assertFalse(resolved[0]['correct']);self.assertEqual(resolved[0]['resolution'],'third_vote');self.assertFalse(resolved[0]['human'])
   self.assertEqual([r['id'] for r in review],['fresh']);self.assertEqual({n:sha256(source/n) for n in names},before);self.assertFalse((out/'grading/human.jsonl').exists())
   rows=load_jsonl(out/'jsonl/grades/independent.jsonl');self.assertEqual({r['id']:r for r in rows}['new']['reused_from']['id'],'old')
 def test_source_tampering_rejected(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   out,source,_=self.fixture(Path(d));(source/'grading/agent-review.jsonl').write_text('{}\n')
   with self.assertRaises(BenchError):adjudicate.independent_votes(out,source)
 def test_new_input_must_equal_master_blind_payload(self):
  import tempfile,json
  from common import write_json,write_text,dumps,sha256
  with tempfile.TemporaryDirectory() as d:
   out,source,_=self.fixture(Path(d));p=out/'grading/agent-input.jsonl';r=json.loads(p.read_text());r['candidate_answer']='different';write_text(p,dumps(r)+'\n');write_json(out/'grading/agent-input-receipt.json',{'sha256':sha256(p)})
   with self.assertRaises(BenchError):adjudicate.independent_votes(out,source)

if __name__=='__main__':unittest.main()
