"""复用第一轮原始作答和三票多数裁决，补算搜索扣分与明确弃答清单。"""
import collections, datetime, json, os, re
from pathlib import Path
import multilingual as m
import multilingual_search_efficiency as efficiency
from common import ROOT, load_jsonl, parse_stream, sha256, write_json, write_text, dumps

SOURCE = ROOT / 'tmp/archive'
OUT = ROOT / 'results/2026-10-20-supplement'
# 对原148份多数判错项按原文件顺序的保守AI语义补注，不是词匹配分类。
ABSTENTIONS = [1,2,3,4,9,10,11,12,13,14,15,17,18,19,24,25,28,34,36,37,38,40,41,44,45,47,50,52,53,54,56,62,63,68,69,70,71,72,73,75,76,77,81,82,83,84,90,93,95,98,100,101,107,110,112,113,121,122,123,124,126,128,130,133,135,138,141,142,145,146,147,148]

def read(p):
    return json.loads(p.read_text())

def build():
    mf = read(SOURCE/'manifest.json')
    qfile = ROOT/'questions/questions.jsonl'
    assert sha256(qfile) == mf['question_sha256']
    qs = {q['id']: q for q in load_jsonl(qfile)}
    mapping = read(SOURCE/'grading/mapping.json')
    blind = {r['id']: r for r in load_jsonl(SOURCE/'grading/blind.jsonl')}
    resolved = load_jsonl(SOURCE/'grading/majority-resolved.jsonl')
    pending = load_jsonl(SOURCE/'grading/majority-needs-review.jsonl')
    assert len(resolved) == 995 and len(pending) == 5
    judges = {j: {r['id']: r for r in load_jsonl(SOURCE/'jsonl/grades'/(j+'.jsonl'))} for j in ['claude','deepseek','independent']}
    assert len(mapping) == len(blind) == 1000 and all(set(t) == set(mapping) for t in judges.values())
    verdicts = {}
    for oid in mapping:
        votes = collections.Counter(t[oid]['verdict'] for t in judges.values())
        verdicts[oid] = next((v for v in ['correct','incorrect'] if votes[v] >= 2), 'uncertain')
    assert {r['id'] for r in pending} == {oid for oid,v in verdicts.items() if v == 'uncertain'}
    assert all(verdicts[r['id']] == ('correct' if r['correct'] else 'incorrect') for r in resolved)
    wrong = [r for r in resolved if not r['correct']]
    assert len(wrong) == 148 and len(ABSTENTIONS) == len(set(ABSTENTIONS)) == 72
    abstained = {wrong[i-1]['id'] for i in ABSTENTIONS}
    lookup = {(meta['group'],meta['question_id']): oid for oid,meta in mapping.items()}
    records, confirmed, sources = [], [], {}
    for group in mf['all_groups']:
        for qid in mf['question_ids']:
            oid = lookup[group,qid]
            path = SOURCE/'runs'/group/(qid+'.json')
            assert sha256(path) == mapping[oid]['run_sha256']
            run = m.check_run(SOURCE,group,qs[qid],mf['config'])
            assert run['answer'] == blind[oid]['candidate_answer']
            raw = SOURCE/run['raw']
            events,_ = parse_stream(raw.read_text(),allowed_budget_denial_ids={r.get('tool_use_id') for r in run.get('budget_denials',[])})
            record = {'group':group,'group_name':efficiency.NAMES[group],'question_id':qid,'lang':qs[qid]['lang'],'question':qs[qid]['question'],'reference_answer':qs[qid]['answer'],'candidate_answer':run['answer'],'verdict':verdicts[oid],'search_calls':run['search_calls'],'search_attempts':run['search_attempts'],'budget_denials':run['search_budget_denials'],'argument_rejections':run.get('search_argument_rejections',0),'adjusted_score':efficiency.score(verdicts[oid],run['search_calls']),'possible_correct_score':efficiency.score('correct',run['search_calls']),'searches':efficiency.search_details(events,run),'raw':os.path.relpath(raw,OUT),'source_raw':run['raw']}
            records.append(record)
            if oid in abstained:
                confirmed.append(dict(record,id=oid,source_run_sha256=sha256(path),original_verdict='incorrect',original_votes={j:t[oid]['verdict'] for j,t in judges.items()},supplemental_label='confirmed_explicit_abstention',reason_from_original_independent_vote=judges['independent'][oid]['reason']))
            for p in [path,raw]: sources[str(p.relative_to(ROOT))] = sha256(p)
    assert len(records) == 1000 and len(confirmed) == 72
    policy = {'retrospective':True,'original_grading_method':'three_ai_majority','source_vote_records':3000,'penalty_per_additional_search':5,'first_search_free':True,'incorrect_score':0,'uncertain_handling':'待核按0至假设答对时的扣分后分数给区间','notes':['按用户要求将运行中新增的5分规则事后回算第一轮；不改原题、原始作答、三票判分或原正确率。','只扣实际执行的搜索；未执行的参数与预算拒绝不计；失败无效次仍另存。','明确弃答72是AI语义复核确认的保守下界，不是完整弃答率或幻觉率。']}
    groups = efficiency.summarize(records,mf['all_groups'])
    for group,row in groups.items(): row['confirmed_abstentions_lower_bound'] = sum(r['group'] == group for r in confirmed)
    summary = {'complete':True,'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'round':'first','answer_records':1000,'grade_records':1000,'source_vote_records':3000,'original_correct':sum(r['verdict']=='correct' for r in records),'original_incorrect':148,'original_uncertain':5,'confirmed_abstentions_among_original_incorrect':72,'confirmed_count_is_lower_bound':True,'policy':policy,'groups':groups,'paired_comparisons':efficiency.comparisons(records,mf['question_ids'])}
    write_json(OUT/'summary.json',summary)
    write_text(OUT/'search-efficiency-records.jsonl',''.join(dumps(r)+'\n' for r in records))
    write_text(OUT/'confirmed-abstentions.jsonl',''.join(dumps(r)+'\n' for r in confirmed))
    template=(ROOT/'tools/search-efficiency-template.html').read_text().replace('多语种搜索：次数、扣分与逐次返回','第一轮中英文搜索：次数、扣分与逐次返回').replace('/1200','/1000').replace('例如 msqa-JA-60','例如 custom-001').replace('link.setAttribute("href","../"+r.raw)','link.setAttribute("href",r.raw)')
    template=re.sub(r'<label for="language">.*?</label>','<label for="language">题目语言<select id="language"><option value="">全部语言</option><option value="zh">中文</option><option value="en">英文</option></select></label>',template)
    template=template.replace('<h2>各组总览</h2>','<p>第一轮采用三位AI多数票；本页沿用原裁决，搜索扣分是事后新增分析。</p><h2>各组总览</h2>')
    payload=json.dumps({'summary':summary,'records':records},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    write_text(OUT/'search-efficiency.html',template.replace('/*__BENCHMARK_DATA__*/',payload))
    lines=['# 第一轮中英文搜索的补充分析','','十组各100题，共1000份答案；沿用原三位AI多数裁决，847正确、148错误、5待核。搜索扣分与明确弃答是2026年10月21日按用户要求追加的事后分析，不覆盖第一轮原结果。','','## 搜索次数与扣分','','答对100分，首次搜索不扣，之后每次扣5分；答错0分；待核按0至其假设答对时可得分计区间。下表分数范围来自待核，不是置信区间。','','| 模型与工具 | 原正确率范围% | 扣分后均分/100 | 平均搜索次数 | 原判错中的明确弃答 至少 |','|---|---:|---:|---:|---:|']
    for row in groups.values(): lines.append(f'| {row["name"]} | {efficiency.bounds(row["accuracy_bounds_on_graded"])} | {efficiency.bounds(row["adjusted_score_bounds_on_graded"])} | {row["mean_search_calls"]:.2f} | {row["confirmed_abstentions_lower_bound"]} |')
    lines+=['','## 同题扣分后比较','','差值均为DeepSeek搜索减原生搜索。全题范围包括未决；bootstrap仅使用共同已判题。']
    for label,v in summary['paired_comparisons'].items():
        b=v['conditional_bootstrap_points'];lines+=['',f'- {label}：全100题分差 {efficiency.bounds(v["all_question_difference_bounds_points"])}；共同已判n={b["n"]}，条件均差{b["estimate"]:.2f}，95%区间[{b["ci95"][0]:.2f}, {b["ci95"][1]:.2f}]。']
    lines+=['','## 明确弃答与其他错误','','原148份多数判错中，确认至少72份明确不提供所求答案，占48.6%；余76份不全部归为幻觉。含不确定候选、撤回、部分回答的边界项不强判；表中0表示本次清单未确认，不证明实际没有弃答。5份待核单列。','','复核原148份判错的匿名回答及既有独立票理由，按语义标注、回看必要原文；没有新调用被测模型或收费评分API。只针对问题所求答案，弃答背景仍可能出错。两轮都是保守确认清单，不能将下界直接当完整弃答率或比较模型拒答倾向。','','[72份弃答完整原文](confirmed-abstentions.jsonl)、[全部1000份查询与返回摘要](search-efficiency.html)、[逐题数据](search-efficiency-records.jsonl)、[统计数据](summary.json)、[第一轮原完整报告](../../tmp/archive/analysis/report.md)。']
    write_text(OUT/'report.md','\n'.join(lines)+'\n')
    for rel in ['manifest.json','grading/majority-receipt.json','grading/majority-resolved.jsonl','grading/majority-needs-review.jsonl','grading/blind.jsonl','grading/mapping.json']:
        sources[str((SOURCE/rel).relative_to(ROOT))]=sha256(SOURCE/rel)
    for j in judges:sources[str((SOURCE/'jsonl/grades'/(j+'.jsonl')).relative_to(ROOT))]=sha256(SOURCE/'jsonl/grades'/(j+'.jsonl'))
    write_json(OUT/'receipt.json',{'generated_at':summary['generated_at'],'answer_records':1000,'source_vote_records':3000,'source_files_sha256':sources,'tool_sha256':sha256(Path(__file__)),'reused_tool_sha256':sha256(ROOT/'tools/multilingual_search_efficiency.py'),'template_sha256':sha256(ROOT/'tools/search-efficiency-template.html'),'files':{p.name:sha256(p) for p in OUT.iterdir() if p.is_file() and p.name!='receipt.json'}})
    return summary

if __name__ == '__main__':
    s=build()
    print(dumps({'answers':s['answer_records'],'correct':s['original_correct'],'incorrect':148,'pending':5,'confirmed_abstentions_lower_bound':72,'report':str(OUT/'report.md')}))
