"""不搜索诊断的复用校验；不调用真实模型。"""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import common,baseline

class BaselineTests(unittest.TestCase):
 def cached(self,root):
  group={'model':'fixture','search':'none','provider':'claude'};cfg={'groups':{'0':group}}
  raw=root/'jsonl/0/q.jsonl';events=[{'type':'system','subtype':'init','tools':[]},{'type':'result','subtype':'success','result':'answer'}]
  common.write_text(raw,''.join(common.dumps(e)+'\n' for e in events))
  r={'status':'ok','group':'0','question_id':'q','model':'fixture','search_calls':0,'search_attempts':0,'tools':[],'searches':[],'raw':'jsonl/0/q.jsonl','answer':'answer'}
  common.write_json(root/'runs/0/q.json',r);return cfg,r
 def test_reuse_requires_matching_raw_and_no_tools(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cfg,r=self.cached(root)
   self.assertEqual(baseline.validate_cached(root,'0','q',cfg),r)
   r['answer']='changed';common.write_json(root/'runs/0/q.json',r)
   with self.assertRaises(common.BenchError):baseline.validate_cached(root,'0','q',cfg)
   r['answer']='answer';r['search_attempts']=1;common.write_json(root/'runs/0/q.json',r)
   with self.assertRaises(common.BenchError):baseline.validate_cached(root,'0','q',cfg)
 def test_copy_is_idempotent_and_never_overwrites(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a=root/'a';b=root/'b';a.write_text('original')
   baseline.copy_checked(a,b);baseline.copy_checked(a,b);a.write_text('changed')
   with self.assertRaises(common.BenchError):baseline.copy_checked(a,b)
   self.assertEqual(b.read_text(),'original')
 def test_resume_only_calls_missing_questions(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);out=root/'out';cfg={'groups':{g:{'search':'none'} for g in baseline.GROUPS}};questions=[{'id':qid,'question':'q'} for qid in ['old','new']]
   for g in baseline.GROUPS:common.write_json(out/'runs'/g/'old.json',{'status':'ok'})
   calls=[]
   def fake(q,g,group,cfg,out,timeout):
    calls.append((g,q['id']));r={'group':g,'question_id':q['id'],'status':'ok','elapsed_seconds':0};common.write_json(out/'runs'/g/(q['id']+'.json'),r);return r
   with patch.object(baseline,'ROOT',root),patch.object(baseline,'prepare',return_value=4),patch.object(baseline.subprocess,'check_output',return_value='fixture'),patch.object(baseline.bench,'execute_one',side_effect=fake):
    baseline.run(out,root/'source',questions,cfg,4,10)
    baseline.run(out,root/'source',questions,cfg,4,10)
   self.assertCountEqual(calls,[(g,'new') for g in baseline.GROUPS])
 def test_reuse_blind_grades_preserves_payload_and_skips_calls(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'pilot';out=root/'baseline';cfg,r=self.cached(source)
   q={'id':'q','question':'question','answer':'answer','aliases':[]};common.write_text(root/'questions/questions.jsonl',common.dumps(q)+'\n')
   manifest={'config':cfg,'question_sha256':common.sha256(root/'questions/questions.jsonl'),'question_ids':['q'],'all_groups':['0'],'seed':42}
   for target in [source,out]:
    common.write_json(target/'manifest.json',manifest)
   baseline.copy_checked(source/'runs/0/q.json',out/'runs/0/q.json')
   for name in ['baseline.py','bench.py','grade.py','common.py']:common.write_text(root/'tools'/name,'fixture')
   with patch.object(baseline.grade,'ROOT',root),patch.object(baseline,'ROOT',root):
    baseline.grade.prepare(source);oldid=common.load_jsonl(source/'grading/blind.jsonl')[0]['id']
    verdict={'verdict':'correct','reason':'same answer'}
    events=[{'type':'system','subtype':'init','tools':['StructuredOutput']},{'type':'result','subtype':'success','result':'','structured_output':verdict}]
    for judge in ['claude','deepseek']:
     raw=source/'grading/raw'/judge/(oldid+'.jsonl');common.write_text(raw,''.join(common.dumps(e)+'\n' for e in events))
     common.write_text(source/'jsonl/grades'/(judge+'.jsonl'),common.dumps(dict(verdict,id=oldid,raw_sha256=common.sha256(raw)))+'\n')
    baseline.prepare_grades(out,source);baseline.prepare_grades(out,source)
    for judge in ['claude','deepseek']:
     rows=common.load_jsonl(out/'jsonl/grades'/(judge+'.jsonl'));self.assertEqual(len(rows),1)
     self.assertNotEqual(rows[0]['id'],oldid);self.assertEqual(rows[0]['reused_pilot_id'],oldid)
     self.assertEqual(rows[0]['raw_sha256'],common.sha256(out/'grading/raw'/judge/(rows[0]['id']+'.jsonl')))
if __name__=='__main__':unittest.main()
