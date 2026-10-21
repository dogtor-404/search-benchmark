#!/usr/bin/env python3
"""按用户确认统一排除四道争议题，另存96题分析，不修改100题原件。"""
import collections
import copy
import datetime
import json
import re
import statistics
from pathlib import Path
from common import ROOT, BenchError, load_jsonl, sha256, write_json, write_text, dumps
import analyze
import multilingual_search_efficiency as efficiency

EXCLUDED = {
    'frames-394': 'launch mass未限定整箭或飞船本体',
    'frames-598': 'given first name未限定常用名或出生名',
    'chinese_simpleqa-4bbc0cb7b62340869edc384db4813a9e': '同名教区缺少地点限定',
    'chinese_simpleqa-59547154e0b64dcca92a2da105631ccb': '撰成与序文年代及来源年份有争议',
}
SOURCE = ROOT/'tmp/archive'
SUPPLEMENT = ROOT/'results/2026-10-20-supplement'
OUT = ROOT/'results/2026-10-20-revised-96'


def read(path):
    return json.loads(path.read_text())


def select_records(records, groups, question_ids, excluded):
    if not excluded or not set(excluded) <= set(question_ids):
        raise BenchError('排除题号必须存在于冻结题库')
    expected = {(g, q) for g in groups for q in question_ids}
    keys = [(r['group'], r['question_id']) for r in records]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise BenchError('原始作答覆盖缺失或重复')
    retained = [copy.deepcopy(r) for r in records if r['question_id'] not in excluded]
    removed = [copy.deepcopy(r) for r in records if r['question_id'] in excluded]
    if any(r['verdict'] not in {'correct', 'incorrect'} for r in retained):
        raise BenchError('剩余题仍有待核，不能静默缩小某组分母')
    ids = [q for q in question_ids if q not in excluded]
    for g in groups:
        if {r['question_id'] for r in retained if r['group'] == g} != set(ids):
            raise BenchError('各组未使用相同题目')
    return retained, removed, ids


def aggregate(records, groups, ids, resources, confirmed):
    result = efficiency.summarize(records, groups)
    by_resource = {(r['group'], r['question_id']): r for r in resources}
    for g, row in result.items():
        rr = [r for r in records if r['group'] == g]
        usage = [by_resource[g, q] for q in ids]
        if len(rr) != len(ids) or row['uncertain'] or row['ungraded']:
            raise BenchError('96题统计覆盖不完整')
        times = [r['elapsed_seconds'] for r in usage]
        token = [r['main_model_usage'] for r in usage]
        row.update(n=len(ids), accuracy=row['correct']/len(ids),
                   accuracy_percent=100*row['correct']/len(ids),
                   adjusted_score_mean=statistics.mean(r['adjusted_score'] for r in rr),
                   mean_seconds=statistics.mean(times), median_seconds=statistics.median(times),
                   p90_seconds=sorted(times)[__import__('math').ceil(len(times)*.9)-1],
                   mean_returned_utf8_bytes=statistics.mean(r['returned_utf8_bytes'] for r in usage),
                   mean_returned_characters=statistics.mean(r['returned_characters'] for r in usage),
                   mean_reported_input_tokens=statistics.mean(t['inputTokens'] for t in token),
                   mean_cache_read_tokens=statistics.mean(t['cacheReadInputTokens'] for t in token),
                   mean_cache_write_tokens=statistics.mean(t['cacheCreationInputTokens'] for t in token),
                   mean_output_tokens=statistics.mean(t['outputTokens'] for t in token),
                   confirmed_abstentions_lower_bound=sum(r['group'] == g for r in confirmed))
        total = [t['total_input_tokens'] for t in token]
        row['mean_total_input_tokens'] = statistics.mean(total) if all(t is not None for t in total) else None
    return result


