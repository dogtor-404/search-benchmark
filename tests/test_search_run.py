"""正式搜索的基线复用、续跑与全局停机回归；不调用真实模型。"""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import common,search_run,bench,baseline

class SearchRunTests(unittest.TestCase):
 def source(self,root):
  cfg=json.loads((ROOT/'tools/config.json').read_text());common.write_json(root/'tools/config.json',cfg);q={'id':'q','question':'fixture','answer':'answer','aliases':[]};common.write_text(root/'questions/questions.jsonl',common.dumps(q)+'\n');source=root/'baseline';hashes={}
  for g in baseline.GROUPS:
   events=[{'type':'system','subtype':'init','tools':[]},{'type':'result','subtype':'success','result':'answer'}];raw=source/'jsonl'/g/'q.jsonl';common.write_text(raw,''.join(common.dumps(e)+'\n' for e in events));meta=source/'runs'/g/'q.json';common.write_json(meta,{'status':'ok','group':g,'question_id':'q','model':cfg['groups'][g]['model'],'search_calls':0,'search_attempts':0,'tools':[],'searches':[],'raw':f'jsonl/{g}/q.jsonl','answer':'answer'})
   for f in [meta,raw]:hashes[str(f.relative_to(source))]=common.sha256(f)
  m={'all_groups':baseline.GROUPS,'question_ids':['q'],'question_sha256':common.sha256(root/'questions/questions.jsonl'),'config_sha256':common.sha256(root/'tools/config.json'),'config':cfg,'claude_code_version':'fixture'};common.write_json(source/'manifest.json',m);common.write_json(source/'baseline-record.json',{'question_sha256':m['question_sha256'],'config_sha256':m['config_sha256'],'file_sha256':hashes});return source,[q],cfg
 def test_baseline_is_copied_without_calling_models(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source,qs,cfg=self.source(root);out=root/'archive'
   with patch.object(search_run,'ROOT',root),patch.object(bench,'CONFIG',root/'tools/config.json'):
    self.assertEqual(search_run.prepare(out,source,qs,cfg,'fixture'),4);self.assertEqual(search_run.prepare(out,source,qs,cfg,'fixture'),4)
   for g in baseline.GROUPS:self.assertEqual((source/'runs'/g/'q.json').read_bytes(),(out/'runs'/g/'q.json').read_bytes())
   m=json.loads((out/'manifest.json').read_text());self.assertEqual(m['phase'],'full');self.assertEqual(len(m['all_groups']),10);self.assertFalse(m['pilot_search_results_reused'])
 def test_source_tampering_and_version_drift_are_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source,qs,cfg=self.source(root)
   with patch.object(search_run,'ROOT',root),patch.object(bench,'CONFIG',root/'tools/config.json'):
    with self.assertRaises(common.BenchError):search_run.validate_source(source,qs,cfg,'different')
    (source/'jsonl/0/q.jsonl').write_text('modified')
    with self.assertRaises(common.BenchError):search_run.validate_source(source,qs,cfg,'fixture')
 def test_existing_search_requires_raw_and_audit_consistency(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);cfg=json.loads((ROOT/'tools/config.json').read_text());q={'id':'q'};events=[{'type':'system','subtype':'init','tools':['mcp__deepseek-search__search']},{'type':'result','subtype':'success','result':'answer'}];common.write_text(out/'jsonl/B/q.jsonl',''.join(common.dumps(e)+'\n' for e in events));r={'status':'ok','group':'B','question_id':'q','model':cfg['groups']['B']['model'],'answer':'answer','search_calls':0,'search_attempts':0,'search_budget_denials':0,'tools':['mcp__deepseek-search__search']};common.write_json(out/'runs/B/q.json',r)
   self.assertEqual(search_run.validate_search_result(out,'B',q,cfg),r)
   r['search_attempts']=1;common.write_json(out/'runs/B/q.json',r)
   with self.assertRaises(common.BenchError):search_run.validate_search_result(out,'B',q,cfg)
 def test_failure_stops_future_questions_and_other_groups(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cfg=json.loads((ROOT/'tools/config.json').read_text());qs=[{'id':'first'},{'id':'later'}];out=root/'archive';calls=[]
   def fake(q,g,group,cfg,out,timeout):
    calls.append((g,q['id']));r={'group':g,'question_id':q['id'],'status':'failed','elapsed_seconds':0};common.write_json(out/'runs'/g/(q['id']+'.json'),r);return r
   with patch.object(search_run,'ROOT',root),patch.object(search_run,'prepare',return_value=400),patch.object(search_run.subprocess,'check_output',return_value='fixture'),patch.object(bench,'execute_one',side_effect=fake):
    with self.assertRaises(common.BenchError):search_run.run(out,root/'source',qs,cfg,1,10)
   self.assertEqual(calls,[('A','first')]);self.assertTrue((out/'audit/A/first/dispatch.json').exists())
 def test_reused_baseline_grades_remain_blind_and_not_recalled(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source,qs,cfg=self.source(root);out=root/'archive'
   for name in ['search_run.py','bench.py','grade.py','common.py']:common.write_text(root/'tools'/name,'fixture')
   m=json.loads((source/'manifest.json').read_text());m['seed']=42;common.write_json(source/'manifest.json',m)
   target=dict(m,all_groups=list(cfg['groups']));common.write_json(out/'manifest.json',target)
   for g in cfg['groups']:
    if g in baseline.GROUPS:baseline.copy_checked(source/'runs'/g/'q.json',out/'runs'/g/'q.json')
    else:common.write_json(out/'runs'/g/'q.json',{'status':'ok','answer':'answer'})
   with patch.object(search_run,'ROOT',root),patch.object(search_run.grade,'ROOT',root):
    search_run.grade.prepare(source);oldmap=json.loads((source/'grading/mapping.json').read_text())
    for judge in ['claude','deepseek']:
     rows=[]
     for oid,detail in oldmap.items():
      verdict={'verdict':'uncertain' if detail['group']=='0' else 'correct','reason':'fixture'};events=[{'type':'system','subtype':'init','tools':['StructuredOutput']},{'type':'result','subtype':'success','result':'','structured_output':verdict}];raw=source/'grading/raw'/judge/(oid+'.jsonl');common.write_text(raw,''.join(common.dumps(e)+'\n' for e in events));rows.append(dict(verdict,id=oid,raw_sha256=common.sha256(raw)))
     common.write_text(source/'jsonl/grades'/(judge+'.jsonl'),''.join(common.dumps(r)+'\n' for r in rows))
    with patch.object(search_run.grade,'keychain_key',side_effect=AssertionError('不得读取凭据')),patch.object(search_run.grade.subprocess,'run',side_effect=AssertionError('不得重复判分')):
     search_run.prepare_grades(out,source);search_run.prepare_grades(out,source)
    for judge in ['claude','deepseek']:
     rows=common.load_jsonl(out/'jsonl/grades'/(judge+'.jsonl'));self.assertEqual(len(rows),4);self.assertEqual(sum(r['verdict']=='uncertain' for r in rows),1)
     self.assertTrue(all(r['reused_from']['phase']=='baseline' and r['id'] not in oldmap for r in rows))
if __name__=='__main__':unittest.main()
