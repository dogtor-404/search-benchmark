import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name('prepare_public.py')
if not SCRIPT.exists():
    SCRIPT = Path(__file__).resolve().parents[1]/'tools/prepare_public.py'
spec = importlib.util.spec_from_file_location('prepare_public_under_test', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PublicCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root/'questions').mkdir()
        (root/'questions/questions.jsonl').write_text(json.dumps({'question': '私有原题', 'set': 'chinese_simpleqa'}, ensure_ascii=False)+'\n')
        self.clean = mod.Cleaner(root)

    def test_remove_private_events_but_keep_answers_and_measurements(self):
        values = [{'type': 'system', 'subtype': 'init', 'model': 'model-x', 'tools': ['WebSearch'], 'session_id': 'private-session', 'plugins': ['private-plugin']},
                  {'type': 'rate_limit_event', 'rate_limit_info': {'weekly': .93}},
                  {'type': 'system', 'subtype': 'thinking_tokens', 'estimated_tokens': 17},
                  {'type': 'result', 'result': 'answer', 'usage': {'output_tokens': 120, 'output_tokens_details': {'thinking_tokens': 60}}, 'session_id': 'private-session'}]
        result = self.clean.value(values)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {'type': 'system', 'subtype': 'init', 'model': 'model-x', 'tools': ['WebSearch']})
        self.assertEqual(result[1]['usage']['output_tokens_details']['thinking_tokens'], 60)
        self.assertEqual(result[1]['result'], 'answer')
        self.assertNotIn('private-session', json.dumps(result))

    def test_tool_returns_and_serialized_search_results_are_reduced(self):
        raw = {'results': [{'title': 'Title', 'url': 'https://example.org', 'summary': 'THIRD_PARTY_FULL_TEXT', 'snippet': 'EXCERPT'}]}
        event = {'type': 'tool_result', 'tool_use_id': 'call-1', 'content': [{'type': 'text', 'text': json.dumps(raw)}]}
        result = self.clean.value(event)
        ref = json.loads(result['content'][0]['text'])
        self.assertEqual(ref['references'], [{'title': 'Title', 'url': 'https://example.org'}])
        self.assertNotIn('THIRD_PARTY_FULL_TEXT', json.dumps(result))
        nested = self.clean.value({'response': json.dumps(raw)})
        self.assertNotIn('THIRD_PARTY_FULL_TEXT', nested['response'])

    def test_plain_native_preview_does_not_keep_prose(self):
        ref = self.clean.references('long copyright excerpt https://example.org/a\nother excerpt')
        self.assertEqual(ref['references'], [{'url': 'https://example.org/a'}])
        self.assertNotIn('long copyright excerpt', json.dumps(ref))

    def test_private_paths_and_question_are_removed_inside_json(self):
        user_path = '/'+'Users/person/project'
        result = self.clean.value({'text': user_path+' 私有原题', 'cwd': user_path})
        self.assertEqual(result, {'text': '~/project [CHINESE_SIMPLEQA_QUESTION_WITHHELD]'})

    def test_nonexistent_local_links_are_not_published(self):
        text = '[pilot](tmp/pilot/report.md) [report](report.md) [web](https://example.org)'
        output = mod.local_links(text, 'README.md', None, {'report.md'})
        self.assertNotIn('(tmp/', output)
        self.assertIn('[report](report.md)', output)

    def test_first_round_archive_links_are_relocated(self):
        output = mod.local_links('[original](tmp/archive/analysis/report.md)', 'README.md', None,
                                 {'results/2026-10-20/analysis/report.md'})
        self.assertEqual(output, '[original](results/2026-10-20/analysis/report.md)')

    def test_private_source_paths_are_hidden_in_thinking(self):
        path = '~/'+'dev/'+'video/project/docs/note.md'
        self.assertEqual(self.clean.text('见'+path+'。'), '见[PRIVATE_SOURCE_DIR]。')

    def test_new_result_ops_remain_executable_without_private_paths(self):
        p = Path(self.tmp.name)/'ops.py'
        p.write_text('from pathlib import Path\nROOT=Path('+repr(str(self.clean.root))+')\n')
        value = self.clean.file(p, 'results/new-result/ops/ops.py').decode()
        compile(value, '<public-ops>', 'exec')
        self.assertIn('parents[3]', value)
        self.assertNotIn(str(self.clean.root), value)

    def test_local_redactions_hide_private_names_and_internal_notes(self):
        root = Path(self.tmp.name)
        (root/'tmp').mkdir()
        (root/'tmp/public-redactions.json').write_text(json.dumps(
            {'terms': ['private-show', '私有目录'], 'replacements': [['，内部备注', '']]}, ensure_ascii=False))
        clean = mod.Cleaner(root)
        self.assertEqual(clean.text('不碰 `private-show/私有目录/`，内部备注。'), '不碰 `[PRIVATE_SOURCE_DIR]`。')
        self.assertEqual(clean.text('--exclude-dir=私有目录'), '--exclude-dir=[PRIVATE_SOURCE_DIR]')
        self.assertEqual(self.clean.private_terms, [])

    def test_codex_thread_ids_become_stable_labels(self):
        root = Path(self.tmp.name)
        first, second = '01a10000-0000-7000-8000-000000000002', '01a10000-0000-7000-8000-000000000001'
        (root/'results/usage').mkdir(parents=True)
        (root/'results/usage/summary.json').write_text(json.dumps({'per_session': [{'thread_id': first}, {'thread_id': second}]}))
        clean = mod.Cleaner(root)
        receipt = clean.value({'projections': {first: 'a', second: 'b'}, 'per_session': [{'thread_id': first, 'role': 'main'}]})
        self.assertEqual(receipt, {'projections': {'codex-session-02': 'a', 'codex-session-01': 'b'}, 'per_session': [{'role': 'main'}]})
        self.assertEqual(clean.text("ROOT_IDS={'"+first+"':'主'}"), "ROOT_IDS={'codex-session-02':'主'}")
        with self.assertRaises(ValueError):
            public = root/'public'
            public.mkdir()
            (public/'receipt.json').write_text(first)
            mod.inspect_public(public, (), list(clean.sessions))

    def test_runtime_heartbeat_is_not_exported(self):
        p = Path(self.tmp.name)/'tmp/archive/follow-up.json'
        p.parent.mkdir(parents=True)
        p.write_text('{}\n')
        self.assertFalse(mod.exportable(p))

    def test_runtime_counters_and_progress_are_excluded_but_audit_is_retained(self):
        root = Path(self.tmp.name)
        for name in ['mcp-count.txt', 'native-count.txt', 'progress.json', 'independent-progress.json']:
            path = root/name
            path.write_text('{}')
            self.assertFalse(mod.exportable(path), name)
        for name in ['search.jsonl', 'native-attempts.jsonl', 'dispatch.json', 'receipt.json']:
            path = root/name
            path.write_text('{}')
            self.assertTrue(mod.exportable(path), name)

    def test_required_search_template_is_included_without_exporting_arbitrary_html(self):
        for name, expected in [('search-efficiency-template.html', True), ('private-preview.html', False)]:
            path = Path(self.tmp.name)/name
            path.write_text('<html></html>')
            self.assertEqual(mod.exportable(path), expected)

    def test_no_whitelist_needed_for_new_result_data(self):
        p = Path(self.tmp.name)/'results/future/no-search-double-blind/votes/a.jsonl'
        p.parent.mkdir(parents=True)
        p.write_text('{}\n')
        self.assertTrue(mod.exportable(p))

    def test_preserve_config_group_order_and_json_shaped_answer(self):
        original = {'groups': {'B': {}, 'A': {}, 'B_prime': {}}}
        self.assertEqual(list(json.loads(mod.encode(original))['groups']), ['B', 'A', 'B_prime'])
        answer = '{ "answer" : "yes", "reason" : "because" }'
        self.assertEqual(self.clean.value({'answer': answer})['answer'], answer)

    def test_sanitizer_does_not_rewrite_its_own_regex_or_external_video(self):
        code = "re.sub(r'/Users/[A-Za-z0-9_.-]+', '~', text)"
        self.assertEqual(self.clean.text(code), code)
        third_party = 'https://www.bilibili.com/video/'+'BV1RW421F7KZ/'
        self.assertEqual(self.clean.text(third_party), third_party)
        self.clean.private_videos.add('BV0000000000')
        self.assertNotIn('BV0000000000', self.clean.text('https://www.bilibili.com/video/BV0000000000/'))
        self.assertEqual(self.clean.text(SCRIPT.read_text()), SCRIPT.read_text())


if __name__ == '__main__':
    unittest.main()
