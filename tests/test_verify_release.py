import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1]/'tools/verify_release.py'
spec = importlib.util.spec_from_file_location('verify_release_under_test', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, list):
        path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in value))
    else:
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))


class OriginalAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = root = Path(self.tmp.name)
        first, second = root/'results/2026-10-20', root/'results/2026-10-21-multilingual'
        write(first/'grading/mapping.json', {'a1': {'group': 'A', 'question_id': 'q1'}, 'a2': {'group': 'A', 'question_id': 'q2'}})
        # a1 is a 2:1 correct majority; a2 has no binary majority and stays pending.
        for name, verdicts in [('claude', ['correct', 'correct']), ('deepseek', ['correct', 'incorrect']), ('independent', ['incorrect', 'uncertain'])]:
            write(first/f'jsonl/grades/{name}.jsonl', [{'id': i, 'verdict': v} for i, v in zip(['a1', 'a2'], verdicts)])
        write(first/'grading/majority-resolved.jsonl', [{'id': 'a1', 'correct': True}])
        write(first/'grading/majority-needs-review.jsonl', [{'id': 'a2'}])
        write(second/'grading/mapping.json', {'b1': {'group': 'A', 'question_id': 'm1'}, 'b2': {'group': 'A', 'question_id': 'm2'}})
        write(second/'jsonl/grades/independent.jsonl', [{'id': 'b1', 'verdict': 'correct'}, {'id': 'b2', 'verdict': 'incorrect'}])
        write(root/'results/2026-10-20-supplement/summary.json', {'groups': {'A': {'name': 'Sonnet 不搜索', 'correct': 1, 'uncertain': 1, 'graded': 2}}})
        write(second/'analysis/summary.json', {'n_questions': 2, 'groups': {'A': {'correct': 1, 'pending': 0}}})
        write(root/'README.md', '| Sonnet 不搜索 | 50.00–100.00 | 50.00 |\n')
        self.runs = {('first', 'A', 'q1'): {}, ('first', 'A', 'q2'): {}, ('second', 'A', 'm1'): {}, ('second', 'A', 'm2'): {}}

    def test_recomputes_both_rounds_from_votes(self):
        counts = mod.original_accuracy(self.root, self.runs)
        self.assertEqual(counts['A']['first'], {'correct': 1, 'pending': 1})
        self.assertEqual(counts['A']['second'], {'correct': 1, 'incorrect': 1})

    def test_tampered_vote_or_homepage_is_rejected(self):
        write(self.root/'results/2026-10-21-multilingual/jsonl/grades/independent.jsonl',
              [{'id': 'b1', 'verdict': 'correct'}, {'id': 'b2', 'verdict': 'correct'}])
        with self.assertRaises(ValueError):
            mod.original_accuracy(self.root, self.runs)
        self.setUp()
        write(self.root/'README.md', '| Sonnet 不搜索 | 100.00 | 50.00 |\n')
        with self.assertRaises(ValueError):
            mod.original_accuracy(self.root, self.runs)

    def test_majority_record_must_match_votes(self):
        write(self.root/'results/2026-10-20/grading/majority-resolved.jsonl', [{'id': 'a1', 'correct': False}])
        with self.assertRaises(ValueError):
            mod.original_accuracy(self.root, self.runs)


if __name__ == '__main__':
    unittest.main()
