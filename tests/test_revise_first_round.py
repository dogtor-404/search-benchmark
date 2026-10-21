import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import revise_first_round as revision
from common import BenchError


class RevisionTests(unittest.TestCase):
    def records(self):
        return [{'group':g,'question_id':q,'verdict':v} for g,values in [('a',['correct','incorrect','correct']),('b',['uncertain','correct','incorrect'])] for q,v in zip(['bad','q1','q2'],values)]

    def test_global_exclusion_removes_correct_and_uncertain_for_same_question(self):
        rows=self.records();before=copy.deepcopy(rows)
        kept,removed,ids=revision.select_records(rows,['a','b'],['bad','q1','q2'],{'bad'})
        self.assertEqual(ids,['q1','q2'])
        self.assertEqual(len(removed),2)
        self.assertEqual({r['verdict'] for r in removed},{'correct','uncertain'})
        self.assertEqual(rows,before)
        for g in ['a','b']:self.assertEqual({r['question_id'] for r in kept if r['group']==g},set(ids))

    def test_duplicate_or_missing_answer_stops_instead_of_changing_denominator(self):
        rows=self.records()
        for invalid in [rows[:-1],rows+[rows[0]]]:
            with self.assertRaises(BenchError):revision.select_records(invalid,['a','b'],['bad','q1','q2'],{'bad'})

    def test_unresolved_retained_answer_is_not_silently_dropped(self):
        rows=self.records();rows[-1]['verdict']='uncertain'
        with self.assertRaises(BenchError):revision.select_records(rows,['a','b'],['bad','q1','q2'],{'bad'})

    def test_nonexistent_exclusion_is_rejected(self):
        with self.assertRaises(BenchError):revision.select_records(self.records(),['a','b'],['bad','q1','q2'],{'absent'})


if __name__=='__main__':unittest.main()
