#!/usr/bin/env python3
"""只读原项目，生成独立脱敏预览及本地人工复核包；拒绝覆盖输出目录。"""
import argparse
import collections
import hashlib
import html
import json
import re
from pathlib import Path

DROP = object()
PRIVATE_KEYS = {'session_id', 'sessionId', 'uuid', 'cwd', 'original_cwd',
                'additional_directories', 'messaging_socket_path', 'plugins',
                'skills', 'agents', 'mcp_servers', 'slash_commands', 'capabilities',
                'account', 'organization', 'email', 'rate_limit_info',
                'thread_id', 'parent_thread_id', 'session_file'}
EXCERPT_KEYS = {'snippet', 'summary', 'excerpt', 'page_content', 'evidence',
                'source_excerpt', 'source_text', 'body_text'}
URL = re.compile(r'https?://[^\s<>"\]`]+')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
SESSION_KEYS = {'thread_id', 'parent_thread_id'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def jsonl(rows):
    return ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode()


class Cleaner:
    def __init__(self, root, redactions=None):
        self.root = root
        self.counts = collections.Counter()
        # Private names and internal notes live in an untracked local file, so this public script never lists them.
        path = Path(redactions) if redactions else root/'tmp/public-redactions.json'
        local = json.loads(path.read_text()) if path.exists() else {}
        self.private_terms = sorted(local.get('terms', []), key=len, reverse=True)
        self.text_edits = [tuple(e) for e in local.get('replacements', [])]
        # Codex thread IDs recorded by token accounting become stable public labels.
        ids = set()
        def collect(v):
            if isinstance(v, dict):
                for k, x in v.items():
                    if k in SESSION_KEYS and isinstance(x, str) and UUID.fullmatch(x): ids.add(x)
                    collect(x)
            elif isinstance(v, list):
                for x in v: collect(x)
        for p in (root/'results').rglob('*.json') if (root/'results').exists() else []:
            text = p.read_text()
            if '"thread_id"' in text: collect(json.loads(text))
        self.sessions = {s: f'codex-session-{i:02d}' for i, s in enumerate(sorted(ids), 1)}
        self.session_pattern = re.compile('|'.join(map(re.escape, self.sessions))) if self.sessions else None
        questions = read_rows(root/'questions/questions.jsonl')
        self.private_videos = set()
        for q in questions:
            if q.get('set') == 'custom':
                self.private_videos.update(re.findall(r'BV[A-Za-z0-9]{10}', q.get('provenance', {}).get('published_video', '')))
        self.private_questions = [q['question'] for q in questions
                                  if q['set'] == 'chinese_simpleqa']

    def text(self, text):
        # Replace complete home prefixes, including JSON-escaped strings after parsing.
        text = re.sub(r'/Users/[A-Za-z0-9_.-]+', '~', text)
        text = re.sub(r'~/(?:dev)/(?:video)(?:/[^\s`"\'<>，；。)]+)?', '[PRIVATE_SOURCE_DIR]', text)
        text = re.sub(r'~/(?:\.codex)/[^\s`"\'<>，；。)]+', '[PRIVATE_WORKSPACE_DIR]', text)
        text = re.sub(r'g-p-[a-f0-9]{20,}', 'PROJECT_ID_REMOVED', text)
        text = re.sub(r'(?:/private)?/tmp/cc-socks/[A-Za-z0-9_.-]+(?:\.sock)?', '[SOCKET_REMOVED]', text)
        for video in self.private_videos:
            text = re.sub(r'https?://(?:www\.)?bilibili\.com/video/'+re.escape(video)+r'[^\s"\'<>\\)]*', '[VIDEO_LINK_WITHHELD]', text)
            text = text.replace(video, '[VIDEO_ID_WITHHELD]')
        for q in self.private_questions:
            text = text.replace(q, '[CHINESE_SIMPLEQA_QUESTION_WITHHELD]')
        for old, new in self.text_edits:
            text = text.replace(old, new)
        for term in self.private_terms:
            text = text.replace(term, '[PRIVATE_SOURCE_DIR]')
        text = re.sub(r'\[PRIVATE_SOURCE_DIR\](?:/\[PRIVATE_SOURCE_DIR\])+/?', '[PRIVATE_SOURCE_DIR]', text)
        if self.session_pattern:
            text = self.session_pattern.sub(lambda m: self.sessions[m.group(0)], text)
        return text

    def references(self, content):
        """Structured search results retain only bibliographic fields; text uses URLs."""
        if isinstance(content, str):
            try:
                return self.references(json.loads(content))
            except (json.JSONDecodeError, TypeError):
                urls = list(dict.fromkeys(u.rstrip('.,;') for u in URL.findall(content)))
                return {'excerpt_removed': True, 'references': [{'url': self.text(u)} for u in urls]}
        if isinstance(content, list):
            refs = []
            for item in content:
                val = self.references(item)
                refs.extend(val.get('references', []))
            return {'excerpt_removed': True, 'references': refs}
        if isinstance(content, dict):
            if content.get('type') == 'text':
                return self.references(content.get('text', ''))
            if isinstance(content.get('results'), list):
                return self.references(content['results'])
            if isinstance(content.get('url'), str):
                return {'excerpt_removed': True, 'references': [
                    {k: self.text(content[k]) for k in ['title', 'url', 'date'] if isinstance(content.get(k), str)}]}
            refs = []
            for value in content.values():
                if isinstance(value, (dict, list, str)):
                    refs.extend(self.references(value).get('references', []))
            return {'excerpt_removed': True, 'references': refs}
        return {'excerpt_removed': True, 'references': []}

    def value(self, value):
        if isinstance(value, list):
            cleaned = [self.value(v) for v in value]
            return [v for v in cleaned if v is not DROP]
        if isinstance(value, dict):
            if value.get('type') == 'rate_limit_event' or (value.get('type') == 'system' and value.get('subtype') == 'thinking_tokens'):
                self.counts['removed_' + value.get('subtype', value['type'])] += 1
                return DROP
            if value.get('type') == 'system' and value.get('subtype') == 'init':
                self.counts['minimized_init'] += 1
                return {k: self.value(value[k]) for k in ['type', 'subtype', 'model', 'tools', 'claude_code_version'] if k in value}
            if value.get('type') == 'tool_result':
                self.counts['reduced_tool_result'] += 1
                # Error returns are also references-only: they can contain saved-file paths/previews.
                return {**{k: self.value(v) for k, v in value.items() if k not in PRIVATE_KEYS and k != 'content'},
                        'content': [{'type': 'text', 'text': json.dumps(self.references(value.get('content')), ensure_ascii=False)}]}
            output = {}
            for k, v in value.items():
                if k in PRIVATE_KEYS:
                    self.counts['removed_private_field'] += 1
                    continue
                if k in EXCERPT_KEYS and isinstance(v, str):
                    output[k] = '[WEB_EXCERPT_REMOVED]'
                    self.counts['removed_excerpt'] += 1
                    continue
                if k == 'returned_text':
                    output[k] = json.dumps(self.references(v), ensure_ascii=False)
                    self.counts['reduced_returned_text'] += 1
                    continue
                if k in {'published_video', 'publication_evidence', 'research_note'}:
                    output[k] = '[PRIVATE_PROVENANCE_WITHHELD]'
                    continue
                # Do not reserialize JSON-looking answers or alter their formatting.
                new = self.text(v) if isinstance(v, str) and k in {'answer', 'candidate_answer', 'reference_answer', 'result', 'question', 'reason'} else self.value(v)
                if new is not DROP:
                    output[self.text(k)] = new
            return output
        if isinstance(value, str):
            # Some API records contain an entire serialized JSON response in a text field.
            if value.lstrip().startswith(('{', '[')):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(parsed, (dict, list)):
                        result = self.value(parsed)
                        return '[EVENT_REMOVED]' if result is DROP else json.dumps(result, ensure_ascii=False)
            return self.text(value)
        return value

    def file(self, path, public_relative=None):
        if path.suffix == '.json':
            return encode(self.value(json.loads(path.read_text())))
        if path.suffix == '.jsonl':
            return jsonl(self.value(read_rows(path)))
        text = path.read_text()
        if path.suffix == '.py' and public_relative:
            # Executable historical scripts derive the project root from their public location.
            depth = len(Path(public_relative).parts)-1
            expr = 'str(Path(__file__).resolve().parents['+str(depth)+'])'
            text = text.replace(repr(str(self.root)), expr).replace('"'+str(self.root)+'"', expr)
            workspace = str(Path.home()/'.codex'/'.chatgpt-projects')
            text = re.sub(r"(['\"])"+re.escape(workspace)+r"/[^'\"]+\1",
                "__import__('os').environ.get('BENCH_WORKSPACE', "+expr+"+'/tmp/workspace')", text)
            sessions = str(Path.home()/'.codex'/'sessions'/'2026'/'10')
            text = text.replace(repr(sessions), "__import__('os').environ.get('BENCH_SESSION_DIR', "+expr+"+'/tmp/private-sessions')")
        if path.name == 'test_benchmark.py' and '需先运行 python3 tools/restore_first_round.py' not in text:
            hint = '需先运行 python3 tools/restore_first_round.py 重建第一轮题库'
            # Only these four tests depend on the withheld question file.
            for name in ['test_news_window_boundaries', 'test_same_pilot_all_groups',
                         'test_bad_questions_block_live', 'test_full_offline_pipeline']:
                text = text.replace(' def '+name+'(self):',
                    ' @unittest.skipUnless((ROOT/\'questions/questions.jsonl\').exists(), '+repr(hint)+')\n def '+name+'(self):')
        return self.text(text).encode()


def review_package(root, target):
    target.mkdir(parents=True)
    out = root/'tmp/archive'
    mapping = json.loads((out/'grading/mapping.json').read_text())
    questions = {q['id']: q for q in read_rows(root/'questions/questions.jsonl')}
    pending = {r['id']: r for r in read_rows(out/'grading/majority-needs-review.jsonl')}
    old = {r['id']: r for r in read_rows(out/'grading/needs-human.jsonl')}
    resolved = {r['id']: r for r in read_rows(out/'grading/majority-resolved.jsonl')}
    votes = {name: {r['id']: r for r in read_rows(out/f'jsonl/grades/{name}.jsonl')}
             for name in ['claude', 'deepseek', 'independent']}
    # Include the union even if a future majority-policy change introduces a new pending record.
    order = list(pending) + [oid for oid in old if oid not in pending]
    rows = []
    for i, oid in enumerate(order, 1):
        meta = mapping[oid]
        q = questions[meta['question_id']]
        run_path = out/'runs'/meta['group']/(meta['question_id']+'.json')
        run = json.loads(run_path.read_text())
        if digest(run_path.read_bytes()) != meta['run_sha256']:
            raise ValueError('复核材料 run hash 不一致: ' + oid)
        original = pending.get(oid, old.get(oid))
        if original['candidate_answer'] != run['answer']:
            raise ValueError('匿名回答与原始回答不一致: ' + oid)
        resolution = resolved.get(oid)
        rows.append({'review_number': i, 'blind_id': oid, **meta,
                     'question': q['question'], 'reference_answer': q['answer'],
                     'aliases': q['aliases'], 'source_urls': q['source_urls'],
                     'candidate_answer': run['answer'],
                     'judges': {n: {'verdict': rs[oid]['verdict'], 'reason': rs[oid]['reason']} for n, rs in votes.items()},
                     'still_pending': oid in pending, 'in_original_dual_review': oid in old,
                     'majority_verdict': None if resolution is None else ('correct' if resolution['correct'] else 'incorrect'),
                     'human_verdict': None, 'human_reason': '', 'reviewed_by_human': False})
    revision_policy = root/'results/2026-10-21-revised-92-95/policy.json'
    excluded_now = set(json.loads(revision_policy.read_text())['excluded_question_ids']['first']) if revision_policy.exists() else set()
    for row in rows:
        row['excluded_from_current_analysis'] = row['question_id'] in excluded_now
    (target/'review-records.jsonl').write_bytes(jsonl(rows))
    lines = ['# 第一轮人工复核清单', '',
             f'多数票后仍待核 {len(pending)} 份；旧双判待核 {len(old)} 份，其中 {sum(r["majority_verdict"] is not None for r in rows)} 份已有第三票多数裁决。下面共 {len(rows)} 份去重材料，不是 13 份。', '',
             '这是本地私人复核包，含 Chinese SimpleQA 原题；不随公开副本发布。尚未填写人工裁决，未改成绩。先看前 5 份；后三份可检查第三票已作出的裁决。', '',
             '| 编号 | 题号 | 组 | 参考答案 | 当前状态 |', '|---|---|---|---|---|']
    for r in rows:
        lines.append(f'| {r["review_number"]} | {r["question_id"]} | {r["group"]} | {str(r["reference_answer"]).replace(chr(10), " ")} | '+('仍待核' if r['still_pending'] else '第三票已判'+('对' if r['majority_verdict']=='correct' else '错'))+' |')
    prompts = {
        'frames-394': '请确认 launch mass 应按整箭还是飞船本体解释；是否保留题意有歧义。',
        'frames-598': '请确认 given first name 是否足以限定为出生名 Rolihlahla，还是 Nelson 也属于合理解读。同题有两份回答，建议用同一口径。',
        'simpleqa_verified-3137': '请确认给出正确猜测但明确撤回、不建议当答案，按现有评分规则算正确还是未作答。',
    }
    for r in rows:
        lines += ['', f'## {r["review_number"]} {r["question_id"]}', '',
                  f'组：{r["group"]}；匿名 ID：`{r["blind_id"]}`；'+('仍待核。' if r['still_pending'] else '第三票已裁决：'+r['majority_verdict']+'。'), '',
                  '题目：'+r['question'], '', '冻结参考答案：'+str(r['reference_answer']), '',
                  '完整模型回答：', '', r['candidate_answer'], '', '原有三位 AI 的意见：', '']
        for name, vote in r['judges'].items():
            lines.append(f'- **{name} / {vote["verdict"]}**：{vote["reason"]}')
        lines += ['', '题库附带来源（未在本次清理中重新作事实裁决）：', '']
        lines += [f'- {u}' for u in r['source_urls']]
        prompt = prompts.get(r['question_id'], '请核对撰成年、序文年代与出版年代是否混用。' if r['still_pending'] else '可选检查第三票的多数裁决是否符合原规则。')
        lines += ['', '需要判断：'+prompt, '', '你的裁决：□ 正确　□ 错误　□ 保留待核', '', '理由：', '']
    (target/'第一轮复核清单.md').write_text('\n'.join(lines)+'\n')
    if excluded_now:
        path = target/'第一轮复核清单.md'
        text = path.read_text().replace('# 第一轮人工复核清单', '# 第一轮原100题复核记录')
        text = text.replace('\n\n', '\n\n当前92题分析已按用户确认，在所有组统一排除8道争议题，剩余题待核为0。下列5份待核是原100题的历史状态，无需再为修订分析逐份裁决。\n\n', 1)
        path.write_text(text)
    sources = ['grading/majority-needs-review.jsonl', 'grading/needs-human.jsonl',
               'grading/majority-resolved.jsonl', 'grading/mapping.json']
    (target/'receipt.json').write_bytes(encode({'human': False, 'pending': len(pending), 'old_dual_pending': len(old),
        'unique_records': len(rows), 'source_sha256': {s: digest((out/s).read_bytes()) for s in sources},
        'question_sha256': digest((root/'questions/questions.jsonl').read_bytes()),
        'review_records_sha256': digest((target/'review-records.jsonl').read_bytes())}))
    return rows


METHODS = '''## 项目指令与搜索预览的影响

运行器使用 `--setting-sources project,local`。可见记录表明被测模型接收了项目 AGENTS.md 的指令，其中要求中文回复。这可能影响输出语言、作答方式和与其他评测的可比性。各组共享项目目录不等于各模型受到相同程度的影响，不能仅据此排除组间偏差。原冻结 manifest 没有记录 AGENTS.md 哈希；本次仅补存当前文件快照及哈希，不能据此证明它与运行时逐字相同。

第二轮 B 与 B′ 的 msqa-ES-53 存在搜索返回过长、被 CLI 保存为文件且上下文仅展示预览的情况。预算与工具限制下模型未继续读取完整文件，因此“只用搜索结果”并不意味着每次都看到了完整返回。

公开副本删除初始化的本机信息、会话标识、订阅额度事件及 thinking_tokens 进度事件；后者是进度通知，不是模型推理内容。保留的搜索返回只展示标题和网址，不等于模型当时看到的全文。答案、原始搜索次数、耗时和模型 token 用量保留；原文字符数与字节数统计仍描述未脱敏时的返回。公开哈希独立列出，旧 manifest 与 receipt 中的哈希只用于指向本地原件，不是脱敏文件的完整性证明。
'''


def local_links(text, source_rel, dest, available):
    def replace(m):
        label, url = m.group(1), m.group(2)
        if re.match(r'^[a-z]+:|^#', url):
            return m.group(0)
        # Reports are copied to the same relative location. Do not invent archive destinations.
        from posixpath import normpath, relpath
        actual = normpath(str(Path(source_rel).parent / url.split('#')[0]))
        if actual.startswith('tmp/archive/'):
            actual = 'results/2026-10-20/'+actual[len('tmp/archive/'):]
            if actual in available:
                fragment = '#'+url.split('#', 1)[1] if '#' in url else ''
                return '['+label+']('+relpath(actual, str(Path(source_rel).parent))+fragment+')'
        return m.group(0) if actual in available else label+'（材料保留于本地）'
    return re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', replace, text)


PUBLIC_TOOLS_README = '''# 运行与核查工具

工具使用Python 3.10+标准库；实际模型调用还需要Claude Code、订阅登录、网络及macOS钥匙串中的 `DEEPSEEK_API_KEY`。在项目根目录执行命令。模型版本、路由与价格是本次实验的冻结配置，复跑前需重新核实。

## 离线核查现有结果

```sh
python3 tools/verify_release.py
python3 tools/restore_first_round.py --cache /path/to/chinese_simpleqa.jsonl
python3 -m unittest discover -s tests -v
```

第一条校验公开文件哈希、2200份作答覆盖，从原评分票复算首页的原100/120题正确率，并重算当前1870份逐题计分及各组汇总，不读私人凭据或联网。第二条恢复本地题库；不指定缓存时从固定上游版本下载并核验SHA256。未恢复时4项依赖完整第一轮题库的测试会跳过。

现有第一轮公开归档在 `results/2026-10-20/`，第二轮在 `results/2026-10-21-multilingual/`。运行器的新输出写入 `tmp/`；历史manifest和receipt的哈希对应脱敏前原件，不能直接用于验证公开文件，也不能把公开归档冒充可原地续跑的原始目录。公开哈希以根目录 `PUBLIC-SHA256.json` 为准。

## 新实验入口

```sh
python3 tools/bench.py check
python3 tools/bench.py plan --phase pilot
python3 tools/bench.py preflight
python3 tools/multilingual.py plan
```

`plan` 只显示计划。新闻窗口、模型配置、版本与预算应按新实验条件检查；本次实验的历史授权不适用于其他人的账号。

第一轮试跑示例：

```sh
python3 tools/bench.py run --phase pilot --execute --quota-confirmed
python3 tools/grade.py prepare --phase pilot
python3 tools/grade.py run --phase pilot --judge claude --execute --quota-confirmed
python3 tools/grade.py run --phase pilot --judge deepseek --execute --quota-confirmed
python3 tools/grade.py resolve --phase pilot
python3 tools/analyze.py --phase pilot
```

`--execute` 启用真实调用；`--quota-confirmed` 表示执行者已确认预算；全量运行还要求 `--pilot-approved`。这些选项不会自动取得任何账号授权。不要把未决项、失败调用或缺失结果当作错题。有效记录续跑前校验冻结配置与原文哈希，失败原文需保留，禁止静默覆盖。

所有组每题最多五次实际搜索，DeepSeek参数固定为 `count=10, need_content=false`，不开放Fetch。预算拒绝与实际搜索分别计数。各被测进程清理模型路由、凭据和IDE上下文环境；密钥仅在调用时由钥匙串读入子进程，不写文件。

## 本次实验与历史工具

| 用途 | 入口或材料 | 口径 |
|---|---|---|
| 第一轮不搜索诊断、正式搜索 | `baseline.py`、`search_run.py`、`report.py` | 原100题，三票多数；诊断双判快照见根目录baseline.md |
| 第二轮作答 | `multilingual.py` | 原六语种120题 |
| 第二轮正式评分 | `multilingual_live_blind.py publish/merge`、`multilingual_single_report.py` | 一位独立AI单票；不是三票多数 |
| 早期第二轮评分方案 | `multilingual_pipeline.py`、`multilingual_grade_parallel.py`、`multilingual_independent_pipeline.py`、`multilingual_report.py` | 历史API/多票方案，未用于第二轮最终评分 |
| 历史搜索效率 | `first_round_supplement.py`、`multilingual_search_efficiency.py`、`revise_first_round.py` | 保留原100分制及额外搜索扣5分等历史行为，不代表当前得分 |
| 402份错答分类 | `results/2026-10-21-response-review/no-search-double-blind/` | 双盲分类与第三票裁决 |
| 最终提交状态与统一计分 | `results/2026-10-21-unified-score/` | 原2200份，正确+5、错误提交−3、弃答/撤回0，第二次起每次搜索−1 |
| 当前删题及分歧结案 | `results/2026-10-21-revised-92-95/` | 第一轮92题、第二轮95题，1870份；事后补充分析 |
| 累计token估算 | `results/2026-10-21-token-usage/` | 含私人会话汇总；会话源未公开，无法独立重算该部分 |

结果目录中的 `ops/` 保存生成当时材料的历史脚本；会重写报告或依赖未公开源文件，不要直接在归档上运行。核查现有公开结果使用 `verify_release.py`。`search-efficiency-template.html` 是历史搜索图表生成器的必需模板。

`prepare_public.py` 从本机完整项目生成独立脱敏副本，拒绝覆盖已有目录；本地私有词表位于 `tmp/public-redactions.json`。公开目录不包含该词表或完整私人输入，不能代替原项目重新导出。原始作答、评分票、失败重试、来源与修订凭据保留；运行计数文件、进度快照和私人日志不导出。
'''


def exportable(path):
    # Resume counters and progress snapshots are redundant with retained audit ledgers
    # and final receipts. Keep those ledgers, raw answers, votes and failed attempts.
    return (path.is_file() and '__pycache__' not in path.parts
            and 'pipeline' not in path.parts and path.name not in {
                'stderr.txt', 'follow-up.json', 'mcp-count.txt', 'native-count.txt',
                'progress.json', 'independent-progress.json'}
            and (path.suffix in {'.py', '.json', '.jsonl', '.md', '.txt', '.csv', '.tsv'}
                 or path.name == 'search-efficiency-template.html')
            and not path.name.endswith('.lock'))


def public_notice(text, results=False):
    text = text.replace('不得自行把原题上传公开网站，保留原作者署名及非商业、相同方式共享条件。',
        '本项目公开策略为隐藏Chinese SimpleQA题干，保留答案、别名、作答与裁决；这不是对上游许可证新增限制。原作者署名及非商业、相同方式共享条件保留。')
    text = text.replace('公开题保留原题和答案，只作固定抽样、排除/补抽、URL 清洗、补充等价别名和来源。',
        '本机题库保留原题和答案；公开副本隐藏Chinese SimpleQA题干，并提供固定上游版本与SHA256校验的本地恢复脚本。其他改动包括固定抽样、排除/补抽、URL清洗、补充等价别名和来源。')
    text = text.replace('每题保留研究笔记位置、BV 链接和发布证据，没有使用未发布选题。',
        '本机保留研究笔记位置、视频链接和发布证据；公开副本隐去这些来源字段，没有使用未发布选题。')
    text = text.replace('未来公开前须按项目 README 经用户确认；本 NOTICE 不是公开审批。', '')
    if results:
        for prefix in ['upstream/', 'multilingual.jsonl', 'multilingual-review.jsonl', 'review.jsonl', 'sources.json']:
            # Longer names first to avoid rewriting review.jsonl within multilingual-review.jsonl twice.
            if prefix == 'review.jsonl':
                text = re.sub(r'(?<![-/])review\.jsonl', '../questions/review.jsonl', text)
            elif prefix == 'sources.json':
                text = re.sub(r'(?<![-/])sources\.json', '../questions/sources.json', text)
            else:
                text = text.replace(prefix, '../questions/'+prefix)
    return text


def public_readme(root):
    first = json.loads((root/'results/2026-10-20-supplement/summary.json').read_text())
    second = json.loads((root/'results/2026-10-21-multilingual/analysis/summary.json').read_text())
    policy = json.loads((root/'results/2026-10-21-revised-92-95/policy.json').read_text())
    current = json.loads((root/'results/2026-10-21-revised-92-95/summary.json').read_text())
    n1, n2 = policy['new_primary_denominators']['first'], policy['new_primary_denominators']['second']
    def pct(correct, pending, n):
        lo, hi = 100*correct/n, 100*(correct+pending)/n
        return f'{lo:.2f}' if pending == 0 else f'{lo:.2f}–{hi:.2f}'
    lines = ['# 搜索工具对事实问答的影响', '',
        '比较相同模型在不搜索、Claude 原生搜索和 DeepSeek 搜索下的事实问答表现。原始题集为中英文100题、六语种120题，各十组，共2200份正式作答；两轮题目和评分方式不同，分别报告。', '',
        '## 原完整题集正确率', '',
        '先列出删题前100/120题的原正确率，便于核查。原判分仍有第一轮5份、第二轮18份待核，以下以“全部判错至全部判对”的范围表示，并非置信区间；没有因为后来移出分母而将原待核补判。第一轮采用三位AI多数票，第二轮采用独立AI单票。', '',
        '| 模型与工具 | 第一轮100题正确率% | 第二轮120题正确率% |', '|---|---:|---:|']
    order = ['0', 'A', 'B', 'D0', 'D2', '0_prime', 'A_prime', 'B_prime', 'D0_prime', 'D2_prime']
    for g in order:
        a, b = first['groups'][g], second['groups'][g]
        lines.append(f"| {a['name']} | {pct(a['correct'], a['uncertain'], a['graded'])} | {pct(b['correct'], b['pending'], second['n_questions'])} |")
    lines += ['', '原完整题集及历史口径见[第一轮100题报告](report-first-round-original-100.md)、[两轮原报告](report-original-100.md)、[第二轮120题原报告](results/2026-10-21-multilingual/analysis/report.md)。', '',
        '## 当前修订计分（事后补充分析）', '',
        f'此前经用户确认，第一轮移出{100-n1}/100题、第二轮移出{120-n2}/120题（{100*(120-n2)/120:.1f}%），同轮十组统一使用剩余{n1}/{n2}题。原答对、答错、弃答和待核一起移出，保留{current["retained_answers"]}份、移出{current["excluded_answers"]}份；当前分母内无待核。原2200份作答和所有评分票仍保留。', '',
        '**筛题与新计分均在看过结果后制定。** 同组同题不能消除筛题带来的难度、语言构成偏差；这不是事前验证，也没有开展新的确认性实验。', '',
        '当前计分：答对+5；错误且仍提交答案−3；不答或最终撤回0；第一次搜索不扣，从第二次起每多搜一次−1，对所有回答生效，不设0分下限。保留此前批准的规则和得分，不将旧“额外搜索扣5分”当作当前规则。', '',
        f'当前分数与逐题依据：[两轮修订报告](report.md)、[第一轮{n1}题](report-first-round.md)、[第二轮{n2}题](report-multilingual.md)、[删题清单](results/2026-10-21-revised-92-95/policy.json)、[已结案判决分歧](results/2026-10-21-revised-92-95/disagreements.md)。', '',
        '402份不搜索错答的四类双盲复核见[复核报告](results/2026-10-21-response-review/no-search-double-blind/report.md)；328份最终提交状态复核与2200份新计分见[统一计分](results/2026-10-21-unified-score/report.md)。历史版本保留原日期和原口径，勿将旧的72/112份弃答清单当作新四类计数的下界。', '',
        '## 复现与核查', '',
        '1. 使用Python 3，运行 `python3 tools/restore_first_round.py`，从固定上游版本下载并校验SHA256，在本地恢复第一轮题库。也可用 `--cache /path/to/chinese_simpleqa.jsonl` 指定已有缓存。恢复文件不提交。',
        '2. 运行 `python3 -m unittest discover -s tests -v`。未恢复时仅依赖完整第一轮题库的4项测试会跳过并提示恢复命令；其余测试照常执行。',
        '3. 运行配置与真实模型调用入口见[工具说明](tools/README.md)。实际调用需要账号、网络和订阅并产生用量；公开原始输出可用于逐份核查，不需要重跑模型。', '',
        '第一轮脱敏的原始输出、逐题作答、评分票与manifest位于[第一轮归档](results/2026-10-20/README.md)；它由本机tmp/archive导出，本机原件未移动。第二轮位于[第二轮归档](results/2026-10-21-multilingual/analysis/report.md)。网页返回仅保留标题/网址；[第一轮搜索记录](results/2026-10-20-supplement/search-efficiency.html)、[第二轮搜索记录](results/2026-10-21-multilingual/analysis/search-efficiency.html)。', '',
        '公开文件哈希见[PUBLIC-SHA256.json](PUBLIC-SHA256.json)，原件与脱敏件对应见[HASH-MAP.jsonl](HASH-MAP.jsonl)。旧manifest/receipt中的哈希属于本地原件，不能直接用于校验脱敏文件；JSON中的历史来源路径也可能仍指向本机归档结构。', '',
        '## 局限与公开范围', '',
        '被测模型接收了要求中文回复的项目指令；两份西班牙语作答只看到超长搜索返回的预览。各模型受指令影响的程度可能不同，不能仅凭共享目录排除组间偏差。[脱敏项目指令快照](context/AGENTS.public.md)与[变更说明](context/README.md)公开供核查；运行时未冻结它的哈希，现有快照不能证明与当时逐字一致。详见[METHODS.md](METHODS.md)。', '',
        'Chinese SimpleQA不公开题干，保留题号、参考答案/别名、模型作答、裁决理由和来源以供核查；这些材料可能透露答案、题意或部分措辞，不能声称题目不可推断。恢复脚本在使用者本地还原题库。频道链接、私人日志、会话身份、本机路径、额度事件和网页摘录已移除。', '',
        '## 相关工作', '',
        '设计前对已有搜索评测项目和相关研究的调研见[已有项目调研](已有项目调研.md)（2026-10-20），之后没有随结果更新。', '',
        '## 授权', '',
        '代码为[MIT](LICENSE)。题库与结果中本项目可授权部分分别见[题库许可](questions/LICENSE)、[题库署名](questions/NOTICE)、[结果许可](results/LICENSE)与[结果署名](results/NOTICE)。上游许可各自保留；模型商标与第三方网页不因此获得重新授权。', '']
    return '\n'.join(lines)


def make_public(root, target, cleaner, hash_map):
    public = target/'public-preview'
    public.mkdir()
    def put(relative, data, source=None, action='generated'):
        path = public/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hash_map[:] = [r for r in hash_map if r['public_path'] != relative]
        hash_map.append({'public_path': relative,
            'original_path': None if source is None else str(source.relative_to(root)),
            'original_sha256': None if source is None else digest(source.read_bytes()),
            'public_sha256': digest(data), 'original_bytes': None if source is None else source.stat().st_size,
            'public_bytes': len(data), 'action': action})
    candidates = {}
    for dirname in ['tools', 'tests', 'results']:
        for p in (root/dirname).rglob('*'):
            if exportable(p): candidates[str(p.relative_to(root))] = p
    # Licenses and NOTICE files have no suffix.
    for p in (root/'results').rglob('*'):
        if p.is_file() and p.name in {'LICENSE', 'NOTICE'}: candidates[str(p.relative_to(root))] = p
    for p in root.glob('report*.md'): candidates[p.name] = p
    for name in ['LICENSE', 'baseline.md', '已有项目调研.md']:
        candidates[name] = root/name
    for p in (root/'questions').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in {'questions.jsonl', '审核记录.md', 'README.md'}:
            candidates[str(p.relative_to(root))] = p
    # Full first-round raw answers and votes, derived independently of the local archive.
    for p in (root/'tmp/archive').rglob('*'):
        if exportable(p): candidates['results/2026-10-20/'+str(p.relative_to(root/'tmp/archive'))] = p
    generated = {'README.md', 'METHODS.md', 'questions/README.md', 'questions/first-round-template.jsonl',
        'context/AGENTS.public.md', 'context/README.md', 'results/2026-10-20/README.md',
        'tools/restore_first_round.py', 'PUBLIC-SHA256.json', 'HASH-MAP.jsonl'}
    displays = []
    for rel in candidates:
        if rel.endswith('search-efficiency-records.jsonl'):
            displays.append(rel[:-len('-records.jsonl')]+'.html')
    available = set(candidates) | generated | set(displays)
    for rel, source in sorted(candidates.items()):
        data = cleaner.file(source, rel)
        if source.suffix == '.md':
            text = data.decode()
            data = local_links(text, rel, public, available).encode()
        if rel == 'baseline.md':
            data = data.decode().replace('# 当前 baseline（2026-10-20）',
                '# 历史 baseline：正式搜索前的双判诊断（2026-10-20）\n\n本页冻结当时的双判诊断，不代表后来三票多数裁决或当前92/95题分析。当前入口见[首页](README.md)。').encode()
        put(rel, data, source, 'sanitized_copy')
    # Put the actually used version of the exporter into the public tools.
    put('tools/prepare_public.py', Path(__file__).read_bytes(), action='exporter_version')
    put('tools/README.md', PUBLIC_TOOLS_README.encode(), root/'tools/README.md', 'public_tool_guide')
    template = []
    for row in read_rows(root/'questions/questions.jsonl'):
        if row['set'] == 'chinese_simpleqa': row = {**row, 'question': None, 'answer': None, 'withheld': True}
        template.append(cleaner.value(row))
    put('questions/first-round-template.jsonl', jsonl(template), root/'questions/questions.jsonl', 'withheld_chinese_text')
    msqa_card = (root/'tmp/datasets/msqa/README.md').read_text().replace(
        '[`tools/build_dataset.py`](../tools/build_dataset.py)',
        '`tools/build_dataset.py` (upstream project path; not included here)')
    put('questions/upstream/msqa-README.md', msqa_card.encode(), root/'tmp/datasets/msqa/README.md', 'upstream_notice_link_localized')
    put('results/LICENSE', (root/'questions/LICENSE').read_bytes(), root/'questions/LICENSE', 'data_license')
    put('results/NOTICE', public_notice((root/'results/NOTICE').read_text(), results=True).encode(), root/'results/NOTICE', 'public_data_notice')
    put('questions/NOTICE', public_notice((root/'questions/NOTICE').read_text()).encode(), root/'questions/NOTICE', 'public_data_notice')
    put('questions/README.md', ('# 题库与本地恢复\n\n第一轮原100题库中25道Chinese SimpleQA题干不公开。先运行 `python3 tools/restore_first_round.py` 从固定revision下载并校验SHA256，再本地恢复questions.jsonl；可用 `--cache /path/to/chinese_simpleqa.jsonl` 离线恢复。该文件不提交。答案、别名、原始作答和复核理由仍可能透露答案或题意。\n\n原100题和120题题库不因后续筛题改变；当前92/95题由[固定排除清单](../results/2026-10-21-revised-92-95/policy.json)确定。许可及上游署名见[LICENSE](LICENSE)、[NOTICE](NOTICE)与[MSQA上游说明](upstream/msqa-README.md)。恢复不意味着重新纳入被排除题。\n').encode())
    put('tools/restore_first_round.py', RESTORE.encode())
    put('.gitignore', b'.DS_Store\n__pycache__/\n*.py[cod]\n.venv/\n.env\n.env.*\n!.env.example\n*.log\n*.lock\ntmp/\nquestions/questions.jsonl\n')
    put('README.md', public_readme(root).encode())
    put('METHODS.md', (METHODS + '\n## 版本与保留范围\n\n公开原100/120题正确率与当前92/95题事后补充计分，不更改原票或原始测量。第一轮原始记录以脱敏形式复制至results/2026-10-20，本机tmp/archive未移动。当前结果目录自动完整纳入，包括402份四类复核、328份提交状态复核、92/95题计分和token估算。\n\n历史ops脚本中的项目根改为相对公开目录推导；评分工作目录改用BENCH_WORKSPACE或本地tmp/workspace，用量统计会话源改用BENCH_SESSION_DIR或tmp/private-sessions。公开包不包含会话源，无法用公开材料独立重算Codex私人会话token估算。\n\n完整Chinese SimpleQA题干隐藏；答案、别名、裁决与模型输出保留，可能推断题意。思考中偶然复制的网页内容或题目片段无法仅通过结构化脱敏完全识别。第三方搜索返回字段及工具返回只保留标题/URL/日期。原文返回量统计描述脱敏前数据。\n').encode())
    agent_source = root/'AGENTS.md'
    agent_text = cleaner.text(agent_source.read_text())
    # Only relocate links; the snapshot text should stay as close as possible to what the tested models saw.
    agent_text = agent_text.replace('](README.md)', '](../README.md)').replace('](已有项目调研.md)', '](../已有项目调研.md)')
    put('context/AGENTS.public.md', agent_text.encode(), agent_source, 'sanitized_current_context_snapshot')
    put('context/README.md', ('# 项目指令快照\n\nAGENTS.public.md来自本次导出时的AGENTS.md，保留操作和中文回复等指令，私人视频项目及其子目录替换为[PRIVATE_SOURCE_DIR]，本机用户路径与项目标识按通用规则隐藏。运行时manifest没有冻结该文件的哈希，不能证明当前文件与被测时逐字相同；HASH-MAP记录当前原件及公开件哈希。\n\n该文件作为复现资料存于context，未自动作为新评测的顶层agent指令。复现当时上下文需显式检查并采用此快照，同时记录新运行的实际哈希。\n').encode())
    put('results/2026-10-20/README.md', ('# 第一轮脱敏归档\n\n由原tmp/archive只读复制而来，包含1000份正式作答、原始输出、三位判分票、原100题5份历史待核及失败重试。当前92题分析已统一移出争议题，不等于原100题待核获得了新裁决。\n\n网页返回已缩减为标题/URL，题干、私人信息和进度事件已清理。原manifest与receipt的SHA256仍指向本地原件；请用根目录[公开哈希](../../PUBLIC-SHA256.json)校验本包。原JSON来源路径保持历史含义，tmp/archive对应本目录，未替换原历史哈希。\n').encode())
    for rel in displays:
        records = read_rows(public/(rel[:-len('.html')]+'-records.jsonl'))
        parts = ['<!doctype html><meta charset="utf-8"><title>逐次搜索标题与网址</title>',
            '<style>body{max-width:1000px;margin:2em auto;padding:0 1em;font-family:system-ui;overflow-wrap:anywhere}details{margin:1em 0}pre{white-space:pre-wrap}</style>',
            '<h1>逐次搜索标题与网址</h1><p>网页摘录已移除；返回量统计为脱敏前数值。</p>']
        for r in records:
            parts.append('<details><summary>'+html.escape(f'{r["group"]} / {r["question_id"]} / {r["search_calls"]} 次搜索')+'</summary>')
            for search in r['searches']:
                parts.append('<h3>'+html.escape(str(search.get('query', '')))+'</h3>')
                value = json.loads(search['returned_text'])
                for ref in value.get('references', []):
                    url = ref.get('url', '')
                    if url.startswith(('http://', 'https://')):
                        parts.append('<p><a rel="noreferrer" href="'+html.escape(url, quote=True)+'">'+html.escape(ref.get('title', url))+'</a></p>')
            parts.append('</details>')
        put(rel, '\n'.join(parts).encode(), action='regenerated_without_excerpts')
    put('HASH-MAP.jsonl', jsonl(hash_map.copy()))
    hashes = {str(p.relative_to(public)): digest(p.read_bytes()) for p in sorted(public.rglob('*')) if p.is_file()}
    (public/'PUBLIC-SHA256.json').write_bytes(encode(hashes))
    return public


RESTORE = '''#!/usr/bin/env python3
"""从固定上游版本在本地重建第一轮题库，不调用被测模型。"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def restore(cache=None):
    sources=json.loads((ROOT/'questions/sources.json').read_text())['datasets']
    source=next(s for s in sources if s['set']=='chinese_simpleqa')
    cache=Path(cache) if cache else ROOT/'tmp/datasets/chinese_simpleqa.jsonl'
    if not cache.exists():
        data=urllib.request.urlopen(source['url'],timeout=60).read()
        if hashlib.sha256(data).hexdigest()!=source['sha256']: raise ValueError('上游文件 SHA256 不符')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
    data=cache.read_bytes()
    if hashlib.sha256(data).hexdigest()!=source['sha256']: raise ValueError('上游文件 SHA256 不符')
    upstream={str(r['id']):r for r in map(json.loads,data.decode().splitlines()) if r}
    rows=[json.loads(l) for l in (ROOT/'questions/first-round-template.jsonl').read_text().splitlines() if l.strip()]
    for row in rows:
        if row.pop('withheld',False):
            item=upstream[str(row['provenance']['source_id'])]
            row['question']=item['question'];row['answer']=item['answer']
    target=ROOT/'questions/questions.jsonl'
    content=''.join(json.dumps(r,ensure_ascii=False)+'\\n' for r in rows)
    if target.exists() and target.read_text()!=content: raise ValueError('已有题库不同，拒绝覆盖')
    target.write_text(content)
    print(json.dumps({'questions':len(rows),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'local_only':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache');a=p.parse_args();restore(a.cache)
'''


def inspect_public(public, private_videos=(), private_literals=()):
    findings = []
    for path in public.rglob('*'):
        if not path.is_file():
            continue
        text = path.read_text()
        if path.relative_to(public).as_posix() == 'tests/test_budget_regression.py':
            # Exact, visibly synthetic fixtures; no other files or credentials are exempted.
            text = text.replace('sk-'+'abcdefghijkl1234567890', '[KNOWN_FAKE_KEY]')
            text = text.replace('Bearer '+'abcdefghijkl1234567890', '[KNOWN_FAKE_BEARER]')
        patterns = [re.escape(str(Path.home()))+r'(?:/|\b)', r'g-p-[a-f0-9]{20,}', r'/tmp/cc-socks/[A-Za-z0-9_.-]+',
                    r'(?<![A-Za-z0-9])sk-[A-Za-z0-9]{16,}',
                    r'Bearer\s+[A-Za-z0-9_.-]{20,}']
        for pattern in patterns + [re.escape(v) for v in private_videos]:
            if re.search(pattern, text):
                findings.append({'path': str(path.relative_to(public)), 'pattern': pattern})
        # Report only the index so a failure message does not repeat a private name.
        for i, literal in enumerate(private_literals):
            if literal in text:
                findings.append({'path': str(path.relative_to(public)), 'private_literal': i})
    if findings:
        raise ValueError('公开副本仍有待清理命中: '+json.dumps(findings[:20]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--redactions', type=Path, help='本地私有词表，默认 <source>/tmp/public-redactions.json')
    args = parser.parse_args()
    root = args.source.resolve()
    target = args.output.resolve()
    if target.exists():
        raise ValueError('拒绝覆盖已有输出目录')
    if root == target or root in target.parents:
        raise ValueError('输出必须位于项目原件之外')
    # Hash all source files except volatile bytecode before and after export.
    original_files = [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts]
    before = {str(p.relative_to(root)): digest(p.read_bytes()) for p in original_files}
    target.mkdir(parents=True)
    cleaner = Cleaner(root, args.redactions)
    reviews = review_package(root, target/'private-review')
    context = target/'private-context'
    context.mkdir()
    context.joinpath('AGENTS.current-snapshot.md').write_bytes((root/'AGENTS.md').read_bytes())
    context.joinpath('receipt.json').write_bytes(encode({'captured_at': '2026-10-21',
        'sha256': digest((root/'AGENTS.md').read_bytes()), 'historical_identity_verified': False,
        'note': '本次清理时的快照；原始manifest没有冻结运行时AGENTS哈希，不能补称为运行时原件。'}))
    hashes = []
    public = make_public(root, target, cleaner, hashes)
    inspect_public(public, cleaner.private_videos,
                   cleaner.private_terms + [old for old, _ in cleaner.text_edits if old] + list(cleaner.sessions))
    changed = [name for name, old in before.items() if not (root/name).is_file() or digest((root/name).read_bytes()) != old]
    after_names = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts}
    if changed or after_names != set(before):
        raise ValueError('原目录在导出期间变化: '+str(changed[:10]))
    receipt = {'source_files_verified_unchanged': len(before), 'source_unchanged': True,
               'source_snapshot_sha256': digest(encode(before)),
               'public_files': sum(p.is_file() for p in public.rglob('*')),
               'public_bytes': sum(p.stat().st_size for p in public.rglob('*') if p.is_file()),
               'transformations': dict(cleaner.counts),
               'first_round_original_pending': sum(r['still_pending'] for r in reviews),
               'first_round_pending': sum(r['still_pending'] and not r['excluded_from_current_analysis'] for r in reviews),
               'review_records': len(reviews), 'published': False,
               'excluded': ['unsanitized project AGENTS.md', 'private work log', 'video channel links',
                            'Chinese SimpleQA question text',
                            'pilot records', 'pipeline machinery', 'stderr'],
               'hash_note': 'HASH-MAP maps original to derived copies; old manifests keep historical source hashes.'}
    (target/'cleanup-receipt.json').write_bytes(encode(receipt))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
