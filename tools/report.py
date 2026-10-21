#!/usr/bin/env python3
"""正式评测的可复现临时报告：保留未决项，不强制排名。"""
import collections,datetime,itertools,json,math,statistics,sys
from common import ROOT,BenchError,load_jsonl,parse_stream,sha256,dumps,write_json,write_text
import bench,search_run,analyze
LABELS={'0':'Sonnet 不搜索','A':'Sonnet + Claude搜索','B':'Sonnet + DeepSeek搜索','D0':'Flash 不搜索','D2':'Flash + DeepSeek搜索','0_prime':'Opus 不搜索','A_prime':'Opus + Claude搜索','B_prime':'Opus + DeepSeek搜索','D0_prime':'Pro 不搜索','D2_prime':'Pro + DeepSeek搜索'}
BASE={'A':'0','B':'0','D2':'D0','A_prime':'0_prime','B_prime':'0_prime','D2_prime':'D0_prime'}
def percentile90(values):
 if not values:raise BenchError('没有耗时数据。')
 return sorted(values)[math.ceil(len(values)*.9)-1]
def contrast_bounds(table,ids,terms):
 lo=hi=0
 for q in ids:
  for g,c in terms:
   value=table.get((g,q))
   if value is None:lo+=min(0,c);hi+=max(0,c)
   else:lo+=c*value;hi+=c*value
 return [lo/len(ids),hi/len(ids)]
def paired(table,ids,a,b):
 common=[q for q in ids if (a,q) in table and (b,q) in table]
 unknown=[(g,q) for q in ids for g in [a,b] if (g,q) not in table]
 if len(unknown)>15:raise BenchError('未决项太多，不能枚举配对检验范围。')
 ps=[]
 for vals in itertools.product([0,1],repeat=len(unknown)):
  completed=dict(table);completed.update(zip(unknown,vals));ps.append(analyze.mcnemar([completed[a,q] for q in ids],[completed[b,q] for q in ids])['p_exact'])
 return {'difference_b_minus_a_bounds':contrast_bounds(table,ids,[(b,1),(a,-1)]),'complete_pairs_n':len(common),'complete_pairs':analyze.mcnemar([table[a,q] for q in common],[table[b,q] for q in common]),'p_exact_completion_range':[min(ps),max(ps)]}
def bounds_string(x,percent=True):
 return (f'{x[0]*100:.1f}–{x[1]*100:.1f}' if percent else f'{x[0]:.2f}–{x[1]:.2f}')
def group_scores(rows,ids,groups):
 out={}
 for g in groups:
  rr=[r for r in rows if r['group']==g];c=sum(r['correct'] for r in rr);w=len(rr)-c;u=len(ids)-len(rr);out[g]={'correct':c,'incorrect':w,'pending':u,'accuracy_bounds':[c/len(ids),(c+u)/len(ids)]}
 return out

