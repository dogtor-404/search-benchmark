from decimal import Decimal, ROUND_HALF_UP
"""按已确认的+5/-3/0及额外搜索-1统一计分，保留原对错裁决。"""
import collections,datetime,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[3]));OUT=ROOT/'results/2026-10-21-unified-score'
sys.path.insert(0,str(ROOT/'tools'));import analyze
GROUPS=['0','A','B','D0','D2','0_prime','A_prime','B_prime','D0_prime','D2_prime']
NAMES={'0':'Sonnet 不搜索','A':'Sonnet 原生搜索','B':'Sonnet + DeepSeek 搜索','D0':'Flash 不搜索','D2':'Flash + DeepSeek 搜索','0_prime':'Opus 不搜索','A_prime':'Opus 原生搜索','B_prime':'Opus + DeepSeek 搜索','D0_prime':'Pro 不搜索','D2_prime':'Pro + DeepSeek 搜索'}
def rd(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def fmt(a,b,d=2):
 def f(x):return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-d),rounding=ROUND_HALF_UP))
 return f(a) if a==b else f(a)+'–'+f(b)
def stats(rows):
 count=collections.Counter(r['scoring_outcome'] for r in rows);n=len(rows);lo=sum(r['score_lower'] for r in rows);hi=sum(r['score_upper'] for r in rows)
 return {'n':n,'outcome_counts':{k:count[k] for k in ['correct','incorrect_submitted','no_answer','withdrawn_answer','pending_submitted']},'search_calls_total':sum(r['search_calls'] for r in rows),'search_penalty_total':sum(r['search_penalty'] for r in rows),'total_lower':lo,'total_upper':hi,'mean_lower':lo/n,'mean_upper':hi/n,'theoretical_max_total':5*n,'zero_point_answers_with_search_penalty':sum(r['scoring_outcome'] in ['no_answer','withdrawn_answer'] and r['search_penalty']>0 for r in rows)}
def comparisons(rows):
 by={(r['group'],r['question_id']):r for r in rows};ids=sorted({r['question_id'] for r in rows});result={}
 pairs=[('sonnet_search','A','B'),('opus_search','A_prime','B_prime'),('mid_no_search','D0','0'),('high_no_search','D0_prime','0_prime'),('mid_deepseek_search_models','D2','B'),('high_deepseek_search_models','D2_prime','B_prime')]+[('lift_'+g,base,g) for g,base in [('A','0'),('B','0'),('D2','D0'),('A_prime','0_prime'),('B_prime','0_prime'),('D2_prime','D0_prime')]]
 for key,a,b in pairs:
  known=[q for q in ids if by[a,q]['score_lower']==by[a,q]['score_upper'] and by[b,q]['score_lower']==by[b,q]['score_upper']]
  diff=[by[b,q]['score_lower']-by[a,q]['score_lower'] for q in known]
  result[key]={'a':a,'b':b,'direction':NAMES[b]+' 减 '+NAMES[a],'n_all_pairs':len(ids),'known_pairs':len(known),'mean_difference_lower':sum(by[b,q]['score_lower']-by[a,q]['score_upper'] for q in ids)/len(ids),'mean_difference_upper':sum(by[b,q]['score_upper']-by[a,q]['score_lower'] for q in ids)/len(ids),'known_pair_bootstrap':analyze.bootstrap(diff,seed=20261021),'note':'连续分数差采用按题配对bootstrap，10000次；只用双方得分均已确定的题。全题差上下界来自原待核，非置信区间。不使用McNemar给连续分数差检验。'}
 return result
