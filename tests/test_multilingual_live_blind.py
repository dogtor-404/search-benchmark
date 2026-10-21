import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import multilingual_live_blind as live
import multilingual_single_report as single
from common import write_json,write_text,sha256,load_jsonl,dumps,BenchError

class LiveBlindTests(unittest.TestCase):
 def setup_run(self,root,n=4):
  out=root/'tmp/archive-multilingual';qfile=root/'questions/frozen.jsonl';qs=[{'id':f'q{i}','question':f'คำถาม{i}','answer':'答案','aliases':[]} for i in range(n)]
  write_text(qfile,''.join(dumps(q)+'\n' for q in qs));write_json(out/'manifest.json',{'question_file':'questions/frozen.jsonl','question_sha256':sha256(qfile),'all_groups':['private_group'],'question_ids':[q['id'] for q in qs],'config':{}})
  for q in qs:write_json(out/'runs/private_group'/(q['id']+'.json'),{'status':'ok','answer':'候选'+q['id']})
  return out
 def check(self,out,g,q,cfg):return json.loads((out/'runs'/g/(q['id']+'.json')).read_text())
 def test_append_only_unique_blind_batches_and_resume(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=self.setup_run(root);(out/'runs/private_group/q3.json').unlink()
   with patch.object(live,'ROOT',root),patch.object(live.m,'check_run',self.check):
    result=live.publish(out,2);self.assertEqual(result['published'],2);self.assertEqual(result['available_unpublished'],1)
    first=out/'grading/independent-input/batch-00.jsonl';digest=sha256(first);ids={r['id'] for r in load_jsonl(first)}
    self.assertEqual(live.publish(out,2)['new_records'],0)
    write_json(out/'runs/private_group/q3.json',{'status':'ok','answer':'新候选'});result=live.publish(out,2)
   self.assertTrue(result['source_complete']);self.assertEqual(result['published'],4);self.assertEqual(digest,sha256(first))
   rows=load_jsonl(out/'grading/blind.jsonl');self.assertEqual(len({r['id'] for r in rows}),4);self.assertTrue(ids<={r['id'] for r in rows});self.assertNotIn('private_group',(out/'grading/blind.jsonl').read_text())
 def test_refuses_change_to_published_answer_or_batch(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=self.setup_run(root)
   with patch.object(live,'ROOT',root),patch.object(live.m,'check_run',self.check):
    live.publish(out,2);write_json(out/'runs/private_group/q0.json',{'status':'ok','answer':'替换'})
    with self.assertRaises(BenchError):live.publish(out,2)
 def test_failed_answers_are_not_sent_to_judge(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=self.setup_run(root);write_json(out/'runs/private_group/q0.json',{'status':'failed','answer':'不应评分'})
   with patch.object(live,'ROOT',root),patch.object(live.m,'check_run',self.check):result=live.publish(out,2)
   self.assertEqual(result['published'],2);self.assertNotIn('不应评分',(out/'grading/blind.jsonl').read_text())
 def test_final_hundred_uses_twenty_record_immutable_batches(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=self.setup_run(root,1200)
   for i in range(1130,1200):(out/'runs/private_group'/f'q{i}.json').unlink()
   with patch.object(live,'ROOT',root),patch.object(live.m,'check_run',self.check):
    r=live.publish(out);self.assertEqual(r['published'],1120);first=out/'grading/independent-input/batch-00.jsonl';tail=out/'grading/independent-input/batch-11.jsonl';digests=[sha256(first),sha256(tail)];self.assertEqual(len(load_jsonl(tail)),20)
    for i in range(1130,1200):write_json(out/'runs/private_group'/f'q{i}.json',{'status':'ok','answer':'候选'})
    r=live.publish(out);self.assertEqual(r['published'],1200);self.assertTrue(r['source_complete']);self.assertEqual(r['batches'],16);self.assertEqual(digests,[sha256(first),sha256(tail)])
   parts=json.loads((out/'grading/independent-input/receipt.json').read_text())['parts'];self.assertEqual([r['records'] for r in parts],[100]*11+[20]*5);self.assertEqual(len({r['id'] for r in load_jsonl(out/'grading/blind.jsonl')}),1200)
 def test_merge_requires_exact_ids_receipts_and_immutable_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);out=self.setup_run(root);staging=root/'staging'
   with patch.object(live,'ROOT',root),patch.object(live.m,'check_run',self.check):live.publish(out,2)
   source=out/'grading/independent-input/batch-00.jsonl';rows=[{'id':r['id'],'verdict':'correct','reason':'实体一致'} for r in load_jsonl(source)];target=staging/source.name;write_text(target,''.join(dumps(r)+'\n' for r in rows));proof=target.with_suffix('.receipt.json');write_json(proof,{'input_sha256':sha256(source),'output_sha256':sha256(target),'records':2,'human':False})
   r=live.merge(out,staging);self.assertEqual(r['graded'],2);self.assertEqual(r['missing_batches'],[1]);self.assertFalse(r['complete']);self.assertFalse((out/'grading/independent-receipt.json').exists())
   rows[0]['id']='wrong';write_text(target,''.join(dumps(r)+'\n' for r in rows))
   with self.assertRaises(BenchError):live.merge(out,staging)
 def test_tariff_calculation_does_not_charge_api_judging(self):
  groups={g:{'resources':{'n':1,'mean_main_reported_input_tokens':1000000,'mean_main_cache_read_tokens':0,'mean_main_output_tokens':1000000}} for g in ['D0','D2','D0_prime','D2_prime']};r=single.price_estimate({'groups':groups})
  self.assertAlmostEqual(r['model_estimate_all_offpeak'],6.78);self.assertAlmostEqual(r['model_estimate_all_peak'],13.56);self.assertEqual(r['api_judging_cost_usd'],0)
 def test_offpeak_proof_converts_utc_and_does_not_assume_holidays(self):
  self.assertTrue(single.outside_peak_clock('2026-10-21T00:00:00+00:00','2026-10-21T00:59:59+00:00'))
  self.assertFalse(single.outside_peak_clock('2026-10-21T00:59:59+00:00','2026-10-21T01:00:01+00:00'))
  self.assertTrue(single.outside_peak_clock('2026-10-21T04:00:00+00:00','2026-10-21T05:00:00+00:00'))
  self.assertTrue(single.outside_peak_clock('2026-10-21T10:00:00+00:00','2026-10-21T11:00:00+00:00'))
  self.assertFalse(single.outside_peak_clock('2026-10-21T15:59:59+00:00','2026-10-21T16:00:01+00:00'))
  with self.assertRaises(BenchError):single.outside_peak_clock('2026-10-21T01:00:00+00:00','2026-10-21T00:00:00+00:00')
 def test_single_resolution_preserves_uncertain_without_fake_majority(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);blind=[{'id':str(i),'question':'问','reference_answer':'答','aliases':[],'candidate_answer':'候选'} for i in range(1200)];votes=[{'id':str(i),'verdict':'uncertain' if i==0 else 'correct','reason':'待核' if i==0 else '一致'} for i in range(1200)];mapping={str(i):{'group':'g','question_id':'q'+str(i),'run_sha256':'hash'} for i in range(1200)}
   fixtures={'policy.json':{'method':'single_independent_ai_live_blind','api_judges_enabled':[]},'receipt.json':{'source_complete':True,'blind_sha256':'hash','mapping_sha256':'hash'},'independent-receipt.json':{'source_blind_sha256':'hash','review_sha256':'hash','votes_per_answer':1,'complete':True},'mapping.json':mapping}
   parts=[{'path':f'grading/independent-input/batch-{i:02d}.jsonl','sha256':'hash'} for i in range(12)]
   def read(path):
    if path.parent.name=='independent-input' and path.name=='receipt.json':return {'source_complete':True,'source_blind_sha256':'hash','parts':parts}
    if path.name.endswith('.receipt.json'):return {'input_sha256':'hash','output_sha256':'hash','records':100}
    return fixtures[path.name]
   def load(path):
    if path.name=='blind.jsonl':return blind
    if path.name=='independent.jsonl':return votes
    if path.name.startswith('batch-'):
     start=int(path.stem.split('-')[1])*100;return (blind if path.parent.name=='independent-input' else votes)[start:start+100]
    return [{'id':'q'+str(i),'source_urls':['https://example.org']} for i in range(1200)]
   with patch.object(single.m,'read',read),patch.object(single,'load_jsonl',load),patch.object(single,'sha256',return_value='hash'):
    resolved,pending=single.resolve_single(out)
   self.assertEqual((len(resolved),len(pending)),(1199,1));self.assertEqual(resolved[0]['method'],'independent_ai_single');self.assertEqual(resolved[0]['votes'],{'independent':'correct'});self.assertEqual(pending[0]['source_urls'],['https://example.org']);self.assertFalse((out/'grading/majority-resolved.jsonl').exists())
if __name__=='__main__':unittest.main()