def build(out,source):
 manifest=json.loads((out/'manifest.json').read_text());cfg=manifest['config'];ids=manifest['question_ids'];groups=manifest['all_groups'];questions=load_jsonl(ROOT/'questions/questions.jsonl');qs={q['id']:q for q in questions}
 if manifest['question_sha256']!=sha256(ROOT/'questions/questions.jsonl') or manifest['config_sha256']!=sha256(bench.CONFIG):raise BenchError('题库或配置漂移。')
 search_run.validate_source(source,questions,cfg,manifest['claude_code_version'])
 runs={}
 for g in groups:
  for q in questions:
   if cfg['groups'][g]['search']!='none':r=search_run.validate_search_result(out,g,q,cfg)
   else:r=json.loads((out/'runs'/g/(q['id']+'.json')).read_text())
   runs[g,q['id']]=r
 for judge in ['claude','deepseek']:
  rows=load_jsonl(out/'jsonl/grades'/(judge+'.jsonl'))
  if len(rows)!=len(ids)*len(groups) or len({r['id'] for r in rows})!=len(rows):raise BenchError('正式判分覆盖不全或ID重复。')
  for r in rows:
   raw=out/'grading/raw'/judge/(r['id']+'.jsonl')
   if sha256(raw)!=r['raw_sha256']:raise BenchError('判分原文散列不符。')
   events,final=parse_stream(raw.read_text(),allow_structured=True);bench.verify_events(events,{'search':'none','structured_output':True});v=final.get('structured_output') or json.loads(final['result'])
   if v!={k:r[k] for k in ['verdict','reason']}:raise BenchError('判分记录与原文不同。')
 majority_rows=load_jsonl(out/'grading/majority-resolved.jsonl');dual_rows=load_jsonl(out/'grading/resolved.jsonl');pending=load_jsonl(out/'grading/majority-needs-review.jsonl');mapping=json.loads((out/'grading/mapping.json').read_text());table={(r['group'],r['question_id']):int(r['correct']) for r in majority_rows}
 if len(table)+len(pending)!=len(ids)*len(groups):raise BenchError('多数票覆盖不完整。')
 scores=group_scores(majority_rows,ids,groups);dual=group_scores(dual_rows,ids,groups)
 independent=load_jsonl(out/'jsonl/grades/independent.jsonl');flagged=sorted({mapping[r['id']]['question_id'] for r in independent if r['verdict']=='uncertain'}|{'frames-137','frames-598'})
 resource_path=out/'analysis/resources.json';resources=json.loads(resource_path.read_text());resource_receipt=json.loads((out/'analysis/resources-receipt.json').read_text())
 if resource_receipt['resources_sha256']!=sha256(resource_path):raise BenchError('资源汇总散列不符。')
 for relative,digest in resource_receipt['file_sha256'].items():
  if sha256(out/relative)!=digest:raise BenchError('资源汇总源文件变化。')
 report={'status':'complete_with_unresolved_review','generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'n_questions':len(ids),'answer_records':len(runs),'dual_scores':dual,'majority_scores':scores,'majority_pending':len(pending),'quality_flagged_question_ids':flagged,'groups':{},'lifts':{},'comparisons':{},'exploratory_contrasts':{},'sensitivity_without_quality_flags':{},'costs':{}}
 for g in groups:
  rr=[runs[g,q] for q in ids];times=[r['elapsed_seconds'] for r in rr];hits=[analyze.source_hit(qs[q],runs[g,q]) for q in ids] if cfg['groups'][g]['search']!='none' else [];observed=[x for x in hits if x is not None]
  report['groups'][g]={'label':LABELS[g],'mean_seconds':statistics.mean(times),'median_seconds':statistics.median(times),'p90_seconds_nearest_rank':percentile90(times),'max_seconds':max(times),'mean_search_calls':statistics.mean(r['search_calls'] for r in rr),'search_calls':sum(r['search_calls'] for r in rr),'search_attempts':sum(r['search_attempts'] for r in rr),'budget_denials':sum(r.get('search_budget_denials',0) for r in rr),'argument_rejections':sum(r.get('search_argument_rejections',0) for r in rr),'search_fee_estimate_usd':sum(r['search_cost_usd'] for r in rr),'reported_model_nominal_usd':sum(r.get('reported_cost_usd') or 0 for r in rr),'source_hit_at5':sum(observed)/len(observed) if observed else None,'source_hit_observable_n':len(observed),'resources':resources['groups'][g]}
 for g,b in BASE.items():
  deltas=[runs[g,q]['elapsed_seconds']-runs[b,q]['elapsed_seconds'] for q in ids]
  report['lifts'][g]={'baseline':b,'accuracy_lift_bounds':contrast_bounds(table,ids,[(g,1),(b,-1)]),'paired_mean_added_seconds':statistics.mean(deltas),'paired_median_added_seconds':statistics.median(deltas),'paired_p90_added_seconds':percentile90(deltas)}
 for a,b in [('A','B'),('A_prime','B_prime')]:report['comparisons'][a+'__'+b]=paired(table,ids,a,b)
 terms=[('Sonnet的DeepSeek搜索提升减Flash的提升',[('B',1),('0',-1),('D2',-1),('D0',1)]),('Opus的DeepSeek搜索提升减Pro的提升',[('B_prime',1),('0_prime',-1),('D2_prime',-1),('D0_prime',1)]),('Claude使用DeepSeek搜索：高档提升减中档提升',[('B_prime',1),('0_prime',-1),('B',-1),('0',1)]),('DeepSeek：高档提升减中档提升',[('D2_prime',1),('D0_prime',-1),('D2',-1),('D0',1)]),('Claude原生搜索：高档提升减中档提升',[('A_prime',1),('0_prime',-1),('A',-1),('0',1)])]
 for name,ts in terms:
  complete=[q for q in ids if all((g,q) in table for g,c in ts)];values=[sum(c*table[g,q] for g,c in ts) for q in complete]
  report['exploratory_contrasts'][name]={'all100_bounds':contrast_bounds(table,ids,ts),'conditional_complete_cases_bootstrap':analyze.bootstrap(values)}
 clean=[q for q in ids if q not in flagged];report['sensitivity_without_quality_flags']['n']=len(clean)
 report['sensitivity_without_quality_flags']['groups']={g:{'correct':sum(table[g,q] for q in clean),'n':len(clean)} for g in groups}
 for a,b in [('A','B'),('A_prime','B_prime')]:report['sensitivity_without_quality_flags'][a+'__'+b]=paired(table,clean,a,b)
 invalid=[]
 for reviewpath in sorted((out/'failed-attempts').glob('*/*/*/review.json')):
  rv=json.loads(reviewpath.read_text());ledgerpath=reviewpath.parent/'audit/search.jsonl';ledger=load_jsonl(ledgerpath) if ledgerpath.exists() else []
  retry=bool(rv.get('retry_number'));billable=rv.get('billable_searches_in_invalid_attempt',sum(bool(r.get('billable')) for r in ledger)) if retry else 0
  invalid.append({'group':rv['group'],'question_id':rv['question_id'],'retry':retry,'reprocessed_without_new_call':bool(rv.get('reprocessing_without_model_call')),'billable_search_estimate':billable,'review':str(reviewpath.relative_to(out))})
 diagnostics=[]
 for f in sorted((out/'diagnostics').glob('*.json')):
  d=json.loads(f.read_text());diagnostics.append({'path':str(f.relative_to(out)),'billable_search_estimate':bool(d.get('billable_search_estimate') or d.get('nonempty_success'))})
 cost={'search_price_usd_from_frozen_config':cfg['search_price_usd'],'valid_search_fee_estimate_usd':sum(v['search_fee_estimate_usd'] for v in report['groups'].values()),'invalid_attempt_billable_searches':sum(v['billable_search_estimate'] for v in invalid),'invalid_attempt_search_fee_estimate_usd':sum(v['billable_search_estimate'] for v in invalid)*cfg['search_price_usd'],'diagnostic_billable_searches':sum(v['billable_search_estimate'] for v in diagnostics),'diagnostic_search_fee_estimate_usd':sum(v['billable_search_estimate'] for v in diagnostics)*cfg['search_price_usd'],'invalid_attempts':invalid,'diagnostics':diagnostics,'reported_answer_model_nominal_usd':sum(v['reported_model_nominal_usd'] for v in report['groups'].values()),'grade_nominal_usd':{}}
 for j in ['claude','deepseek']:
  grades=load_jsonl(out/'jsonl/grades'/(j+'.jsonl'));cost['grade_nominal_usd'][j]={'all1000':sum(r.get('reported_cost_usd') or 0 for r in grades),'new600':sum(r.get('reported_cost_usd') or 0 for r in grades if not r.get('reused_from'))}
 report['costs']=cost
 diffs=[]
 for a,b in [('A','B'),('A_prime','B_prime')]:
  for q in ids:
   av=table.get((a,q));bv=table.get((b,q))
   if av==bv:continue
   data={'a':a,'b':b,'question_id':q,'question':qs[q]['question'],'reference_answer':qs[q]['answer'],'quality_flagged':q in flagged,'a_correct':av,'b_correct':bv,'runs':{}}
   for g in [a,b]:
    r=runs[g,q];raw=out/r['raw'];events,_=parse_stream(raw.read_text());uses={}
    for e in events:
     for block in e.get('message',{}).get('content',[]) if isinstance(e.get('message',{}).get('content'),list) else []:
      if block.get('type')=='tool_use':uses[block['id']]=block
    data['runs'][g]={'answer':r['answer'],'queries':[v['input'].get('query') for v in uses.values()],'elapsed_seconds':r['elapsed_seconds'],'raw_path':str(raw),'audit_path':str(out/'audit'/g/q),'returned_utf8_bytes':next(x['returned_utf8_bytes'] for x in load_jsonl(out/'analysis/resource-runs.jsonl') if x['group']==g and x['question_id']==q)}
   diffs.append(data)
 write_text(out/'analysis/paired-cases.jsonl',''.join(dumps(x)+'\n' for x in diffs));write_json(out/'analysis/full-summary.json',report)
 lines=['# Search benchmark：正式作答与三位AI评分报告','','日期：'+report['generated_at'][:10]+'（北京时间）。600份搜索作答、400份复用baseline均完成；原双判2000条及独立盲审1000票已核验。多数票995份有结论、5份仍待核。本文给准确率范围，不给待核未决情况下的最终排名。','','## 术语与计量','','正确/错误：至少两张相同的二元AI票；待核：三票中没有两张相同correct/incorrect。准确率范围=[已判对/100, (已判对+待核)/100]，不是统计置信区间。个百分点用pp表示。P90使用nearest-rank，即100题中排序后的第90个耗时。KB=1000个UTF-8字节。原双判结果与第三票裁决分别保留，未填写human.jsonl。','','## 主要观察','','- 搜索与不搜索的差异明显；多数票口径下，六个搜索组相对同模型baseline提升约20–34个百分点，精确范围见下表。','- Sonnet搭配DeepSeek搜索的已判对数为97，搭配Claude搜索为91且1份待核，差值为5–6pp；方向值得关注，但配对检验尚不足以在5%阈值下确认稳定优势。','- Opus配Claude搜索99对、DeepSeek搜索97对，差2pp，配对检验也未形成明确差异。Flash与Pro配DeepSeek搜索分别95–98%与96%，不能据这批题断言高档更强。','- 同一Claude主模型下，DeepSeek搜索返回文本更多、主模型输入更多，但完整作答平均更快；Claude原生搜索另有CLI上报的Haiku用量。服务端未上报的内部处理不按零计算。','','## 多数票：每组100题','','| 组 | 模型与条件 | 正确 | 错误 | 待核 | 准确率范围 |','|---|---|---:|---:|---:|---:|']
 for g in groups:
  s=scores[g];lines.append(f'| {g} | {LABELS[g]} | {s["correct"]} | {s["incorrect"]} | {s["pending"]} | {bounds_string(s["accuracy_bounds"])}% |')
 lines+=['','## 相对同模型baseline的搜索提升','','原baseline文件不改；下表统一采用新增多数票口径，使两端评分规则一致。','','| 搜索组 | 对照 | 准确率提升范围（pp） | 同题平均增时（秒） | 同题增时中位数（秒） |','|---|---|---:|---:|---:|']
 for g,v in report['lifts'].items():lines.append(f'| {g} | {v["baseline"]} | {bounds_string(v["accuracy_lift_bounds"])} | {v["paired_mean_added_seconds"]:+.2f} | {v["paired_median_added_seconds"]:+.2f} |')
 lines+=['','## 两种搜索的配对比较','','p值为双侧精确McNemar；全100题的p范围枚举所有未决二元结果。已判定共同样本的p单列，不能把删去未决项后的结果冒称完整100题。','','| 比较（DeepSeek搜索减Claude搜索） | 全100题差值范围（pp） | 全100题p范围 | 已判定配对题数 | Claude独对 / DeepSeek独对 | 条件p |','|---|---:|---:|---:|---:|---:|']
 for key,v in report['comparisons'].items():
  p0,p1=v['p_exact_completion_range'];c=v['complete_pairs'];lines.append(f'| {key} | {bounds_string(v["difference_b_minus_a_bounds"])} | {p0:.4f}–{p1:.4f} | {v["complete_pairs_n"]} | {c["a_only"]} / {c["b_only"]} | {c["p_exact"]:.4f} |')
 lines+=['','## 实际作答耗时与搜索次数','','| 组 | 平均秒数 | 中位秒数 | P90秒数 | 每题平均实际搜索次数 |','|---|---:|---:|---:|---:|']
 for g,v in report['groups'].items():lines.append(f'| {g} | {v["mean_seconds"]:.2f} | {v["median_seconds"]:.2f} | {v["p90_seconds_nearest_rank"]:.2f} | {v["mean_search_calls"]:.2f} |')
 lines+=['','计时从启动claude进程到完整输出落盘，含启动、思考、搜索、生成及本地扫描和写盘开销，不含此前的凭据读取、排队和判分。这里统计最终入样本的成功作答；真实失败/重跑与诊断耗时另存原始审计，不混入单题分布。未记录首字延迟，不能计算可靠的首字速度。baseline含40份较早pilot复用，baseline与搜索又在不同时段运行，网络、缓存、并发及输出长度均会影响耗时；不是严格隔离条件下的纯模型tokens/sec。Flash搜索组平均比不搜索短，伴随平均输出从1399降至487个报告token，不能据此宣称搜索没有延迟。','','## 搜索返回的数据量','','返回量是成功tool_result中的模型可见文本，不含外层JSON包裹；每个调用ID只计一次。不等同HTTP网络流量，也不等同去重后的事实量。','','| 组 | 每题平均KB | 每次搜索平均KB | 每题平均字符数 | 实际搜索总次数 |','|---|---:|---:|---:|---:|']
 for g in BASE:
  v=resources['groups'][g];lines.append(f'| {g} | {v["mean_returned_utf8_bytes_per_question"]/1000:.2f} | {v["mean_returned_utf8_bytes_per_call"]/1000:.2f} | {v["mean_returned_characters_per_question"]:.0f} | {v["search_calls"]} |')
 lines+=['','Sonnet每题DeepSeek/Claude返回量比约5.98倍；Opus约5.69倍。DeepSeek工具固定请求10条并返回标题、URL、snippet、summary、日期；这与Claude原生工具的返回格式不同，所以字节数差异同时体现工具返回设计。','','## 主模型token用量（每题平均）','','Claude累计输入=未缓存输入+缓存读取+缓存写入，包含多轮重读；不是只处理搜索内容的token。DeepSeek Anthropic兼容接口缓存字段的合计含义未在本次核对的公开文档中明确，保留原字段、不推断总量。不同模型tokenizer不能直接等量比较。输出字段可能已含思考token，不再额外相加。','','| 组 | 报告input | 缓存读 | 缓存写 | Claude累计输入 | 报告输出 |','|---|---:|---:|---:|---:|---:|']
 for g in groups:
  v=resources['groups'][g];total='—' if v['mean_main_input_tokens'] is None else f'{v["mean_main_input_tokens"]:.0f}';lines.append(f'| {g} | {v["mean_main_reported_input_tokens"]:.0f} | {v["mean_main_cache_read_tokens"]:.0f} | {v["mean_main_cache_write_tokens"]:.0f} | {total} | {v["mean_main_output_tokens"]:.0f} |')
 lines+=['','Claude原生搜索的全部100题均额外上报Haiku：A每题平均输入21561、输出1190；A_prime输入22162、输出1248。它们与主模型分列，不能漏掉，也不据此断言已观测全部服务端成本。DeepSeek Search生成摘要的内部模型用量未上报，不能视为0。整题相对baseline的token差还含工具定义、调用、历史重读及推理策略变化，不能精确归因为只处理返回材料。口径来源：[Claude提示缓存](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)、[DeepSeek Anthropic兼容说明](https://api-docs.deepseek.com/guides/anthropic_api/)。','','## 原双判结果（保留原口径）','','| 组 | 一致判对 | 一致判错 | 待核 |','|---|---:|---:|---:|']
 for g,s in dual.items():lines.append(f'| {g} | {s["correct"]} | {s["incorrect"]} | {s["pending"]} |')
 lines+=['','双判原有8份待核；第三票解决3份，保留5份。原baseline中的4份待核及其不可变快照保持原样，见[baseline]('+str(ROOT/'baseline.md')+')。这里新增的多数票baseline为：Sonnet63/37/0、Flash65/34/1、Opus77/23/0、Pro67/33/0（正确/错误/待核），不覆盖旧表。','','## 仍待核的5份答案','','| 组 | 题目ID | 票数（Claude / DeepSeek / 独立AI） | 待核原因 |','|---|---|---|---|']
 for r in pending:
  m=mapping[r['id']];votes=' / '.join(r['judges'][j]['verdict'] for j in ['claude','deepseek','independent']);reason=r['judges']['independent']['reason'].replace('|','/');lines.append(f'| {m["group"]} | {m["question_id"]} | {votes} | {reason} |')
 lines+=['','## 题意质量与敏感性分析','','原baseline的frames-137与frames-598质量标记保留；第三位AI还标记其他口径问题。这些是独立质量标记，不能被多数票消除，也未据此改原题库或参考答案。合计'+str(len(flagged))+'道ID：'+', '.join(flagged)+'。除两道原有题已留来源复核外，新增质量意见仍需核实。','','以下是事后探索性敏感性分析：只在分析视图中同时排除上述'+str(len(flagged))+'题，仍保留完整100题主结果；不能将此当作重新挑选后的正式题库或主要排名。剩'+str(len(clean))+'题均有二元多数票。','','| 组 | 排除质量标记后正确 / 题数 |','|---|---:|']
 for g,v in report['sensitivity_without_quality_flags']['groups'].items():lines.append(f'| {g} | {v["correct"]} / {v["n"]} |')
 lines+=['','## 搜索提升差的探索性统计','','按题重抽样10000次。因为全100题仍有待核，完整题集只报识别范围；bootstrap只使用该对比涉及组均已判定的共同题目，区间是条件结果，不能当作完整100题的最终区间。未做多重比较校正。','','| 对比 | 全100题提升差范围（pp） | 条件样本n | 条件bootstrap估计与95%区间（pp） |','|---|---:|---:|---:|']
 for name,v in report['exploratory_contrasts'].items():
  b=v['conditional_complete_cases_bootstrap'];lines.append(f'| {name} | {bounds_string(v["all100_bounds"])} | {b["n"]} | {b["estimate"]*100:.1f} [{b["ci95"][0]*100:.1f}, {b["ci95"][1]*100:.1f}] |')
 lines+=['','## 来源前五命中','','URL按既定规则规范化后做精确匹配，不代表语义正确率，也不把最终引用当作搜索原始排名。','','| 搜索组 | 可观测题数 | 前五来源命中率 |','|---|---:|---:|']
 for g in BASE:
  v=report['groups'][g];hit='不可观测' if v['source_hit_at5'] is None else f'{v["source_hit_at5"]:.1%}';lines.append(f'| {g} | {v["source_hit_observable_n"]} | {hit} |')
 lines+=['','## 费用与运行故障口径','','按冻结配置每次非空成功DeepSeek Search估值$'+str(cfg['search_price_usd'])+'，不是重新查询的当前价或已核对账单。','','| 项目 | Search API估值（USD） |','|---|---:|',f'| 最终入样本成功搜索 | {cost["valid_search_fee_estimate_usd"]:.5f} |',f'| 真实失败/无效次中已成功或被本地拦截的非空返回 | {cost["invalid_attempt_search_fee_estimate_usd"]:.5f} |',f'| 两次独立诊断 | {cost["diagnostic_search_fee_estimate_usd"]:.5f} |',f'| 本次正式搜索相关合计 | {cost["valid_search_fee_estimate_usd"]+cost["invalid_attempt_search_fee_estimate_usd"]+cost["diagnostic_search_fee_estimate_usd"]:.5f} |','','上述不含pilot阶段搜索费、模型推理费或判分费。Search请求失败且账本无非空响应的收费无法从客户端确认，需对账；这里不假定实际扣款。Claude搜索未单列Search API收费，走既定订阅调用；不能把配置中的0解释成所有搜索基础设施免费。','','| 组 | CLI报告模型名义估值（USD，非实际扣款） |','|---|---:|']
 for g,v in report['groups'].items():lines.append(f'| {g} | {v["reported_model_nominal_usd"]:.4f} |')
 lines+=['','Claude的名义估值不是Max订阅扣款或周额度；DeepSeek兼容CLI价格依据标记unknown，不能据此当真实API费用。原800条baseline双判复用，不发生新的相同判分调用。','','| 判分员 | 1000条名义估值 | 其中新增600条名义估值 |','|---|---:|---:|']
 for j,v in cost['grade_nominal_usd'].items():lines.append(f'| {j} | {v["all1000"]:.4f} | {v["new600"]:.4f} |')
 lines+=['','共有'+str(sum(r['retry'] for r in invalid))+'份真实无效作答按规则保留后各重跑一次；另1份参数拒绝漏记依据原输出修复审计、未重跑模型。记录均在failed-attempts/。两次早期通用搜索失败未能确认异常类型；后续包含SSL意外断连与凭据扫描网址误报。相关补丁只涉及审计/误报修复，旧源码及manifest散列链保存在validation/；没有修改题目、模型、提示词、最大五次实际搜索或Fetch禁用。实际预算拒绝次数合计'+str(sum(v['budget_denials'] for v in report['groups'].values()))+'，参数拒绝'+str(sum(v['argument_rejections'] for v in report['groups'].values()))+'；不把离线回归覆盖冒称正式运行发生过第六次调用。','','## 同题差异案例与复现材料','','完整同题对照包括DeepSeek搜索获胜、Claude搜索获胜及未决项目，见[配对案例](paired-cases.md)。案例只展示作答、查询、数据量和最终评分，不把答错自动归类为检索失败。Apollo质量口径与El Tomatal同名地点等质量标记随案例保留。','','可复现数字：[完整汇总](full-summary.json)、[资源汇总](resources.json)、[逐题资源](resource-runs.jsonl)、[多数票凭据](../grading/majority-receipt.json)、[规则授权](../grading/adjudication-policy.json)。报告与正式结果仍留tmp/archive，未提交、推送、公开或移动。5份待核使准确率仍是临时范围；机器判分完成不代表人工已经复核。']
 write_text(out/'analysis/report.md','\n'.join(lines)+'\n')
 case_lines=['# 同题搜索对照','','包含两种搜索评分不同或单方未决的全部同题案例，避免只挑一方获胜。以下评分均按本次参考答案和AI多数票；质量标记保留，尚未逐一作独立来源裁决。']
 for x in diffs:
  case_lines+=['','## '+x['a']+' / '+x['b']+'：'+x['question_id'],'','题目：'+x['question'],'','参考答案：'+x['reference_answer'],'','题意质量标记：'+('有（独立AI标记，仍需核实）' if x['quality_flagged'] else '未标记')]
  for g in [x['a'],x['b']]:
   v=x['runs'][g];verdict=x['a_correct'] if g==x['a'] else x['b_correct'];label='待核' if verdict is None else '正确' if verdict else '错误'
   case_lines+=['','### '+LABELS[g]+'：'+label,'','查询：'+'；'.join(v['queries']),'',f'耗时{v["elapsed_seconds"]:.3f}秒，可见返回{v["returned_utf8_bytes"]}字节。','','回答：','',v['answer'],'','[原始记录]('+v['raw_path']+')；[工具审计目录]('+v['audit_path']+')。']
 write_text(out/'analysis/paired-cases.md','\n'.join(case_lines)+'\n')
 write_json(out/'analysis/report-receipt.json',{'created_at':report['generated_at'],'tool_sha256':sha256(ROOT/'tools/report.py'),'manifest_sha256':sha256(out/'manifest.json'),'baseline_record_sha256':sha256(source/'baseline-record.json'),'majority_receipt_sha256':sha256(out/'grading/majority-receipt.json'),'resources_receipt_sha256':sha256(out/'analysis/resources-receipt.json'),'files':{n:sha256(out/'analysis'/n) for n in ['report.md','full-summary.json','paired-cases.md','paired-cases.jsonl']},'baseline_source_hashes_verified':True,'formal_grade_raws_verified':2000,'status':'complete_with_5_unresolved_review'})
 return report
if __name__=='__main__':
 try:
  report=build(ROOT/'tmp/archive',ROOT/'tmp/baseline');print(dumps({'report':str(ROOT/'tmp/archive/analysis/report.md'),'majority_pending':report['majority_pending'],'comparisons':report['comparisons'],'costs':{k:v for k,v in report['costs'].items() if k not in ['invalid_attempts','diagnostics','grade_nominal_usd']}}))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