def main():
 p=rd(OUT/'protocol.json');receipt=rd(OUT/'resolution-receipt.json');review=jl(OUT/'resolved.jsonl');assert len(review)==p['records']==328
 assert sha(OUT/'resolved.jsonl')==receipt['resolved_sha256'] and sha(OUT/'all-answer-inputs.jsonl')==p['all_answer_inputs_sha256']
 for rel,digest in p['source_files_sha256'].items():assert sha(ROOT/rel)==digest,rel
 decisions={r['id']:r for r in review};q={}
 for name in ['questions/questions.jsonl','questions/multilingual.jsonl']:
  q.update({r['id']:r for r in jl(ROOT/name)})
  manifest=rd(ROOT/('tmp/archive/manifest.json' if name.endswith('questions.jsonl') else 'results/2026-10-21-multilingual/manifest.json'));assert sha(ROOT/name)==manifest['question_sha256']
 rows=[]
 for meta in jl(OUT/'all-answer-inputs.jsonl'):
  r=dict(meta);v=decisions.get(r.get('review_id'));d=v['decision'] if v else r['decision'];assert d in ['submitted_answer','no_answer','withdrawn_answer'];correct=r['original_correct'];calls=r['search_calls'];assert isinstance(calls,int) and 0<=calls<=5
  if v:r.update(decision=d,decision_method=v['resolution'],decision_rationale=v['rationale'],decision_evidence_quote=v['evidence_quote'])
  if d=='no_answer':base=[0,0];outcome='no_answer'
  elif d=='withdrawn_answer':base=[0,0];outcome='withdrawn_answer'
  elif correct is True:base=[5,5];outcome='correct'
  elif correct is False:base=[-3,-3];outcome='incorrect_submitted'
  else:base=[-3,5];outcome='pending_submitted'
  penalty=max(calls-1,0);r.update(lang=q[r['question_id']]['lang'],scoring_outcome=outcome,base_lower=base[0],base_upper=base[1],search_penalty=penalty,score_lower=base[0]-penalty,score_upper=base[1]-penalty)
  assert -7<=r['score_lower']<=r['score_upper']<=5
  rows.append(r)
 assert len(rows)==len({(r['round'],r['group'],r['question_id']) for r in rows})==2200
 policy=rd(ROOT/'results/2026-10-20-revised-96/policy.json');excluded=set(policy['exclusions'])
 cohorts={'first_96':[r for r in rows if r['round']=='first' and r['question_id'] not in excluded],'first_original_100':[r for r in rows if r['round']=='first'],'second_120':[r for r in rows if r['round']=='second']}
 summary={'created_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'complete':True,'scoring_rule':p['base_points'],'search_penalty_rule':p['search_penalty'],'primary_views':['first_96','second_120'],'historical_view':'first_original_100','records_all':2200,'records_primary':2160,'original_correctness_grades_changed':False,'deepseek_judging_api_calls':0,'review':{'independent_self_review_revision_records':1,'superseded_adjudications_not_in_final_disagreements':1,'new_independent_review_records':328,'reviewers':2,'third_adjudications':receipt['adjudicated'],'agreement':328-receipt['disagreements'],'identity':'Codex agents，同一基础模型独立上下文；非人工或跨模型审核','reused_commitment_states':p['reused_decisions'],'scope':p['review_scope']},'cohorts':{}}
 for name,rs in cohorts.items():
  n=96 if name=='first_96' else 100 if name=='first_original_100' else 120
  assert len(rs)==10*n
  c={'questions_per_group':n,'answers':len(rs),'groups':{g:dict(name=NAMES[g],**stats([r for r in rs if r['group']==g])) for g in GROUPS},'comparisons':comparisons(rs)}
  for g in GROUPS:assert c['groups'][g]['n']==n
  if name=='second_120':
   c['languages']={lang:{g:stats([r for r in rs if r['lang']==lang and r['group']==g]) for g in GROUPS} for lang in sorted({r['lang'] for r in rs})}
   assert all(v['n']==20 for gs in c['languages'].values() for v in gs.values())
  summary['cohorts'][name]=c
 (OUT/'score-records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows));wr(OUT/'summary.json',summary)
 lines=['# 两轮统一计分：答对+5、答错−3、弃答/最终撤回0、额外搜索−1','','按用户2026年10月21日确认方案，第一轮与小语种第二轮的十组使用同一计分规则。沿用既有答案和原正确性裁决，没有重跑被测模型，没有调用DeepSeek判分API。第一轮主表采用项目现有统一剔除4题后的96题，原100题视图另列；第二轮仍是六语种各20题，共120题。','','## 规则','','[计分理由与用户确认的设计取舍](rules-and-rationale.md)：评估搜索辅助下的最终作答，关键词命中本身不获分；弃答与撤回未交付答案，错误回答会造成误导，额外搜索计入时间和资源成本。','','每题得分 = 作答分 − max（搜索次数−1，0）。作答分：正确+5；错误且仍提交答案−3；没有回答、明确不知道或给候选后最终撤回为0。搜索扣分对所有结果生效，不设0分下限；搜索3次时，答对+3，答错−5，弃答/撤回−2。','','“可能/不确定但仍提交”按原对错裁决计+5或−3，不能一律归0。部分回答只要确实提交了所求信息，也沿用原正确性。原待核且仍提交答案的作答分为[−3,+5]；若经盲判确认不答或撤回，作答分固定0，原uncertain标记仍保留。得分范围来自原待核，不是置信区间。','','当前平均分上限为每题5分；总分上限第一轮480、第二轮600，两个轮次题数不同，跨轮只可对照均分且不能归因于单一语言因素。旧100分制及“仅答对扣搜索分”表保留为历史指标，本表是当前统一计分。','','## 两轮主表','']
 for name,title in [('first_96','第一轮：同96题'),('second_120','小语种第二轮：同120题')]:
  c=summary['cohorts'][name];lines+=['### '+title,'','| 模型与工具 | +5正确 | −3已提交错误 | 0不答 | 0最终撤回 | 待核已提交 | 搜索扣分合计 | 总分 | 每题均分 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for g,r in c['groups'].items():
   z=r['outcome_counts'];lines.append('| '+r['name']+' | '+' | '.join(str(z[k]) for k in ['correct','incorrect_submitted','no_answer','withdrawn_answer','pending_submitted'])+f' | {r["search_penalty_total"]} | {fmt(r["total_lower"],r["total_upper"],0)} | {fmt(r["mean_lower"],r["mean_upper"])} |')
  lines.append('')
 lines+=['## 同题配对的均分差','','正值表示右列模型/工具得分更高。均分差上下界允许原待核落在可能范围；95%区间只用双方得分已确定的同题做配对bootstrap，二者分母可能不同，不相互替代。本指标为看完原结果后确定的事后综合分，不作事前确认性胜负检验。','','| 轮次 | 差值方向 | 全题均分差范围 | 确定配对n | 条件配对均差 | 条件配对95%区间 |','|---|---|---:|---:|---:|---|']
 for name in ['first_96','second_120']:
  for key in ['sonnet_search','opus_search','mid_no_search','high_no_search','mid_deepseek_search_models','high_deepseek_search_models']:
   r=summary['cohorts'][name]['comparisons'][key];b=r['known_pair_bootstrap'];ci=b['ci95'];lines.append('| '+('第一轮96题' if name=='first_96' else '第二轮120题')+' | '+r['direction']+f' | {fmt(r["mean_difference_lower"],r["mean_difference_upper"])} | {r["known_pairs"]} | {b["estimate"]:.2f} | [{ci[0]:.2f}, {ci[1]:.2f}] |')
 lines+=['','## 小语种逐语言均分','','各语言每组20题，仍使用上方完全相同规则。小样本语言细分为探索性展示。','','| 语言 | '+' | '.join(NAMES[g] for g in GROUPS)+' |','|---|'+'---:|'*len(GROUPS)]
 for lang,gs in summary['cohorts']['second_120']['languages'].items():lines.append('| '+lang+' | '+' | '.join(fmt(gs[g]['mean_lower'],gs[g]['mean_upper']) for g in GROUPS)+' |')
 lines+=['','## 第一轮原100题历史视图','','此表保留全部原100题，与用户指定的原127份不搜索错答复核对应；不是项目当前96题主表。','','| 模型与工具 | 总分范围 | 每题均分范围 |','|---|---:|---:|']
 for r in summary['cohorts']['first_original_100']['groups'].values():lines.append('| '+r['name']+f' | {fmt(r["total_lower"],r["total_upper"],0)} | {fmt(r["mean_lower"],r["mean_upper"])} |')
 lines+=['','## 判分范围与证据','',f'既有原正确1631份沿用原正确性判为提交；402份四类双盲中，145份明确弃答与96份确定断言沿用其提交状态。其余153份试猜/撤回、8份不完整、144份搜索组原判错，以及23份原待核，共328份重新匿名，另由两位独立Codex agent各逐条判断最终是否提交。两票一致{328-receipt["disagreements"]}份，{receipt["disagreements"]}处分歧全部由第三位独立裁决，裁决员看不到前票。三个agent是同一基础模型独立上下文，不是不同模型或人工母语审核。','','B在未读组别或前票的独立自检中修订过1条边界判断，修订前票、回执与当时已发生的额外第三票均保留在votes/superseded及原分批文件中；该条自检后两票一致，不计入最终7处分歧。','','该提交状态审核不是重新判断事实真伪；有疑问的参考答案仍按冻结原成绩计分，第一轮只执行已获用户确认的4题统一排除，未自行扩展删题。原始正确率、历史100分制、原待核及其来源凭据均未改。','', '[逐题得分与依据](score-records.jsonl) · [完整计数、各语言和配对数据](summary.json) · [新语义判断规则](rubric.md) · [328份判断与引文](resolved.jsonl) · [两票及裁决凭据](resolution-receipt.json) · [原402份四类复核](../2026-10-21-response-review/no-search-double-blind/report.md)。','']
 (OUT/'report.md').write_text('\n'.join(lines))
 wr(OUT/'report-receipt.json',{'created_at':summary['created_at'],'protocol_sha256':sha(OUT/'protocol.json'),'resolution_sha256':sha(OUT/'resolution-receipt.json'),'source_files_verified':len(p['source_files_sha256']),'tool_sha256':sha(Path(__file__)),'calculation_question_sha256':{n:sha(ROOT/n) for n in ['questions/questions.jsonl','questions/multilingual.jsonl']},'rules_and_rationale_sha256':sha(OUT/'rules-and-rationale.md'),'files':{x.name:sha(x) for x in [OUT/'report.md',OUT/'summary.json',OUT/'score-records.jsonl']}})
 print(json.dumps({'all_answers':2200,'primary_answers':2160,'new_blind_reviews':328,'primary':{name:{g:[r['mean_lower'],r['mean_upper']] for g,r in summary['cohorts'][name]['groups'].items()} for name in ['first_96','second_120']}},ensure_ascii=False))
 return summary
if __name__=='__main__':main()
