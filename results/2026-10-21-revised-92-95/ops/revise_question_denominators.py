"""用户授权：统一移出题目/参考疑问及待核题，只展示判决语义分歧。"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import collections,datetime,hashlib,importlib.util,json,os,shutil,sys
ROOT=Path(str(Path(__file__).resolve().parents[3]))
OLD=ROOT/'results/2026-10-21-response-review/no-search-double-blind'
SCORE=ROOT/'results/2026-10-21-unified-score'
OUT=ROOT/'results/2026-10-21-revised-92-95'
REL='results/2026-10-21-revised-92-95'
GROUPS=['0','A','B','D0','D2','0_prime','A_prime','B_prime','D0_prime','D2_prime']
BASE=['0','D0','0_prime','D0_prime']
LABELS={'explicit_abstention':'明确弃答','confident_incorrect_assertion':'错误的确定断言','incomplete_answer':'不完整回答','hedged_or_withdrawn_guess':'试猜或撤回'}
DEC={'submitted_answer':'仍提交答案','no_answer':'没有作答','withdrawn_answer':'最终撤回'}
CONTEXT={'msqa-JA-05':'问“把家电当宠物一样疼爱的人叫什么”。这里只判断模型有没有最终交出一个称呼，不需要你懂日语。','msqa-KO-50':'问一个韩语网络用语是什么意思。这里只判断模型最终有没有采用自己的解释。','msqa-ES-58':'问某项学院禁令扩大到所有改宗者的确切年份。','msqa-ID-48':'问采蜜仪式中Ubo这个东西做什么用。','msqa-ID-53':'问一句印尼谚语的比喻意思。','msqa-ES-51':'问三座堡垒的火炮总数。此题因题目来源疑问已统一移出分母。','msqa-RU-95':'问一种特定文本类型叫什么，回答却主要解释“文本”这个普通概念。','msqa-ES-56':'问某制度最初在西班牙哪里建立。此题已统一剔除，无需判断地理史实。','msqa-RU-31':'问9月30日某种民间聚会的名称。此题已统一剔除，无需核验风俗。','msqa-ID-63':'问某族群通常把猪养在哪里。','msqa-ID-72':'问Bimbang Bebalai究竟是什么仪式、属于哪个族群。','msqa-TH-51':'问泰国一种菱形织物花纹的名称。','msqa-TH-85':'问一种泰国壁画形象最早出现于何时。此题已统一剔除。','msqa-JA-86':'根据某位僧人的经历，问他叫什么。','msqa-ES-37':'问一个巴西宗教术语在内部语境的含义。此题已统一剔除。','msqa-RU-08':'问某种俄罗斯黏土动物哨子的象征意义。'}
TRANSLATIONS={'msqa-RU-31':'准确说我不知道，也无法说出专属于9月30日的名称。一般秋季聚会有几个叫法，但不能确认所问习俗对应其中任何一个。','msqa-JA-86':'不知道。我想到曾在笠置山修行的贞庆，但他所属寺院与题干经历不符，应该是另一个人；没有能确定回答的姓名。','msqa-ES-56':'虽说没有唯一地点和确切日期，回答仍明确称制度起源于卡斯蒂利亚，并把这一说法称为历史共识。'}
def rd(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wr(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def fmt(x,d=2):return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-d),rounding=ROUND_HALF_UP))
def esc(x):return str(x).replace('|','\\|').replace('\n',' ')
def load_helper():
 sys.path.insert(0,str(ROOT/'tools'));p=SCORE/'ops/report_unified_score.py';spec=importlib.util.spec_from_file_location('frozen_score_helper',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 helper=load_helper();original=jl(SCORE/'score-records.jsonl');classes=jl(OLD/'resolved.jsonl');oldsummary=rd(OLD/'summary.json')
 flags={rd_:set(v) for rd_,v in oldsummary['all_reference_flags'].items()}
 pending={rd_:{r['question_id'] for r in original if r['round']==rd_ and r['original_correct'] is None} for rd_ in flags}
 for rd_ in flags:flags[rd_]|=pending[rd_]
 assert {k:len(v) for k,v in flags.items()}=={'first':8,'second':25}
 OUT.mkdir(exist_ok=True)
 # 单独保存当时的主文档，不覆盖既有原始评分或旧版本结果。
 for name in ['README.md','report.md','report-first-round.md','report-multilingual.md']:
  p=OUT/'previous-documents'/name
  if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
 sources={str(p.relative_to(ROOT)):sha(p) for p in [SCORE/'score-records.jsonl',SCORE/'summary.json',SCORE/'protocol.json',SCORE/'resolution-receipt.json',OLD/'summary.json',OLD/'resolved.jsonl',OLD/'resolution-receipt.json',ROOT/'results/2026-10-20-revised-96/policy.json']}
 policy={'adopted_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'authorization':'给我看分歧内容吧题目的我也看不懂，直接从分母删掉。主要给我看判决的分歧就好了','selection_rule':'截至本次处理，完整四类复核summary中全部all_reference_flags题号，并集两轮所有原待核题号。按题号在同轮十组统一剔除，包含原答对、答错、弃答与待核；不只剔除某模型的某份答案。','retrospective':True,'apply_to_all_groups':True,'original_grades_modified':False,'source_questions_deleted':False,'previous_primary_denominators':{'first':96,'second':120},'new_primary_denominators':{'first':92,'second':95},'excluded_question_ids':{k:sorted(v) for k,v in flags.items()},'reference_flag_question_ids':oldsummary['all_reference_flags'],'original_pending_question_ids':{k:sorted(v) for k,v in pending.items()},'source_files_sha256':sources}
 if (OUT/'policy.json').exists():
  existing=rd(OUT/'policy.json');assert existing['excluded_question_ids']==policy['excluded_question_ids'];policy=existing
 else:wr(OUT/'policy.json',policy)
 kept=[r for r in original if r['question_id'] not in flags[r['round']]];removed=[r for r in original if r['question_id'] in flags[r['round']]]
 assert len(kept)==1870 and len(removed)==330 and not any(r['original_correct'] is None for r in kept)
 kept_classes=[r for r in classes if r['question_id'] not in flags[r['round']]]
 for name,rows in [('score-records.jsonl',kept),('excluded-records.jsonl',removed),('classification-records.jsonl',kept_classes)]:
  (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
 summary={'created_at':policy['adopted_at'],'complete':True,'original_answers':2200,'retained_answers':1870,'excluded_answers':330,'retrospective':True,'same_question_ids_for_all_groups':True,'rule':'正确+5，错误且仍提交-3，不答或最终撤回0；第二次起每次搜索-1，对所有结果生效，无零分下限。','original_grades_modified':False,'policy_sha256':sha(OUT/'policy.json'),'cohorts':{}}
 for rd_,n in [('first',92),('second',95)]:
  rs=[r for r in kept if r['round']==rd_];cs=[r for r in kept_classes if r['round']==rd_]
  c={'questions_per_group':n,'question_ids':sorted({r['question_id'] for r in rs}),'excluded_question_ids':sorted(flags[rd_]),'groups':{},'comparisons':helper.comparisons(rs),'classification_groups':{},'confident_error_comparisons':{}}
  for g in GROUPS:
   gr=[r for r in rs if r['group']==g];assert len(gr)==n and all(r['score_lower']==r['score_upper'] for r in gr)
   c['groups'][g]={'name':helper.NAMES[g],**helper.stats(gr),'original_correct':sum(r['original_correct'] is True for r in gr),'original_incorrect':sum(r['original_correct'] is False for r in gr),'original_pending':0,'correct_percent':100*sum(r['original_correct'] is True for r in gr)/n}
  for g in BASE:
   gr=[r for r in cs if r['group']==g];counts={k:sum(r['category']==k for r in gr) for k in LABELS};assert len(gr)==c['groups'][g]['original_incorrect']
   c['classification_groups'][g]={'model':helper.NAMES[g],'all_questions':n,'original_incorrect':len(gr),'category_counts':counts,'confident_incorrect_percent_all_questions':100*counts['confident_incorrect_assertion']/n}
  lookup={(r['group'],r['question_id']):r for r in cs}
  for tier,a,b in [('mid','0','D0'),('high','0_prime','D0_prime')]:
   ids=c['question_ids'];va=[int((a,q) in lookup and lookup[a,q]['category']=='confident_incorrect_assertion') for q in ids];vb=[int((b,q) in lookup and lookup[b,q]['category']=='confident_incorrect_assertion') for q in ids]
   c['confident_error_comparisons'][tier]={'claude_group':a,'deepseek_group':b,'n':n,'claude_count':sum(va),'deepseek_count':sum(vb),'difference_percent_deepseek_minus_claude':100*(sum(vb)-sum(va))/n,'mcnemar':helper.analyze.mcnemar(va,vb),'paired_bootstrap':helper.analyze.bootstrap([y-x for x,y in zip(va,vb)],seed=20261021)}
  if rd_=='second':c['languages']={lang:{g:helper.stats([r for r in rs if r['lang']==lang and r['group']==g]) for g in GROUPS} for lang in sorted({r['lang'] for r in rs})}
  summary['cohorts'][rd_]=c
 wr(OUT/'summary.json',summary)
 build_disagreements(flags,kept,helper)
 (OUT/'report.md').write_text(render_report(summary,helper))
 write_documents(summary,helper)
 (OUT/'ops').mkdir(exist_ok=True);shutil.copy2(Path(__file__),OUT/'ops/revise_question_denominators.py')
 wr(OUT/'receipt.json',{'created_at':policy['adopted_at'],'source_files_sha256':sources,'retained':1870,'excluded':330,'original_pending_remaining':0,'files':{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='receipt.json'},'documents_sha256':{n:sha(ROOT/n) for n in ['README.md','report.md','report-first-round.md','report-multilingual.md','日志.md']}})
 print(json.dumps({'n':{'first':92,'second':95},'retained':len(kept),'excluded':len(removed),'score_means':{rd_:{g:round(v['mean_lower'],4) for g,v in c['groups'].items()} for rd_,c in summary['cohorts'].items()},'disagreements':rd(OUT/'disagreements.json')['counts']},ensure_ascii=False))

def build_disagreements(flags,kept,helper):
 lookup={(r['round'],r['group'],r['question_id']):r for r in jl(SCORE/'score-records.jsonl')};rows=[]
 for folder,kind,field in [(SCORE,'作答或撤回','decision'),(OLD,'四类分类','category')]:
  a={r['id']:r for r in jl(folder/'votes/reviewer-a.jsonl')};b={r['id']:r for r in jl(folder/'votes/reviewer-b.jsonl')};c={r['id']:r for r in jl(folder/'votes/adjudicator.jsonl')}
  for r in jl(folder/'resolved.jsonl'):
   if r['resolution']!='third_independent_adjudication':continue
   score=lookup[r['round'],r['group'],r['question_id']];impact=(kind=='作答或撤回' and ((a[r['id']][field]=='submitted_answer')!=(b[r['id']][field]=='submitted_answer')))
   rows.append({'kind':kind,'id':r['id'],'round':r['round'],'group':r['group'],'question_id':r['question_id'],'included':r['question_id'] not in flags[r['round']],'context_zh':CONTEXT[r['question_id']],'answer_original':r['candidate_answer'],'evidence_translation_zh':TRANSLATIONS.get(r['question_id']),'a':a[r['id']],'b':b[r['id']],'third':c[r['id']],'field':field,'affects_base_points':impact,'base_points':score['base_lower'],'search_penalty':score['search_penalty'],'current_final_points':score['score_lower'],'source_resolved':str((folder/'resolved.jsonl').relative_to(ROOT))})
 priority=[r for r in rows if r['included'] and r['affects_base_points']];priority.sort(key=lambda r:0 if r['question_id']=='msqa-JA-05' else 1)
 assert len(rows)==20 and len(priority)==2
 counts={'all_judgment_disagreements':20,'four_category_disagreements':13,'commitment_disagreements':7,'unique_answers':len({(r['round'],r['group'],r['question_id']) for r in rows}),'included_judgments':sum(r['included'] for r in rows),'excluded_judgments':sum(not r['included'] for r in rows),'included_commitment_disagreements_affecting_points':2}
 for i,r in enumerate(priority,1):r['human_review_number']=i
 wr(OUT/'disagreements.json',{'counts':counts,'priority':priority,'all':rows,'note':'保留原A/B/第三位裁决，不把人工尚未决定的内容擅自改判。页面不标模型，方便先看措辞边界；完整映射在本地JSON供审计。'})
 lines=['# 判决分歧：先看会改变分数的两份','','题目和参考答案的疑问已按题号在同轮十组统一剔除：第一轮92题，小语种95题；原始题库和答案仍保留。这里不用核验外语事实，只看回答最后有没有交出可采纳的答案。','','保留20次分歧判断（对应17份不同回答）：原四类13次、新作答状态7次，其中6次所属题已剔除。当前保留题中，作答状态分歧只有下面2份涉及作答分−3还是0。其他分歧主要影响分类名称，不改变现行作答分。下面“当前裁决”仍是第三位AI的结果，未冒充人工确认。','']
 for i,r in enumerate(priority,1):
  lines += [f'## {i}. '+('列出近似称呼，算作答还是没答？' if i==1 else '先给解释线索，最后说“不知道”，算撤回吗？'),'',r['context_zh'],'','回答全文：','','> '+r['answer_original'].replace('\n','\n> '),'',f'**A：{DEC[r["a"]["decision"]]}**。'+r['a']['rationale'],'',f'**B：{DEC[r["b"]["decision"]]}**。'+r['b']['rationale'],'',f'**第三位：{DEC[r["third"]["decision"]]}**。'+r['third']['rationale'],'',f'**当前作答分：{r["base_points"]}；搜索扣分：{r["search_penalty"]}；最终：{r["current_final_points"]}。** 如果人工采用另一票，作答分在−3与0之间改变。本页未自动改票。','']
 lines+=['## 其余5份“作答/撤回”分歧','','这5份A/B都是“不答”和“撤回”之分，作答分一律0；题目已剔除的两份只保留审计。','','| 中文场景 | A | B | 第三位 | 当前题目是否保留 | 作答分 |','|---|---|---|---|---|---:|']
 for r in rows:
  if r['kind']!='作答或撤回' or r in priority:continue
  lines.append('| '+esc(r['context_zh'])+' | '+DEC[r['a']['decision']]+' | '+DEC[r['b']['decision']]+' | '+DEC[r['third']['decision']]+' | '+('保留' if r['included'] else '已剔除')+' | 0 |')
 lines+=['','## 原13份四类分类分歧','','“不完整”与“确定答错”在新计分下仍按最终提交状态及原对错计分；“弃答”与“试猜/撤回”也不能直接推导分数，具体是否撤回已在统一计分中另审。这里只展示当时三位原票，不擅自合并或改写原标签。','','| 中文场景 | A | B | 第三位 | 当前题目是否保留 | 当前作答分 |','|---|---|---|---|---|---:|']
 for r in rows:
  if r['kind']!='四类分类':continue
  lines.append('| '+esc(r['context_zh'])+' | '+LABELS[r['a']['category']]+' | '+LABELS[r['b']['category']]+' | '+LABELS[r['third']['category']]+' | '+('保留' if r['included'] else '已剔除')+f' | {r["base_points"]} |')
 lines+=['','## 全部分歧的回答及三票理由','','外语回答附中文大意；原文与逐字证据完整保留，中文大意仅供理解，不替代原文。','']
 for i,r in enumerate(rows,1):
  labels=DEC if r['field']=='decision' else LABELS
  lines+=['<details>',f'<summary>{i}．{r["kind"]}：{r["context_zh"]}（'+('保留' if r['included'] else '题目已剔除')+'）</summary>','']
  if r['evidence_translation_zh']:lines+=['中文大意：'+r['evidence_translation_zh'],'']
  lines+=['候选原文：','','> '+r['answer_original'].replace('\n','\n> '),'']
  for k,title in [('a','A'),('b','B'),('third','第三位')]:lines += [f'**{title}：{labels[r[k][r["field"]]]}**。'+r[k]['rationale'],'','证据：'+r[k]['evidence_quote'],'']
  lines+=['</details>','']
 lines+=['[完整结构化原票与映射](disagreements.json) · [当前剔除规则](policy.json) · [剔除后成绩](report.md)。','']
 (OUT/'disagreements.md').write_text('\n'.join(lines))

def score_table(summary,helper,rounds=('first','second')):
 if len(rounds)==2:
  lines=['| 模型与工具 | 第一轮92题总分 | 第一轮每题均分 | 小语种95题总分 | 小语种每题均分 |','|---|---:|---:|---:|---:|']
  for g in GROUPS:
   a=summary['cohorts']['first']['groups'][g];b=summary['cohorts']['second']['groups'][g];lines.append(f'| {helper.NAMES[g]} | {a["total_lower"]} | {fmt(a["mean_lower"])} | {b["total_lower"]} | {fmt(b["mean_lower"])} |')
 else:
  c=summary['cohorts'][rounds[0]];lines=['| 模型与工具 | 原正确/题数 | 正确率 | 提交错答 | 不答 | 撤回 | 搜索扣分 | 新总分 | 每题均分 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for g in GROUPS:
   r=c['groups'][g];z=r['outcome_counts'];lines.append(f'| {helper.NAMES[g]} | {r["original_correct"]}/{r["n"]} | {fmt(r["correct_percent"])}% | {z["incorrect_submitted"]} | {z["no_answer"]} | {z["withdrawn_answer"]} | {r["search_penalty_total"]} | {r["total_lower"]} | {fmt(r["mean_lower"])} |')
 return '\n'.join(lines)

def class_table(summary,helper,rounds=('first','second')):
 lines=['| 轮次 | 模型（不搜索） | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 原判错合计 | 确定错误断言/全部题 |','|---|---|---:|---:|---:|---:|---:|---:|']
 for rd_ in rounds:
  for g in BASE:
   r=summary['cohorts'][rd_]['classification_groups'][g];z=r['category_counts'];lines.append('| '+('第一轮92题' if rd_=='first' else '第二轮95题')+' | '+helper.NAMES[g]+' | '+' | '.join(str(z[k]) for k in LABELS)+f' | {r["original_incorrect"]} | {fmt(r["confident_incorrect_percent_all_questions"])}% |')
 return '\n'.join(lines)

def render_report(summary,helper,rounds=('first','second')):
 lines=['# 剔除题目争议后的统一计分','','用户确认将题目本身无法核验的项目移出分母。固定采用本次处理时已存在的全部题意/参考疑问标记，并集原待核题号；同轮十组统一剔除，原答对、答错及弃答一同移出，没有按模型分别选题。第一轮原100题移出8题，保留92题；小语种原120题移出25题，保留95题。实际2200份运行记录均保留，当前计分1870份，330份不计分。','','这是观察结果后追加的筛题规则，不能包装成事前验证；各组在本轮使用同一题集，但剩余题可能有难度和语言构成偏差。原所有待核都已移出当前分母，因此当前得分没有待核区间。','','## 当前得分','','规则：正确+5；错误且仍提交−3；不答或最终撤回0；第二次起每次搜索−1，对所有结果生效，不设0分下限。旧成绩及所有原票保留，不重跑模型、不新增模型调用。','',score_table(summary,helper,rounds),'','## 原正确率与分数构成','']
 for rd_ in rounds:lines+=['### '+('第一轮：92题' if rd_=='first' else '小语种第二轮：95题'),'',score_table(summary,helper,(rd_,)),'']
 lines+=['## 不搜索组四类计数','','沿用原402份四类双盲裁决，仅按同一排除名单过滤；各行四类之和等于当前保留题中的原判错数。列顺序已按类别名称明确固定，避免主文档此前的展示顺序错误。','',class_table(summary,helper,rounds),'','## 同题均分差','','差值和区间使用双方同一批保留题；配对bootstrap共10000次，固定种子20261021。连续分数不用McNemar检验，以下为事后探索性结果，不作未经多重校正的确认性胜负声明。','','| 轮次 | 差值方向 | 配对n | 每题均分差 | 95%配对bootstrap区间 |','|---|---|---:|---:|---|']
 for rd_ in rounds:
  for key in ['sonnet_search','opus_search','mid_no_search','high_no_search','mid_deepseek_search_models','high_deepseek_search_models']:
   r=summary['cohorts'][rd_]['comparisons'][key];b=r['known_pair_bootstrap'];ci=b['ci95'];lines.append('| '+('第一轮92题' if rd_=='first' else '第二轮95题')+' | '+r['direction']+f' | {r["known_pairs"]} | {fmt(b["estimate"])} | [{fmt(ci[0])}, {fmt(ci[1])}] |')
 if 'second' in rounds:
  c=summary['cohorts']['second'];lines+=['','## 小语种各语言剩余题数与均分','','删题后每种语言的题数不同，各组在同一语言仍使用同一题集。总均分按全部95题加权，不能取六个语言均分的简单平均。语言细分样本较小，不直接作语言能力排名。','','| 语言 | 每组题数 | '+' | '.join(helper.NAMES[g] for g in GROUPS)+' |','|---|---:|'+'---:|'*len(GROUPS)]
  for lang,gs in c['languages'].items():lines.append('| '+lang+f' | {gs["0"]["n"]} | '+' | '.join(fmt(gs[g]['mean_lower']) for g in GROUPS)+' |')
 lines+=['','## 剔除清单、判决分歧与原件','','[全部剔除规则和题号](policy.json) · [判分员分歧的中文对照](disagreements.md) · [1870份计分记录](score-records.jsonl) · [330份移出记录](excluded-records.jsonl) · [完整统计](summary.json)。','','原100题/120题的四类复核、328份提交状态复核以及旧96题/120题统一分数均保留在上一级结果目录中。原题库、原始回答、对错裁决和审计凭据没有删除；已发生的运行时间与费用不能因删题而减少。新分母仅用于当前结果分析。','','原模型收到项目中文回复指令、不同搜索返回格式与可见资料量、两轮题集和原正确性评分方式不同，仍限制跨模型及跨轮解释。本次仅处理既有疑问，不代表剩余题已由母语人工全量验收。','']
 return '\n'.join(lines)

def write_documents(summary,helper):
 # 报告正文以新的统一分母为准，旧完整文档已在本次previous-documents封存。
 for name,rounds in [('report.md',('first','second')),('report-first-round.md',('first',)),('report-multilingual.md',('second',))]:
  text=render_report(summary,helper,rounds)
  for file in ['policy.json','disagreements.md','score-records.jsonl','excluded-records.jsonl','summary.json']:text=text.replace(']('+file+')',']('+REL+'/'+file+')')
  text+='\n[删题前的完整报告存档]('+REL+'/previous-documents/'+name+')。\n';(ROOT/name).write_text(text)
 p=ROOT/'README.md';t=p.read_text();ls=t.splitlines();ls[2]='最新状态（2026-10-21）：按用户确认，题意/参考疑问及原待核题已在同轮十组统一移出分母。第一轮保留92题，小语种保留95题，当前计分1870份、无待核；原2200份答案及全部原票保留。[两轮当前报告](report.md) · [第一轮92题](report-first-round.md) · [小语种95题](report-multilingual.md) · [判决分歧中文对照]('+REL+'/disagreements.md)。';t='\n'.join(ls)+'\n'
 t=t.replace('第一轮当前主表采用已有的96题统一排除口径，原100题视图另保留；小语种第二轮仍为120题','第一轮当前主表保留92题；小语种第二轮保留95题；原100/120题及上一版96/120题视图另保留')
 t=t.replace('历史补注（2026-10-21）：旧规则曾将第二轮398份判错中的112份列为弃答；当前四类互斥计数以[402份完整双盲复核](results/2026-10-21-response-review/no-search-double-blind/report.md)为准，不沿用旧112作为新类别下界。msqa-RU-04日期来源冲突仍待核；原正确性成绩不变，以下另按当前统一方案计分。','当前四类计数与统一分数均按92/95题过滤。旧112份弃答清单、原402份双盲分类和96/120题版分数保留为历史版本；所有题目来源疑问已统一移出当前分母，未重判原正确性。')
 t=t.replace('[统一计分结果与逐题依据](results/2026-10-21-unified-score/report.md)。','[当前统一计分与逐题依据]('+REL+'/report.md) · [删题清单]('+REL+'/policy.json)。')
 start='<!-- unified-score-results:start -->';end='<!-- unified-score-results:end -->';a=t.index(start);b=t.index(end,a)+len(end)
 block='## 当前统一计分结果\n\n第一轮92题、小语种95题，同轮十组使用完全相同题号。所有原待核已移出当前分母，以下均为确定分数；筛题和计分均为事后调整。\n\n'+score_table(summary,helper)+'\n\n[当前完整报告]('+REL+'/report.md) · [判决分歧中文对照]('+REL+'/disagreements.md) · [统一剔除规则]('+REL+'/policy.json)。\n'
 t=t[:a]+start+'\n'+block+end+t[b:]
 start='<!-- response-review-402:start -->';end='<!-- response-review-402:end -->';a=t.index(start);b=t.index(end,a)+len(end)
 block='## 当前不搜索组四类计数\n\n沿用已完成的两位独立Codex agent及第三位裁决的原402份分类，只按当前固定排除名单过滤；不把四类标签直接等同于新分数。\n\n'+class_table(summary,helper)+'\n\n[原402份完整双盲复核](results/2026-10-21-response-review/no-search-double-blind/report.md) · [当前分类数据]('+REL+'/classification-records.jsonl) · [13份类别分歧和7份作答状态分歧]('+REL+'/disagreements.md)。此前主文档四类表列顺序不符，已修正；原结构化计数及判分未变。\n'
 t=t[:a]+start+'\n'+block+end+t[b:]
 t=t.replace('## 第一轮正确率与旧100分制（保留）','## 历史：第一轮96题与旧100分制（保留）',1).replace('## 第二轮正确率与旧100分制（保留）','## 历史：第二轮120题与旧100分制（保留）',1)
 (ROOT/'README.md').write_text(t)
 p=ROOT/'tools/README.md';t=p.read_text();heading='## 当前分母与判决分歧（2026-10-21更新）'
 if heading not in t:t+='\n\n'+heading+'\n\n用户确认将全部已标记题意/参考疑问及原待核题在同轮十组统一剔除：第一轮92题、小语种95题。当前结果在`results/2026-10-21-revised-92-95/`，同目录ops保存本次复算工具；旧`revise_first_round.py`和统一分数工具保留历史96/120题行为，不应误当当前分母。原始记录未删除，详情见根README和新policy.json。\n'
 p.write_text(t)
 p=ROOT/'日志.md';t=p.read_text();heading='## 2026-10-21：按用户要求统一移出题目疑问，展示判决分歧'
 if heading not in t:t+='\n\n'+heading+'\n\n用户明确不再人工核验外语题目，授权题目争议直接移出分母，重点看判决语义分歧。采用既有all_reference_flags与原待核题号的并集：第一轮8题（含之前已排除4题），第二轮25题（22参考/题意标记并集3个额外待核题号）。同轮十组一同移出原答对、答错、弃答与待核，当前92/95题、1870份，无待核；原2200份记录及所有原票保留。新增固定policy、保留/移出逐题清单、两轮新分数及配对bootstrap、过滤后的四类计数。\n\n20次判决分歧对应17份回答；6次所属题已剔除，保留的作答状态分歧中仅2份涉及-3与0，其余主要为不答/撤回或类别名称差异。新增中文对照，优先两份影响分数的全文、A/B理由和第三位结果，未代替用户作人工改判。\n\n检查发现上次主文档四类表用了JSON键排序后的值顺序，列标题仍按既定顺序，导致展示错列；本次固定显式类别顺序并更正主文档。原402份结构化计数、匿名三票及原详细复核报告始终正确、未改动。删题前主文档逐字封存于新结果目录previous-documents。\n'
 p.write_text(t)

if __name__=='__main__':main()
