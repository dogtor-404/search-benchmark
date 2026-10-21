"""只向项目主文档添加新的402份分类结果，保留96题主表与历史原件。"""
import json
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[4]));REL='results/2026-10-21-response-review/no-search-double-blind';OUT=ROOT/REL
s=json.loads((OUT/'summary.json').read_text());labels=list(s['category_labels']);groups=['0','D0','0_prime','D0_prime']
def table(rounds):
 lines=['| 轮次 | 模型（均不搜索） | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 原判错合计 | 确定错误断言/全部题 |','|---|---|---:|---:|---:|---:|---:|---:|']
 for rd in rounds:
  for g in groups:
   r=s['groups'][rd+'__'+g];lines.append('| '+('第一轮原100题' if rd=='first' else '第二轮120题')+' | '+r['model']+' | '+' | '.join(str(r['category_counts'][k]) for k in labels)+f' | {r["original_incorrect"]} | {r["confident_incorrect_percent_all_questions"]:.2f}% |')
 return '\n'.join(lines)
def section(rounds=['first','second'],detail=False):
 lines=['## 不搜索组错答的四类双盲复核（新增）','','按用户要求完成第一轮原100题中127份、第二轮120题中275份原判错的完整互斥分类，共402份。两位Codex agent使用独立上下文盲判；389份一致（96.77%），13份分歧由第三位独立裁决。判分员看不到组别、轮次或前票；本次DeepSeek判分API调用为0。三个agent使用同一基础模型，不是跨模型交叉复核。','',table(rounds),'','第一轮此表按用户指定的原100题保留，区别于项目当前96题主表；同一分类过滤到96题的明细也在完整复核报告中。四类之和分别为原判错127/275，原待核未计入确认分子。确定断言按冻结参考与输出措辞定义，含参考疑问项，不等于全部回答的严格幻觉率。','','同档比较：第一轮Sonnet/Flash为2/6、Opus/Pro为2/7，尚不足以判稳定输赢。第二轮分别为10/27、11/31，差14.17和16.67个百分点；共同原已判样本的配对McNemar检验，经四项Holm校正后p分别为0.00273、0.000352，支持本题集下Claude两档这类错误更少。两轮不合并成总体排名。','','选例核查另发现舰长、哈瓦那城墙、韩语近义谚语、泰国壁画及部队锅年代的参考疑问，均未改原成绩，也不作无争议幻觉例子。每组目标两例；第一轮Sonnet可用1例、Opus为0例，第二轮Opus可用1例，其余各2例，没有为凑数放宽规则。全部此类原文（含未展示的争议项）保留。','','旧72/112及96题过滤后的71份清单仍是历史补注，未采用本次四类互斥规则；其中部分回答会重新归入试猜/撤回或不完整，所以旧“至少”数不能继续作为本次明确弃答类别的下界。','',f'[完整复核与案例]({REL}/report.md) · [新的完整四类计数]({REL}/summary.json) · [逐题类别与证据]({REL}/resolved.jsonl) · [来源核查]({REL}/example-fact-checks.json)。']
 if detail:
  lines+=['','| 轮次与档位 | DeepSeek减Claude 个百分点 | 条件配对差95%区间 个百分点 | 四项Holm校正p |','|---|---:|---|---:|']
  for r in s['comparisons'].values():
   if r['round'] not in rounds:continue
   st=r['conditional_paired'];ci=st['difference_deepseek_minus_claude_bootstrap']['ci95'];lines.append(f'| {("第一轮原100题" if r["round"]=="first" else "第二轮120题")+(" 中档" if r["tier"]=="mid" else " 高档")} | {r["observed_percent_difference_deepseek_minus_claude"]:+.2f} | [{100*ci[0]:.2f}, {100*ci[1]:.2f}] | {st["p_holm_four_comparisons"]:.6f} |')
 return '\n'.join(lines)+'\n\n'
