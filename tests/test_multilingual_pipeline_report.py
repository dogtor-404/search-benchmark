import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import multilingual_pipeline as pipe
import multilingual_report as report
from common import write_json,write_text,load_jsonl,sha256,dumps,BenchError

class PipelineReportTests(unittest.TestCase):
 def test_input_batches_cover_same_opaque_ids_without_mapping(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);rows=[{'id':f'opaque{i}','question':'คำถาม','reference_answer':'答','aliases':[],'candidate_answer':'候选'} for i in range(1200)];write_text(out/'grading/blind.jsonl',''.join(dumps(r)+'\n' for r in rows))
   with patch.object(pipe,'OUT',out):pipe.split_blind()
   rec=json.loads((out/'grading/independent-input/receipt.json').read_text());self.assertEqual(rec['source_blind_sha256'],sha256(out/'grading/blind.jsonl'));combined=[]
   for r in rec['parts']:
    path=out/r['path'];self.assertEqual(r['sha256'],sha256(path));part=load_jsonl(path);self.assertEqual(len(part),100);combined+=part
   self.assertEqual(combined,rows);self.assertEqual(len({r['id'] for r in combined}),1200)
 def test_failed_answer_never_launches_judges(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);write_json(out/'manifest.json',{'question_ids':list(range(120)),'all_groups':list(range(10))});write_json(out/'runs/g/q.json',{'group':'g','question_id':'q','status':'failed','error':'故障'})
   with patch.object(pipe,'OUT',out),patch.object(pipe.subprocess,'run') as run,patch.object(pipe.subprocess,'Popen') as popen,self.assertRaises(BenchError):pipe.main()
   run.assert_not_called();popen.assert_not_called();state=json.loads((out/'pipeline/status.json').read_text());self.assertEqual(state['stage'],'answer_failure_needs_review')
 def test_cross_round_bootstrap_uses_each_round_denominator(self):
  r=report.cross_bootstrap([1]*5,[0]*2,draws=40);self.assertEqual(r['estimate'],1);self.assertEqual(r['ci95'],[1,1]);self.assertEqual((r['new_n'],r['old_n']),(5,2))
  self.assertIsNone(report.cross_bootstrap([],[-1]))
 def make_old(self,root):
  q=root/'questions/questions.jsonl';write_text(q,dumps({'id':'oldzh','lang':'zh'})+'\n'+dumps({'id':'olden','lang':'en'})+'\n')
  old=root/'tmp/archive';write_json(old/'manifest.json',{'question_ids':['oldzh','olden'],'question_sha256':sha256(q)})
  records=[{'group':g,'question_id':qid,'correct':c} for qid in ['oldzh','olden'] for g,c in [('A',0),('B',1),('A_prime',1),('B_prime',0)]];write_text(old/'grading/majority-resolved.jsonl',''.join(dumps(r)+'\n' for r in records));return q
 def test_cross_round_keeps_unknown_values_as_bounds(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);self.make_old(root);table={('A','new'):0,('A_prime','new'):0,('B_prime','new'):1}
   with patch.object(report,'ROOT',root):result=report.cross_round(root,{'question_ids':['new']},{},table)
   r=result['comparisons']['A__B']['zh'];self.assertEqual(r['first_deepseek_minus_claude_bounds'],[1,1]);self.assertEqual(r['second_deepseek_minus_claude_bounds'],[0,1]);self.assertEqual(r['second_minus_first_bounds'],[-1,0]);self.assertIsNone(r['conditional_cross_bootstrap'])
 def test_cross_round_rejects_drifted_first_question_bank(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);q=self.make_old(root);q.write_text(q.read_text()+'\n')
   with patch.object(report,'ROOT',root),self.assertRaises(BenchError):report.cross_round(root,{'question_ids':['new']},{},{})
if __name__=='__main__':unittest.main()
