import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import report
class ReportTests(unittest.TestCase):
 def test_pending_bounds_do_not_become_errors(self):
  table={('a','q1'):0,('b','q1'):1,('a','q2'):1}
  self.assertEqual(report.contrast_bounds(table,['q1','q2'],[('b',1),('a',-1)]),[0,0.5])
 def test_p_range_enumerates_unknown_binary_outcomes(self):
  table={('a','q1'):0,('b','q1'):1,('a','q2'):0,('b','q2'):1,('a','q3'):0,('b','q3'):1,('b','q4'):1}
  r=report.paired(table,['q1','q2','q3','q4'],'a','b')
  self.assertEqual(r['complete_pairs_n'],3);self.assertEqual(r['p_exact_completion_range'],[0.125,0.25]);self.assertEqual(r['difference_b_minus_a_bounds'],[0.75,1])
 def test_p90_nearest_rank(self):self.assertEqual(report.percentile90(list(range(1,101))),90)
 def test_group_scores_keep_pending_denominator(self):
  rows=[{'group':'g','correct':True},{'group':'g','correct':False}]
  self.assertEqual(report.group_scores(rows,['q1','q2','q3'],['g'])['g'],{'correct':1,'incorrect':1,'pending':1,'accuracy_bounds':[1/3,2/3]})
if __name__=='__main__':unittest.main()
