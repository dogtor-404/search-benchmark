"""402份不搜索组错答的双盲四类计数、配对比较及均衡案例。"""
import collections, datetime, json, math, os, sys
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[4]))
sys.path.insert(0,str(ROOT/'tools'))
import analyze
OUT=ROOT/'results/2026-10-21-response-review/no-search-double-blind'
LABELS={'explicit_abstention':'明确弃答','confident_incorrect_assertion':'错误的确定断言','incomplete_answer':'不完整回答','hedged_or_withdrawn_guess':'试猜或猜到后撤回'}
GROUPS=['0','D0','0_prime','D0_prime']
NAMES={'0':'Sonnet','D0':'DeepSeek Flash','0_prime':'Opus','D0_prime':'DeepSeek Pro'}
TARGET='confident_incorrect_assertion'

def read(p):return json.loads(p.read_text())
def jl(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def sha(p):
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()
def interval(values):return analyze.bootstrap(values,seed=20261021) if values else None
def paired(claude,deepseek,ids,values):
    common=[q for q in ids if values.get((claude,q)) is not None and values.get((deepseek,q)) is not None]
    a=[values[claude,q] for q in common];b=[values[deepseek,q] for q in common]
    return {'known_pair_n':len(common),'mcnemar':analyze.mcnemar(a,b) if common else None,'difference_deepseek_minus_claude_bootstrap':interval([y-x for x,y in zip(a,b)])}

def build():
    protocol=read(OUT/'protocol.json');receipt=read(OUT/'resolution-receipt.json');rows=jl(OUT/'resolved.jsonl')
    assert len(rows)==len({r['id'] for r in rows})==402 and sha(OUT/'resolved.jsonl')==receipt['resolved_sha256']
    assert sha(OUT/'rubric.md')==protocol['rubric_sha256']==receipt['rubric_sha256']
    for rel,digest in protocol['source_files_sha256'].items():assert sha(ROOT/rel)==digest,rel
    original={};known_flags={};source_summaries={};source_extra={}
    for rd,folder,rel in [('first','tmp/archive','grading/majority-resolved.jsonl'),('second','results/2026-10-21-multilingual','grading/independent-resolved.jsonl')]:
        source=ROOT/folder;mf=read(source/'manifest.json');resolved=jl(source/rel)
        original[rd]={'ids':mf['question_ids'],'status':{(r['group'],r['question_id']):r['correct'] for r in resolved},'source':source}
        summary=read(source/'analysis/full-summary.json');source_summaries[rd]=summary
        known_flags[rd]=set(summary.get('quality_flagged_question_ids',[]))
        source_extra[str((source/'analysis/full-summary.json').relative_to(ROOT))]=sha(source/'analysis/full-summary.json')
    known_flags['second'].add('msqa-RU-04')
    checks=read(OUT/'example-fact-checks.json')
    check_map={(r['round'],r['question_id']):r for r in checks['checks']}
    post_flags={rd:{r['question_id'] for r in checks['checks'] if r['round']==rd and r['reference_concern']} for rd in original}
    all_flags={rd:known_flags[rd]|post_flags[rd]|{r['question_id'] for r in rows if r['round']==rd and r['reference_concern']} for rd in original}
    counters={};examples={};values={rd:{} for rd in original};lookup={(r['round'],r['group'],r['question_id']):r for r in rows}
    for rd in original:
        for g in GROUPS:
            selected=[r for r in rows if r['round']==rd and r['group']==g];counts={k:sum(r['category']==k for r in selected) for k in LABELS};n=100 if rd=='first' else 120
            assert len(selected)==protocol['cohorts'][rd]['by_group'][g] and sum(counts.values())==len(selected)
            pending=sum((g,q) not in original[rd]['status'] for q in original[rd]['ids'])
            for q in original[rd]['ids']:
                correct=original[rd]['status'].get((g,q))
                values[rd][g,q]=None if correct is None else 0 if correct else int(lookup[rd,g,q]['category']==TARGET)
            c=counts[TARGET]
            key=rd+'__'+g
            counters[key]={'round':rd,'group':g,'model':NAMES[g],'all_questions':n,'original_incorrect':len(selected),'original_pending':pending,'category_counts':counts,'confident_incorrect_count':c,'confident_incorrect_fraction_all_questions':c/n,'confident_incorrect_percent_all_questions':100*c/n,'potential_percent_bounds_if_original_pending_resolved_as_confident_errors':[100*c/n,100*(c+pending)/n],'reference_concern_count_any_judge':sum(r['reference_concern'] for r in selected),'confident_incorrect_with_reference_concern':sum(r['category']==TARGET and (r['reference_concern'] or r['question_id'] in known_flags[rd]) for r in selected)}
            eligible=[r for r in selected if r['category']==TARGET and r['question_id'] not in all_flags[rd]]
            eligible.sort(key=lambda r:((rd,r['question_id']) not in check_map,r['resolution']!='two_independent_agreement',len(r['candidate_answer']),r['question_id']))
            chosen=eligible[:2]
            examples[key]={'requested':2,'available_confident_incorrect_total':c,'eligible_without_reference_concern':len(eligible),'selected':[dict(r,example_fact_check=check_map.get((rd,r['question_id']))) for r in chosen],'all_confident_incorrect_records_including_flagged':[dict(r,display_reference_concern=r['question_id'] in all_flags[rd],example_fact_check=check_map.get((rd,r['question_id']))) for r in sorted(selected,key=lambda r:r['question_id']) if r['category']==TARGET],'selection_rule':'每组同一规则：排除任一判分员、既有质量标记及选例来源核对的参考疑问；优先有补充核查记录，再优先两票一致，随后按回答长度、题号排序，最多2例。不凑数。核查在揭盲后进行，不用于改变分类计数。'}
            counters[key]['confident_incorrect_with_any_reference_flag']=sum(r['category']==TARGET and r['question_id'] in all_flags[rd] for r in selected)
    a={r['id']:r for r in jl(OUT/'votes/reviewer-a.jsonl')};b={r['id']:r for r in jl(OUT/'votes/reviewer-b.jsonl')}
    matrix={x:{y:sum(a[r['id']]['category']==x and b[r['id']]['category']==y for r in rows) for y in LABELS} for x in LABELS}
    agreement=sum(a[r['id']]['category']==b[r['id']]['category'] for r in rows);po=agreement/402
    pe=sum(sum(matrix[x].values())*sum(matrix[y][x] for y in LABELS) for x in LABELS)/402**2
    reliability={'records':402,'agreed':agreement,'disagreed':402-agreement,'agreement_fraction':po,'cohens_kappa':(po-pe)/(1-pe) if pe<1 else 1,'confusion_matrix':matrix,'third_matches_a':sum(r['resolution']=='third_independent_adjudication' and r['category']==a[r['id']]['category'] for r in rows),'third_matches_b':sum(r['resolution']=='third_independent_adjudication' and r['category']==b[r['id']]['category'] for r in rows),'third_new_category':sum(r['resolution']=='third_independent_adjudication' and r['category'] not in [a[r['id']]['category'],b[r['id']]['category']] for r in rows)}
    comparisons={}
    for rd in original:
        ids=original[rd]['ids'];n=len(ids)
        for tier,cg,dg in [('mid','0','D0'),('high','0_prime','D0_prime')]:
            cv=counters[rd+'__'+cg];dv=counters[rd+'__'+dg];cc=cv['confident_incorrect_count'];dc=dv['confident_incorrect_count']
            entry={'round':rd,'tier':tier,'claude_group':cg,'deepseek_group':dg,'all_questions':n,'claude_confident_incorrect_count':cc,'deepseek_confident_incorrect_count':dc,'observed_percent_difference_deepseek_minus_claude':100*(dc-cc)/n,'full_question_difference_percent_bounds_allowing_original_pending':[100*(dc-cc-cv['original_pending'])/n,100*(dc-cc+dv['original_pending'])/n],'sample_fewer':'claude' if cc<dc else 'deepseek' if dc<cc else 'tie','conditional_paired':paired(cg,dg,ids,values[rd]),'reference_concern_sensitivity':{'excluded_question_ids':sorted(all_flags[rd]),'label':'事后探索性排除参考疑问题；疑问未全部查实，不替代全题主结果','paired':paired(cg,dg,[q for q in ids if q not in all_flags[rd]],values[rd])}}
            comparisons[rd+'__'+tier]=entry
    ordered=sorted(comparisons,key=lambda k:comparisons[k]['conditional_paired']['mcnemar']['p_exact']);previous=0
    for i,key in enumerate(ordered):
        p=comparisons[key]['conditional_paired']['mcnemar']['p_exact'];adjusted=max(previous,min(1,p*(len(ordered)-i)));comparisons[key]['conditional_paired']['p_holm_four_comparisons']=adjusted;previous=adjusted
    revised=None
    policy_path=ROOT/'results/2026-10-20-revised-96/policy.json'
    if policy_path.exists():
        policy=read(policy_path);excluded=set(policy['exclusions']);kept=[r for r in rows if r['round']=='first' and r['question_id'] not in excluded]
        revised={'scope':'项目当前96题视图：仅从已完成的原100题盲判中按现有统一排除规则过滤，不新增判分、不替代本次请求的100题主计数。','policy_sha256':sha(policy_path),'all_questions_per_group':96,'excluded_question_ids':sorted(excluded),'retained_incorrect_records':len(kept),'groups':{}}
        source_extra[str(policy_path.relative_to(ROOT))]=sha(policy_path)
        for g in GROUPS:
            selected=[r for r in kept if r['group']==g];counts={k:sum(r['category']==k for r in selected) for k in LABELS}
            revised['groups'][g]={'model':NAMES[g],'original_incorrect':len(selected),'category_counts':counts,'confident_incorrect_percent_all_questions':100*counts[TARGET]/96}
    summary={'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'complete':True,'records':402,'round_records':{'first':127,'second':275},'category_labels':LABELS,'category_totals':{k:sum(r['category']==k for r in rows) for k in LABELS},'method':{'independent_reviewers':2,'records_per_reviewer':402,'adjudicator_records':402-agreement,'disagreement_resolution':protocol['scoring'],'blind_fields':['id','question','reference_answer','aliases','candidate_answer'],'identity':'三个Codex agent分别使用独立上下文；不是不同基础模型交叉评测','deepseek_judging_api_calls':0,'original_grades_changed':False,'reference_concern_is_separate_flag':True,'rubric_sha256':protocol['rubric_sha256']},'metric_definition':'原判错且本次归为错误的确定断言的数量/该组全部题数（第一轮原100、第二轮120）；不是全部回答逐断言核查得到的严格幻觉率。','uncertainty':'原判对/原待核不在402分类材料中；待核未入已确认分子，另给可能范围。配对检验仅共同原已判样本，四项检验给Holm校正，跨轮不合并。','groups':counters,'comparisons':comparisons,'reliability':reliability,'first_round_current_96_view':revised,'examples':{k:{kk:vv for kk,vv in v.items() if kk not in ['selected','all_confident_incorrect_records_including_flagged']} for k,v in examples.items()},'known_reference_flags':{k:sorted(v) for k,v in known_flags.items()},'post_unblind_example_check_flags':{k:sorted(v) for k,v in post_flags.items()},'all_reference_flags':{k:sorted(v) for k,v in all_flags.items()},'notes':['这是按用户要求追加的事后回答类型分类，不改原答案、原正确率或搜索扣分。','确定性按核心答案的文字表达判断，不推断模型内部是否知道或是否有意编造。','原参考可能有争议，主计数仍按冻结原判错；疑问单列，例子排除这些题。','旧72/112清单包含搜索组，且没有采用本次四类互斥规则；边界回答会重新分入试猜/撤回或不完整，因此旧弃答数也不是新类别的保证下界。']}
    write(OUT/'summary.json',summary);write(OUT/'examples.json',examples)
    lines=['# 两轮不搜索组错答的四类盲判复核','','仅复核用户指定的原已判错：第一轮原100题中的127份、第二轮120题中的275份，共402份。两位独立Codex agent分别读匿名原文，不看组别、轮次、旧判分理由或对方判断；一致直接采用，分歧由第三位独立裁决，第三位也不看前两票。三个独立上下文使用同一基础模型，不是跨模型复核。本次DeepSeek判分API调用为0。','','类别互斥：明确弃答、错误的确定断言、不完整回答、试猜或猜到后撤回。规则在判分前冻结，完整语义定义见 [分类规则](rubric.md)。原成绩保持不变。项目另有第一轮96题修订主表，本次按用户指定保留100题主复核，后附同一分类过滤到96题的视图。','','## 每组四类计数','']
    for rd,title in [('first','第一轮 中英文 每组100题'),('second','第二轮 六语种 每组120题')]:
        lines += ['### '+title,'','| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 原判错合计 | 确定错误断言/全部题 |','|---|---:|---:|---:|---:|---:|---:|']
        for g in GROUPS:
            r=counters[rd+'__'+g];counts=r['category_counts'];lines.append('| '+r['model']+' | '+' | '.join(str(counts[k]) for k in LABELS)+' | '+str(r['original_incorrect'])+' | '+f'{r["confident_incorrect_count"]}/{r["all_questions"]} = {r["confident_incorrect_percent_all_questions"]:.2f}%'+' |')
        lines.append('')
    lines+=['四类之和等于每组原判错数，两个轮次分别合计127和275。比例分母使用100和120，不是错误数；原待核未入已确认分子。这里的确定错误断言按原参考答案及输出表述定义，含参考疑问项，不能直接称为严格幻觉率。','','第一轮Sonnet/Flash为2/6，Opus/Pro为2/7，样本差异尚不足以判稳定输赢。第二轮分别为10/27和11/31；在本次题集、原判分及本分类口径下，Claude两档均较少，四项比较的Holm校正后仍支持差异。结论仅限这批题，不表示所有小语种或所有任务的总体排名。','','## 同档 Claude 与 DeepSeek 的比较','','差值为DeepSeek减Claude，正值表示Claude这类错误更少。点值按全部100/120题；配对检验与bootstrap仅用双方原已判的同题。','','| 轮次与档位 | Claude 数量/全部题 | DeepSeek 数量/全部题 | 样本比例差 个百分点 | 共同已判n | 条件配对差95%区间 个百分点 | McNemar p | 四项Holm校正p |','|---|---:|---:|---:|---:|---|---:|---:|']
    for key,r in comparisons.items():
        stat=r['conditional_paired'];boot=stat['difference_deepseek_minus_claude_bootstrap'];ci=boot['ci95'];name=('第一轮' if r['round']=='first' else '第二轮')+(' 中档' if r['tier']=='mid' else ' 高档');lines.append(f'| {name} | {r["claude_confident_incorrect_count"]}/{r["all_questions"]} | {r["deepseek_confident_incorrect_count"]}/{r["all_questions"]} | {r["observed_percent_difference_deepseek_minus_claude"]:+.2f} | {stat["known_pair_n"]} | [{ci[0]*100:.2f}, {ci[1]*100:.2f}] | {stat["mcnemar"]["p_exact"]:.4f} | {stat["p_holm_four_comparisons"]:.4f} |')
    lines+=['','置信区间跨0或校正后检验不支持差异时，不能将样本中的数量差写成稳定胜负。两轮题集及原正确性评分口径不同，分别比较，不汇总成模型总排名。原待核可能改变完整题集的差值；上下界保存在 [统计数据](summary.json)。','','### 参考疑问的探索性敏感性分析','','按题号在同档双方统一排除任一判分员、既有质量标记及选例核查提出的参考疑问。它们并未全部证实参考错误，此表不替代上方冻结参考主计数。','','| 轮次与档位 | 排除后共同已判n | DeepSeek减Claude 个百分点 | McNemar p（未校正，探索性） |','|---|---:|---:|---:|']
    for r in comparisons.values():
        st=r['reference_concern_sensitivity']['paired'];name=('第一轮' if r['round']=='first' else '第二轮')+(' 中档' if r['tier']=='mid' else ' 高档')
        lines.append(f'| {name} | {st["known_pair_n"]} | {100*st["difference_deepseek_minus_claude_bootstrap"]["estimate"]:+.2f} | {st["mcnemar"]["p_exact"]:.5f} |')
    lines+=['','## 选例核查中新增的参考疑问','','主计数按冻结参考保留，不把下列题作为无争议的幻觉例子。核查发生在揭盲后，完全独立于三位匿名类别裁决。完整说明与链接见 [选例核查记录](example-fact-checks.json)。','']
    for c in checks['checks']:
        if c['reference_concern']:lines+=['- '+c['question_id']+'：'+c['note']+' '+'、'.join('['+s['title']+']('+s['url']+')' for s in c['sources'])+'。']
    if revised:
        lines+=['','## 项目当前第一轮96题视图','','以下只按项目既有4题统一排除规则过滤同一批分类，供与当前主表对照；不替代用户指定的原100题复核。其余参考疑问没有追加到项目删题规则。','','| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 保留判错合计 | 确定错误断言/96 |','|---|---:|---:|---:|---:|---:|---:|']
        for g in GROUPS:
            r=revised['groups'][g];lines.append('| '+r['model']+' | '+' | '.join(str(r['category_counts'][k]) for k in LABELS)+f' | {r["original_incorrect"]} | {r["confident_incorrect_percent_all_questions"]:.2f}% |')
    lines+=['','## 判分一致性','',f'两位独立判分一致 {agreement}/402（{po*100:.2f}%），分歧 {402-agreement}份全部交第三位独立裁决；Cohen κ={reliability["cohens_kappa"]:.4f}。第三位在{reliability["third_new_category"]}份中选择前两票之外的类别，这些按预定独立裁决规则采用，并保留三张原票。','','[逐题最终类别与证据](resolved.jsonl)、[判分员A](votes/reviewer-a.jsonl)、[判分员B](votes/reviewer-b.jsonl)、[第三位裁决](votes/adjudicator.jsonl)、[裁决凭据](resolution-receipt.json)。','','## 每组确定错误断言案例','','每组采用同一选择规则：排除任一判分员、既有质量标记及选例核查的参考疑问，优先有补充核查记录，再优先两票一致，随后按回答长度、题号排序，最多两例。不为凑数放宽类别；未选中不影响完整计数。原文、参考答案与来源网址并列，模型名称在分类完成后才还原。全部此类记录（含有争议而未展示的）也保留在 [结构化案例](examples.json) 的 all_confident_incorrect_records_including_flagged 字段，便于核对每组两例为何不足。','']
    for rd in ['first','second']:
        for g in GROUPS:
            entry=examples[rd+'__'+g];lines += ['### '+('第一轮' if rd=='first' else '第二轮')+' '+NAMES[g],'']
            if len(entry['selected'])<2:lines += [f'本组最终共{entry["available_confident_incorrect_total"]}份此类错误，排除参考疑问后可用{entry["eligible_without_reference_concern"]}例，因此只展示{len(entry["selected"])}例。','']
            for r in entry['selected']:
                lines += ['#### '+r['question_id'],'','题目：'+r['question'],'','参考答案：'+r['reference_answer'],'','候选回答：','','> '+r['candidate_answer'].replace('\n','\n> '),'','分类依据：'+r['rationale'],'','原始输出：[完整记录]('+os.path.relpath(ROOT/r['source_raw'],OUT)+')；参考来源：'+'、'.join('['+str(i+1)+']('+url+')' for i,url in enumerate(r['question_source_urls']))+'。','']
                c=r.get('example_fact_check')
                if c:lines+=['补充核查：'+c['note']+' '+'、'.join('['+s['title']+']('+s['url']+')' for s in c['sources'])+'。','']
    lines+=['## 范围与原结果','','本次只给原判错核心答案分类，没有逐条审核所有回答的附带事实，也没有重新校正有争议的参考答案。确定断言是文字表述类别，不证明有意造假或可观察到模型内部确信度。旧有72/112条清单仍保留为历史补充，不能替代本次402条双盲分类；旧清单未采用本次四类互斥规则，因此也不能继续作为本次明确弃答类别的保证下界。','','[原始选择与匿名化凭据](protocol.json)、[完整结构化计数](summary.json)、[结构化案例](examples.json)。','']
    (OUT/'report.md').write_text('\n'.join(lines))
    write(OUT/'report-receipt.json',{'generated_at':summary['generated_at'],'records':402,'resolved_sha256':receipt['resolved_sha256'],'protocol_sha256':sha(OUT/'protocol.json'),'rubric_sha256':protocol['rubric_sha256'],'tool_sha256':sha(Path(__file__)),'source_summary_sha256':source_extra,'files':{p.name:sha(p) for p in [OUT/'summary.json',OUT/'examples.json',OUT/'report.md',OUT/'example-fact-checks.json']}})
    print(json.dumps({'groups':8,'records':402,'agreement':agreement,'disagreements':402-agreement,'category_totals':summary['category_totals'],'example_shortfalls':{k:len(v['selected']) for k,v in examples.items() if len(v['selected'])<2},'report':str(OUT/'report.md')},ensure_ascii=False))
    return summary

if __name__=='__main__':build()
