import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import multilingual_search_efficiency as eff
from common import BenchError

class SearchEfficiencyTests(unittest.TestCase):
 def test_five_point_penalty_and_zero_floor(self):
  self.assertEqual([eff.score('correct',n) for n in range(6)],[100,100,95,90,85,80])
  self.assertEqual([eff.score('incorrect',n) for n in range(6)],[0]*6)
  self.assertIsNone(eff.score('uncertain',5));self.assertIsNone(eff.score(None,2))
  for n in [-1,6,True,1.5]:
   with self.assertRaises(BenchError):eff.score('correct',n)
 def test_unknown_upper_bound_uses_observed_search_cost_and_ungraded_is_separate(self):
  rows=[{'group':'A','verdict':v,'search_calls':c,'adjusted_score':eff.score(v,c),'search_attempts':c,'budget_denials':0,'argument_rejections':0} for v,c in [('correct',2),('incorrect',5),('uncertain',5),(None,1)]]
  s=eff.summarize(rows,['A'])['A'];self.assertEqual((s['answered'],s['graded'],s['ungraded'],s['uncertain']),(4,3,1,1));self.assertEqual(s['adjusted_score_bounds_on_graded'],[95/3,175/3]);self.assertEqual(s['deduction_on_known_correct_total'],5)
 def test_denied_search_is_not_a_return_or_penalty_and_duplicate_stream_ids_are_deduped(self):
  blocks=[{'type':'tool_use','id':'one','name':'WebSearch','input':{'query':'query1'}},{'type':'tool_use','id':'two','name':'WebSearch','input':{'query':'query2'}},{'type':'tool_use','id':'denied','name':'WebSearch','input':{'query':'query3'}},{'type':'tool_result','tool_use_id':'two','content':[{'type':'text','text':'ไทย'}]},{'type':'tool_result','tool_use_id':'one','content':'first'},{'type':'tool_result','tool_use_id':'denied','is_error':True,'content':'budget exceeded'}]
  events=[{'message':{'content':blocks}},{'message':{'content':[blocks[0],blocks[4]]}}];rows=eff.search_details(events,{'search_calls':2,'searches':[{'query':'query1'},{'query':'query2'}]});self.assertEqual([r['query'] for r in rows],['query1','query2']);self.assertEqual(rows[1]['returned_utf8_bytes'],len('ไทย'.encode()));self.assertEqual(rows[0]['returned_text'],'first')
 def test_continuous_score_difference_is_not_booleanized(self):
  rows=[{'group':g,'question_id':q,'search_calls':c,'adjusted_score':eff.score('correct',c)} for q in ['q1','q2'] for g,c in [('A',5),('B',1)]]
  r=eff.comparisons(rows,['q1','q2'])['A__B'];self.assertEqual(r['all_question_difference_bounds_points'],[20,20]);self.assertEqual(r['conditional_bootstrap_points']['estimate'],20);self.assertEqual(r['conditional_bootstrap_points']['ci95'],[20,20])
if __name__=='__main__':unittest.main()
