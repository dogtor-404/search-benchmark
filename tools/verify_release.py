#!/usr/bin/env python3
"""离线核查公开文件与两轮既有计分；不调用模型、不读取私人会话。"""
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {'0', 'A', 'B', 'D0', 'D2', '0_prime', 'A_prime', 'B_prime', 'D0_prime', 'D2_prime'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def identity(row):
    return row['round'], row['group'], row['question_id']


def pct(correct, pending, n):
    lo, hi = 100*correct/n, 100*(correct+pending)/n
    return f'{lo:.2f}' if pending == 0 else f'{lo:.2f}–{hi:.2f}'


def original_accuracy(root, runs):
    """从原评分票复算首页最先展示的原100/120题正确率，并与汇总文件和首页表格对照。"""
    counts = {}
    # 第一轮：三位评分员中至少两张相同的对/错票才裁决，否则待核。
    grading = root/'results/2026-10-20/grading'
    mapping = read(grading/'mapping.json')
    require({('first', m['group'], m['question_id']) for m in mapping.values()} == {k for k in runs if k[0] == 'first'}
            and len(mapping) == sum(k[0] == 'first' for k in runs), '第一轮评分映射与作答不符')
    votes = [{r['id']: r['verdict'] for r in rows(root/f'results/2026-10-20/jsonl/grades/{name}.jsonl')}
             for name in ['claude', 'deepseek', 'independent']]
    require(all(set(v) == set(mapping) for v in votes), '第一轮评分票不全')
    resolved = {r['id']: r['correct'] for r in rows(grading/'majority-resolved.jsonl')}
    pending = {r['id'] for r in rows(grading/'majority-needs-review.jsonl')}
    require(not set(resolved) & pending and set(resolved) | pending == set(mapping), '第一轮裁决记录不全')
    first = collections.defaultdict(collections.Counter)
    for oid, meta in mapping.items():
        binary = collections.Counter(v[oid] for v in votes if v[oid] in ('correct', 'incorrect'))
        top = [verdict for verdict, n in binary.items() if n >= 2]
        outcome = top[0] if top else 'pending'
        recorded = 'pending' if oid in pending else ('correct' if resolved[oid] else 'incorrect')
        require(outcome == recorded, '第一轮多数票与裁决记录不符')
        first[meta['group']][outcome] += 1
    # 第二轮：每份作答一张独立AI票，不确定即待核。
    mapping2 = read(root/'results/2026-10-21-multilingual/grading/mapping.json')
    require({('second', m['group'], m['question_id']) for m in mapping2.values()} == {k for k in runs if k[0] == 'second'}
            and len(mapping2) == sum(k[0] == 'second' for k in runs), '第二轮评分映射与作答不符')
    votes2 = rows(root/'results/2026-10-21-multilingual/jsonl/grades/independent.jsonl')
    require(len(votes2) == len({r['id'] for r in votes2}) and {r['id'] for r in votes2} == set(mapping2), '第二轮评分票不全')
    second = collections.defaultdict(collections.Counter)
    for r in votes2:
        second[mapping2[r['id']]['group']][r['verdict'] if r['verdict'] in ('correct', 'incorrect') else 'pending'] += 1
    s1 = read(root/'results/2026-10-20-supplement/summary.json')['groups']
    s2 = read(root/'results/2026-10-21-multilingual/analysis/summary.json')
    readme = (root/'README.md').read_text()
    require(set(s1) == set(s2['groups']) == set(first) == set(second), '原正确率分组不符')
    for group, stats in s1.items():
        a, b, n2 = first[group], second[group], s2['n_questions']
        require((a['correct'], a['pending'], sum(a.values())) == (stats['correct'], stats['uncertain'], stats['graded']),
                '第一轮原正确数与汇总不符：'+group)
        require((b['correct'], b['pending'], sum(b.values())) == (s2['groups'][group]['correct'], s2['groups'][group]['pending'], n2),
                '第二轮原正确数与汇总不符：'+group)
        row = f"| {stats['name']} | {pct(a['correct'], a['pending'], sum(a.values()))} | {pct(b['correct'], b['pending'], n2)} |"
        require(row in readme, '首页原正确率表与评分票不符：'+group)
        counts[group] = {'first': dict(a), 'second': dict(b)}
    return counts


def verify(root=ROOT):
    hashes = read(root/'PUBLIC-SHA256.json')
    for name, digest in hashes.items():
        path = root/name
        require(path.resolve().is_relative_to(root.resolve()), '校验路径越界')
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                '公开文件校验失败：'+name)
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()
              and not any(x in p.relative_to(root).parts for x in ['.git', '__pycache__', '.venv', 'tmp'])
              and str(p.relative_to(root)) not in ['PUBLIC-SHA256.json', 'questions/questions.jsonl']}
    require(actual == set(hashes), '公开目录有未登记或缺失文件')
    for entry in rows(root/'HASH-MAP.jsonl'):
        require(hashes.get(entry['public_path']) == entry['public_sha256'], '脱敏映射不符')

    runs = {}
    for round_name, folder, n in [('first', '2026-10-20', 100), ('second', '2026-10-21-multilingual', 120)]:
        counts = collections.Counter()
        question_sets = collections.defaultdict(set)
        for path in (root/'results'/folder/'runs').glob('*/*.json'):
            record = read(path)
            key = (round_name, record['group'], record['question_id'])
            require(key not in runs and record['status'] == 'ok', '重复或无效作答')
            runs[key] = record
            counts[record['group']] += 1
            question_sets[record['group']].add(record['question_id'])
        require(set(counts) == GROUPS and all(v == n for v in counts.values()), '原题集覆盖不完整')
        require(all(ids == question_sets['0'] for ids in question_sets.values()), '各组原题号不一致')
    original_accuracy(root, runs)

    all_scores = rows(root/'results/2026-10-21-unified-score/score-records.jsonl')
    lookup = {identity(r): r for r in all_scores}
    require(len(all_scores) == len(lookup) == 2200 and set(lookup) == set(runs), '统一计分覆盖不完整')
    bases = {'correct': (5, 5), 'incorrect_submitted': (-3, -3),
             'no_answer': (0, 0), 'withdrawn_answer': (0, 0), 'pending_submitted': (-3, 5)}
    for key, score in lookup.items():
        run = runs[key]
        require(score['candidate_answer'] == run['answer'], '计分作答与原始记录不同')
        require(score['search_calls'] == run['search_calls'], '搜索次数与原始记录不同')
        low, high = bases[score['scoring_outcome']]
        penalty = max(score['search_calls']-1, 0)
        require((score['base_lower'], score['base_upper'], score['search_penalty'],
                 score['score_lower'], score['score_upper']) == (low, high, penalty, low-penalty, high-penalty),
                '逐题计分不符')

    current = root/'results/2026-10-21-revised-92-95'
    kept, removed = rows(current/'score-records.jsonl'), rows(current/'excluded-records.jsonl')
    require(len(kept) == 1870 and len(removed) == 330, '修订记录数不符')
    partition = {identity(r): r for r in kept+removed}
    require(len(kept+removed) == len(partition) and partition == lookup, '保留/移出未完整划分原始记录')
    policy, summary = read(current/'policy.json'), read(current/'summary.json')
    for r in kept:
        require(r['question_id'] not in policy['excluded_question_ids'][r['round']], '保留了排除题')
    for r in removed:
        require(r['question_id'] in policy['excluded_question_ids'][r['round']], '移出了规则外题目')
    for round_name, n in [('first', 92), ('second', 95)]:
        cohort = summary['cohorts'][round_name]
        require(set(cohort['groups']) == GROUPS, '修订分组不完整')
        for group, stats in cohort['groups'].items():
            selected = [r for r in kept if r['round'] == round_name and r['group'] == group]
            require(len(selected) == n and {r['question_id'] for r in selected} == set(cohort['question_ids']),
                    '修订题号集合不同')
            require(all(r['original_correct'] is not None and r['score_lower'] == r['score_upper'] for r in selected),
                    '修订题集中仍有待核')
            total = sum(r['score_lower'] for r in selected)
            require(stats['n'] == n and stats['total_lower'] == stats['total_upper'] == total
                    and abs(stats['mean_lower']-total/n) < 1e-10, '修订汇总分不符')
            require(stats['original_correct'] == sum(r['original_correct'] is True for r in selected), '正确数不符')
    return {'passed': True, 'public_hashes': len(hashes), 'original_answers': len(runs),
            'original_accuracy_recalculated_from_votes': len(runs),
            'scores_recalculated': len(all_scores), 'retained': len(kept), 'excluded': len(removed),
            'denominators': [92, 95], 'network_calls': 0}


if __name__ == '__main__':
    try:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('公开结果核查失败：'+str(error), file=sys.stderr)
        sys.exit(1)