def compare(records, groups, ids):
    table = {(r['group'], r['question_id']): r for r in records}
    pairs = [('A', 'B'), ('A_prime', 'B_prime')]
    baselines = {'A':'0','B':'0','D2':'D0','A_prime':'0_prime','B_prime':'0_prime','D2_prime':'D0_prime'}
    result = {}
    for a, b in pairs + [(v, k) for k, v in baselines.items()]:
        av = [table[a, q]['verdict'] == 'correct' for q in ids]
        bv = [table[b, q]['verdict'] == 'correct' for q in ids]
        delta = [int(v)-int(u) for u, v in zip(av, bv)]
        adjusted = [table[b, q]['adjusted_score']-table[a, q]['adjusted_score'] for q in ids]
        result[a+'__'+b] = {'a':a, 'b':b, 'n':len(ids), 'difference_b_minus_a_pp':100*statistics.mean(delta),
                            'mcnemar':analyze.mcnemar(av,bv),
                            'accuracy_bootstrap':analyze.bootstrap(delta,seed=20261021),
                            'adjusted_score_difference':statistics.mean(adjusted),
                            'adjusted_score_bootstrap':analyze.bootstrap(adjusted,seed=20261021)}
    return result


def markdown(summary):
    lines = ['# 第一轮统一剔除争议题后的96题报告', '',
             '原第一轮实际完成100题×10组，共1000份作答。用户在查看争议后，于2026年10月21日确认统一剔除4道题；所有组均按相同96题、960份作答重新统计。原题库、原始输出、三张判分票与原100题报告保留。', '',
             '这是事后调整的分析口径，不能写成运行前已确定的筛题规则。排除按题号统一执行，答对、答错与待核均排除；没有只缩小某个组的分母。原5份待核都落在排除题中，剩余96题每组均有二元多数裁决。第二轮120题及18份待核维持原状。', '',
             '## 排除范围', '', '| 题号 | 原争议 | 所有组处理 |', '|---|---|---|']
    for q, reason in EXCLUDED.items():
        lines.append(f'| {q} | {reason} | 全部排除 |')
    removed = summary['removed_outcomes']
    lines += ['', f'共移出40份作答：原判对{removed.get("correct",0)}份、原判错{removed.get("incorrect",0)}份、原待核{removed.get("uncertain",0)}份。这些裁决没有改写，只是移出本次分析。原报告另有2道题意质量标记，本次没有扩大排除范围。', '',
              '## 各组成绩', '',
              '正确率=保留题的正确数÷96；搜索扣分均分也以96为分母。答对100分，首次搜索不扣，第二至五次每次扣5分；答错0分。该扣分指标与本次删题均是事后分析。', '',
              '| 模型与工具 | 正确/96 | 错误 | 正确率% | 扣分均分 | 平均搜索次数 | 明确弃答至少 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['groups'].values():
        lines.append(f'| {row["name"]} | {row["correct"]}/96 | {row["incorrect"]} | {efficiency.fmt(row["accuracy_percent"])} | {efficiency.fmt(row["adjusted_score_mean"])} | {efficiency.fmt(row["mean_search_calls"])} | {row["confirmed_abstentions_lower_bound"]} |')
    lines += ['', '## 同模型两种搜索的比较', '',
              '以下全部使用同一96题，差值为DeepSeek搜索减原生搜索。McNemar仅用于对错，扣分均分另用按题配对bootstrap，10000次、固定种子20261021；未做多重比较校正。', '',
              '| 模型 | 正确率差pp | 原生独对/DeepSeek独对 | McNemar p | 扣分均分差 | 扣分差95% bootstrap区间 |', '|---|---:|---:|---:|---:|---|']
    for key, label in [('A__B','Sonnet'),('A_prime__B_prime','Opus')]:
        v=summary['comparisons'][key];p=v['mcnemar'];ci=v['adjusted_score_bootstrap']['ci95']
        lines.append(f'| {label} | {efficiency.fmt(v["difference_b_minus_a_pp"])} | {p["a_only"]}/{p["b_only"]} | {p["p_exact"]:.5f} | {efficiency.fmt(v["adjusted_score_difference"])} | [{efficiency.fmt(ci[0])}, {efficiency.fmt(ci[1])}] |')
    lines += ['', '删题依据已经观察到的题目争议，显著性检验只描述本次修订样本，不能包装成一次新的事前验证。', '',
              '## 搜索相对同模型不搜索的提升', '', '| 搜索组 | 对照 | 同题数 | 正确率差pp | 正确率差95% bootstrap区间pp |', '|---|---|---:|---:|---|']
    for key,v in summary['comparisons'].items():
        if key in {'A__B','A_prime__B_prime'}:continue
        ci=v['accuracy_bootstrap']['ci95']
        lines.append(f'| {v["b"]} | {v["a"]} | {v["n"]} | {efficiency.fmt(v["difference_b_minus_a_pp"])} | [{efficiency.fmt(100*ci[0])}, {efficiency.fmt(100*ci[1])}] |')
    lines += ['', '## 耗时与搜索返回量', '', '下表均按保留的96题重算。返回量为本地原始成功工具返回的文本，不是脱敏副本中缩减后的长度。模型用量明细保留于summary.json及resource-runs.jsonl；不同模型tokenizer及兼容接口缓存口径不直接等量比较。', '',
              '| 模型与工具 | 平均秒数 | 中位秒数 | P90秒数 | 每题返回KB | 报告输入token/题 | 报告输出token/题 |', '|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['groups'].values():
        lines.append(f'| {row["name"]} | {efficiency.fmt(row["mean_seconds"])} | {efficiency.fmt(row["median_seconds"])} | {efficiency.fmt(row["p90_seconds"])} | {efficiency.fmt(row["mean_returned_utf8_bytes"]/1000)} | {row["mean_reported_input_tokens"]:.0f} | {row["mean_output_tokens"]:.0f} |')
    lines += ['', '## 明确弃答与原有记录', '',
              f'保留960份作答中，{summary["incorrect"]}份多数判错；其中原有保守语义复核确认至少{summary["confirmed_abstentions_lower_bound"]}份明确弃答（{100*summary["confirmed_abstentions_lower_bound"]/summary["incorrect"]:.1f}%）。只过滤既有标注，没有新增语义裁决；其余判错不能统称幻觉。', '',
              '原100题847正确、148错误、5待核与至少72份明确弃答的数字保留为历史结果。原6道质量标记中，另2道未列入本次排除，不把“未排除”解释为已证明没有题意问题。', '',
              '本次没有新作答或收费判分。历史实际运行的用量与费用估值仍覆盖100题及已知无效次，不能因为统计删题而按96/100缩减。原有时段、缓存、并发、项目中文回复指令等复现局限继续适用。', '',
              '[排除规则](policy.json) · [统计数据](summary.json) · [逐题记录](scoring-records.jsonl) · [逐次搜索展示](search-efficiency.html) · [原始来源与哈希回执](receipt.json) · [原100题报告](../../report-first-round-original-100.md)', '']
    return '\n'.join(lines)


def build():
    mf=read(SOURCE/'manifest.json');groups=mf['all_groups'];qids=mf['question_ids']
    if len(groups)!=10 or len(qids)!=100 or sha256(ROOT/'questions/questions.jsonl')!=mf['question_sha256']:
        raise BenchError('冻结题库或实验规模不符')
    receipt=read(SUPPLEMENT/'receipt.json')
    # Confirm the cached supplemental records still derive from the immutable source files.
    for name,digest in receipt['files'].items():
        if sha256(SUPPLEMENT/name)!=digest:raise BenchError('原补充分析文件变化: '+name)
    for name,digest in receipt['source_files_sha256'].items():
        if sha256(ROOT/name)!=digest:raise BenchError('原始来源变化: '+name)
    resources_receipt=read(SOURCE/'analysis/resources-receipt.json')
    for rel,digest in resources_receipt['file_sha256'].items():
        if sha256(SOURCE/rel)!=digest:raise BenchError('逐题资源来源变化: '+rel)
    if sha256(SOURCE/'analysis/resource-runs.jsonl')!=resources_receipt['resource_runs_sha256']:
        raise BenchError('逐题资源表变化')
    records=load_jsonl(SUPPLEMENT/'search-efficiency-records.jsonl')
    mapping=read(SOURCE/'grading/mapping.json');pending=load_jsonl(SOURCE/'grading/majority-needs-review.jsonl')
    if len(pending)!=5 or {mapping[r['id']]['question_id'] for r in pending}!=set(EXCLUDED):
        raise BenchError('四题/五份待核边界变化，停止自动修订')
    canonical={(r['group'],r['question_id']):('correct' if r['correct'] else 'incorrect') for r in load_jsonl(SOURCE/'grading/majority-resolved.jsonl')}
    canonical.update({(mapping[r['id']]['group'],mapping[r['id']]['question_id']):'uncertain' for r in pending})
    if any(canonical[r['group'],r['question_id']]!=r['verdict'] for r in records):raise BenchError('缓存判定与原多数票不同')
    kept,removed,ids=select_records(records,groups,qids,EXCLUDED)
    confirmed=[r for r in load_jsonl(SUPPLEMENT/'confirmed-abstentions.jsonl') if r['question_id'] not in EXCLUDED]
    resources=[r for r in load_jsonl(SOURCE/'analysis/resource-runs.jsonl') if r['question_id'] not in EXCLUDED]
    policy={'adopted_at':'2026-10-21','retrospective':True,'user_authorized':True,
            'authorization':'用户确认将四道争议题在所有组一起剔除，各组使用相同96题；不采用按组只排除待核回答的方案。',
            'scope':'first_round_only','exclusions':EXCLUDED,'original_questions_per_group':100,'retained_questions_per_group':96,
            'apply_to_all_groups':True,'exclude_correct_incorrect_and_uncertain':True,'original_votes_modified':False,
            'second_round_modified':False,'other_quality_flags_excluded':False}
    group_stats=aggregate(kept,groups,ids,resources,confirmed)
    summary={'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
             'complete':True,'round':'first_revised_96','policy':policy,'original_answer_records':1000,
             'n_questions':len(ids),'question_ids':ids,'groups':group_stats,'answer_records':len(kept),
             'excluded_answer_records':len(removed),'removed_outcomes':dict(collections.Counter(r['verdict'] for r in removed)),
             'correct':sum(r['verdict']=='correct' for r in kept),'incorrect':sum(r['verdict']=='incorrect' for r in kept),
             'uncertain':0,'confirmed_abstentions_lower_bound':len(confirmed),'comparisons':compare(kept,groups,ids),
             'paired_comparisons':efficiency.comparisons(kept,ids)}
    # Original supplemental records use paths at the same results/<name>/ depth.
    write_json(OUT/'policy.json',policy);write_json(OUT/'summary.json',summary)
    for filename,rows in [('scoring-records.jsonl',kept),('excluded-records.jsonl',removed),('resource-runs.jsonl',resources),('confirmed-abstentions.jsonl',confirmed)]:
        write_text(OUT/filename,''.join(dumps(r)+'\n' for r in rows))
    write_text(OUT/'report.md',markdown(summary))
    template=(ROOT/'tools/search-efficiency-template.html').read_text().replace('多语种搜索：次数、扣分与逐次返回','第一轮96题：次数、扣分与逐次返回').replace('/1200','/960').replace('例如 msqa-JA-60','例如 custom-001').replace('link.setAttribute("href","../"+r.raw)','link.setAttribute("href",r.raw)')
    template=re.sub(r'<label for="language">.*?</label>','<label for="language">题目语言<select id="language"><option value="">全部语言</option><option value="zh">中文</option><option value="en">英文</option></select></label>',template)
    payload=json.dumps({'summary':summary,'records':kept},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    write_text(OUT/'search-efficiency.html',template.replace('/*__BENCHMARK_DATA__*/',payload))
    sources=[SUPPLEMENT/'receipt.json',SUPPLEMENT/'search-efficiency-records.jsonl',SUPPLEMENT/'confirmed-abstentions.jsonl',
             SOURCE/'manifest.json',SOURCE/'grading/majority-resolved.jsonl',SOURCE/'grading/majority-needs-review.jsonl',
             SOURCE/'grading/mapping.json',SOURCE/'analysis/resource-runs.jsonl',SOURCE/'analysis/resources-receipt.json']
    write_json(OUT/'receipt.json',{'source_files_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in sources},
               'original_sources_verified':True,'tool_sha256':sha256(Path(__file__)),
               'retained_questions_per_group':96,'answer_records':960,'excluded_answer_records':40,
               'files':{p.name:sha256(p) for p in OUT.iterdir() if p.is_file() and p.name!='receipt.json'}})
    return summary


if __name__=='__main__':
    s=build()
    print(dumps({'retained_questions_per_group':s['n_questions'],'answer_records':s['answer_records'],
                 'correct':s['correct'],'incorrect':s['incorrect'],'excluded_outcomes':s['removed_outcomes'],
                 'groups':{g:{k:v[k] for k in ['correct','accuracy_percent','adjusted_score_mean']} for g,v in s['groups'].items()},
                 'comparisons':{k:{x:v[x] for x in ['n','difference_b_minus_a_pp','mcnemar','adjusted_score_difference']} for k,v in s['comparisons'].items() if k in {'A__B','A_prime__B_prime'}}}))