def put(path,body,anchor):
 p=ROOT/path;text=p.read_text();start='<!-- response-review-402:start -->';end='<!-- response-review-402:end -->';new=start+'\n'+body+end+'\n\n'
 if start in text:
  a=text.index(start);b=text.index(end,a)+len(end);text=text[:a]+new.rstrip('\n')+text[b:]
 else:assert anchor in text,path;text=text.replace(anchor,new+anchor,1)
 p.write_text(text)
put('README.md',section(),'## 第二轮的弃答与错误回答')
put('report.md',section(detail=True),'## 明确弃答与错误回答')
put('report-multilingual.md',section(['second'],True),'## 弃答与错误回答')
view=s['first_round_current_96_view'];r96=['## 第一轮96题对应的四类计数','','仅按既有4题排除规则过滤原100题的双盲分类，剩余四个不搜索组共120份判错；不新增删题、不改原票。','','| 模型 | 明确弃答 | 错误的确定断言 | 不完整回答 | 试猜或撤回 | 合计 | 确定错误断言/96 |','|---|---:|---:|---:|---:|---:|---:|']
for g in groups:
 r=view['groups'][g];r96.append('| '+r['model']+' | '+' | '.join(str(r['category_counts'][k]) for k in labels)+f' | {r["original_incorrect"]} | {r["confident_incorrect_percent_all_questions"]:.2f}% |')
r96+=['','以下原100题表仅作为用户指定的历史复核口径；其计数不能直接除以96。','',section(['first'],True)]
put('report-first-round.md','\n'.join(r96),'## 明确弃答与原有记录')
for name,heading in [('README.md','## 第二轮的弃答与错误回答'),('report.md','## 明确弃答与错误回答'),('report-multilingual.md','## 弃答与错误回答'),('report-first-round.md','## 明确弃答与原有记录')]:
 p=ROOT/name;t=p.read_text();notice='历史单人保守补注，保留原记录。新的四类互斥计数以上方双盲复核为准；下文旧“至少”数不作为新类别下界。'
 t=t.replace(heading,heading+'（历史补注）\n\n'+notice,1);p.write_text(t)
(ROOT/'results/2026-10-21-response-review/README.md').write_text('''# 回答类型复核索引

- **最新完整复核**：[两轮四个不搜索组402份原判错](no-search-double-blind/report.md)，包括四类计数、同档比较、独立双评与第三位裁决、完整候选原文及选例来源核查。机器可读总数在 [no-search-double-blind/summary.json](no-search-double-blind/summary.json)。
- **早期历史补注**：[第二轮398份错答中的保守弃答清单与5个案例](report.md)。本目录原有summary.json、receipt.json等仍保存该历史版本，不是新402份复核的计数；其规则和范围不同，旧弃答数字不作为新类别下界。

原答案与原正确性裁决均未修改。第一轮当前96题视图和原100题复核在新报告中分开列示。
''')
log=ROOT/'日志.md';t=log.read_text();heading='## 2026-10-21：完成两轮不搜索错答402份四类双盲复核'
if heading not in t:
 t+='\n\n'+heading+'\n\n用户明确要求原第一轮127份、第二轮275份原判错按四类互斥计数，试猜与撤回合并。重新随机匿名化，冻结规则及输入散列；两位独立上下文Codex agent各逐条判402份，389份一致、13份分歧全部由看不到前票的第三位独立裁决。未调用DeepSeek或其他收费判分API；不是人工母语审核或跨基础模型复核。共145明确弃答、96错误的确定断言、8不完整、153试猜/撤回；原成绩及原收据未改。\n\n结果在results/2026-10-21-response-review/no-search-double-blind，原日期目录的旧summary/receipt保持原样，新增README区分两版。按原100/120分母提供8组计数、同档配对检验/区间及四项Holm校正；另按项目当前4题统一排除规则过滤第一轮96题视图，主复核仍按用户指定原100题。\n\n选例来源核查新单列5道参考疑问，不改原计数；第一轮Sonnet无争议可用1例、Opus0例，第二轮Opus1例，其余各2例，完整96份原文含争议项全部可回查。旧72/112清单不适用本次互斥规则，不能继续作为新明确弃答类别的下界。\n'
 log.write_text(t)
print('updated README/report/both detailed reports/index/log; original receipts untouched')
