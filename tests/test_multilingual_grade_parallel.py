import collections,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import multilingual_grade_parallel as pg
from common import load_jsonl,write_json,write_text,sha256,dumps,BenchError

class ParallelGradeTests(unittest.TestCase):
 def fixture(self,path,n=12):
  rows=[{'id':f'case{i}','question':f'คำถาม{i}','reference_answer':'金答案','aliases':[],'candidate_answer':'候选回答'} for i in range(n)]
  write_json(path/'manifest.json',{'config':{'judges':{'claude':'test-model'}}})
  write_text(path/'grading/blind.jsonl',''.join(dumps(r)+'\n' for r in rows))
  write_json(path/'grading/receipt.json',{'blind_sha256':sha256(path/'grading/blind.jsonl'),'instruction':pg.multilingual.INSTRUCTION,'schema':pg.grade.SCHEMA})
  return rows
 def fake_run(self,job,judge,execute,quota,timeout):
  rows=load_jsonl(job/'grading/blind.jsonl');self.assertEqual(len(rows),1);r=rows[0]
  self.assertEqual(set(r),{'id','question','reference_answer','aliases','candidate_answer'})
  time.sleep(int(r['id'][4:])%3*.001)
  value={'verdict':'correct','reason':'与标准答案等价'}
  raw=job/'grading/raw'/judge/(r['id']+'.jsonl')
  write_text(raw,'\n'.join(dumps(e) for e in [{'type':'system','subtype':'init','tools':['StructuredOutput'],'model':'test-model'},{'type':'result','subtype':'success','result':'','structured_output':value}])+'\n')
  write_text(job/'jsonl/grades'/(judge+'.jsonl'),dumps(dict(value,id=r['id'],raw_sha256=sha256(raw),reported_cost_usd=.01))+'\n')
 def test_parallel_exact_coverage_and_resume_without_calls(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);rows=self.fixture(p)
   with patch.object(pg.grade,'run',side_effect=self.fake_run) as invoke:self.assertEqual(pg.execute(p,'claude',4,30),12);self.assertEqual(invoke.call_count,12)
   grades=load_jsonl(p/'jsonl/grades/claude.jsonl');self.assertEqual({r['id'] for r in grades},{r['id'] for r in rows});self.assertEqual(len(grades),12)
   before=sha256(p/'jsonl/grades/claude.jsonl')
   with patch.object(pg.grade,'run') as invoke:self.assertEqual(pg.execute(p,'claude',4,30),12);invoke.assert_not_called()
   self.assertEqual(sha256(p/'jsonl/grades/claude.jsonl'),before)
 def test_changed_input_is_not_silently_reused(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);self.fixture(p,1)
   with patch.object(pg.grade,'run',side_effect=self.fake_run):pg.execute(p,'claude',1,30)
   rows=load_jsonl(p/'grading/blind.jsonl');rows[0]['candidate_answer']='另一回答';write_text(p/'grading/blind.jsonl',dumps(rows[0])+'\n')
   rec=json.loads((p/'grading/receipt.json').read_text());rec['blind_sha256']=sha256(p/'grading/blind.jsonl');write_json(p/'grading/receipt.json',rec)
   with patch.object(pg.grade,'run') as invoke,self.assertRaises(BenchError):pg.execute(p,'claude',1,30)
   invoke.assert_not_called()
 def test_changed_raw_blocks_without_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);self.fixture(p,1)
   with patch.object(pg.grade,'run',side_effect=self.fake_run):pg.execute(p,'claude',1,30)
   raw=p/'grading/raw/claude/case0.jsonl';write_text(raw,'damaged\n')
   with patch.object(pg.grade,'run') as invoke,self.assertRaises(BenchError):pg.execute(p,'claude',1,30)
   invoke.assert_not_called();self.assertEqual(raw.read_text(),'damaged\n')
 def test_failure_preserves_raw_and_stops_new_jobs(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);self.fixture(p,20);calls=[]
   def fail(job,*args):
    oid=load_jsonl(job/'grading/blind.jsonl')[0]['id'];calls.append(oid)
    if oid=='case0':
     write_text(job/'grading/raw/claude/case0.jsonl','API failed\n');raise BenchError('模拟故障')
    time.sleep(.03);self.fake_run(job,*args)
   with patch.object(pg.grade,'run',side_effect=fail),self.assertRaises(BenchError):pg.execute(p,'claude',4,30)
   self.assertLessEqual(len(calls),4);self.assertEqual((p/'grading/jobs/claude/case0/grading/raw/claude/case0.jsonl').read_text(),'API failed\n')
 def test_other_model_or_tool_cannot_pass_as_same_judge(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);self.fixture(p,1)
   def wrong(job,*args):
    self.fake_run(job,*args);raw=job/'grading/raw/claude/case0.jsonl';events=load_jsonl(raw);events[0]['model']='wrong-model';write_text(raw,''.join(dumps(e)+'\n' for e in events));g=load_jsonl(job/'jsonl/grades/claude.jsonl')[0];g['raw_sha256']=sha256(raw);write_text(job/'jsonl/grades/claude.jsonl',dumps(g)+'\n')
   with patch.object(pg.grade,'run',side_effect=wrong),self.assertRaises(BenchError):pg.execute(p,'claude',1,30)
if __name__=='__main__':unittest.main()
