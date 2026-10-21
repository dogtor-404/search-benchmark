from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[3]));OUT=ROOT/'results/2026-10-21-unified-score';REL='results/2026-10-21-unified-score'
s=json.loads((OUT/'summary.json').read_text());groups=['0','A','B','D0','D2','0_prime','A_prime','B_prime','D0_prime','D2_prime']
def fmt(a,b,d=2):
 def f(x):return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-d),rounding=ROUND_HALF_UP))
 return f(a) if a==b else f(a)+'–'+f(b)
def section(view=None):
 lines=['## 当前统一计分结果','','答对+5，答错且仍提交−3，不答/最终撤回0；第二次起每次搜索−1，所有结果都扣、不设0分下限。沿用原对错，不重跑模型；第一轮统一96题、小语种第二轮120题，原100题另列。均分上限每题5，待核所致范围不是置信区间。','']
 if view:
  lines+=['| 模型与工具 | 总分 | 每题均分 | +5正确 | −3已提交错误 | 0不答 | 0最终撤回 | 待核已提交 | 搜索扣分 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
  for r in [s['cohorts'][view]['groups'][g] for g in groups]:
   c=r['outcome_counts'];lines.append('| '+r['name']+f' | {fmt(r["total_lower"],r["total_upper"],0)} | {fmt(r["mean_lower"],r["mean_upper"])} | '+' | '.join(str(c[k]) for k in ['correct','incorrect_submitted','no_answer','withdrawn_answer','pending_submitted'])+f' | {r["search_penalty_total"]} |')
 else:
  lines+=['| 模型与工具 | 第一轮96题总分 | 第一轮每题均分 | 小语种120题总分 | 小语种每题均分 |','|---|---:|---:|---:|---:|']
  for g in groups:
   a=s['cohorts']['first_96']['groups'][g];b=s['cohorts']['second_120']['groups'][g]
   lines.append('| '+a['name']+f' | {fmt(a["total_lower"],a["total_upper"],0)} | {fmt(a["mean_lower"],a["mean_upper"])} | {fmt(b["total_lower"],b["total_upper"],0)} | {fmt(b["mean_lower"],b["mean_upper"])} |')
 lines+=['',f'[完整规则与计分原因]({REL}/rules-and-rationale.md) · [两轮新成绩、逐语言与配对比较]({REL}/report.md) · [逐题得分依据]({REL}/score-records.jsonl) · [结构化统计]({REL}/summary.json)。','','旧100分制表保留为历史指标，不能与本表数值直接混用；本次新增提交/撤回语义审核不改变原正确性成绩或待核标记。','']
 return '\n'.join(lines)+'\n'
def insert(name,anchor,view=None):
 p=ROOT/name;t=p.read_text();start='<!-- unified-score-results:start -->';end='<!-- unified-score-results:end -->';body=start+'\n'+section(view)+end+'\n\n'
 if start in t:
  a=t.index(start);b=t.index(end,a)+len(end);t=t[:a]+body.rstrip('\n')+t[b:]
 else:assert anchor in t,(name,anchor);t=t.replace(anchor,body+anchor,1)
 p.write_text(t)
insert('README.md','## 第一轮中英文成绩')
insert('report.md','## 两轮成绩对照')
insert('report-first-round.md','## 各组成绩','first_96')
insert('report-multilingual.md','## 这轮测试回答了什么','second_120')
for name,replacements in {
 'README.md':[('## 第一轮中英文成绩','## 第一轮正确率与旧100分制（保留）'),('## 第二轮多语种成绩','## 第二轮正确率与旧100分制（保留）')],
 'report.md':[('## 两轮成绩对照','## 两轮正确率与旧100分制对照（保留）')],
 'report-first-round.md':[('## 各组成绩','## 各组正确率与旧100分制（保留）')]
}.items():
 p=ROOT/name;t=p.read_text()
 for a,b in replacements:t=t.replace(a,b,1)
 p.write_text(t)
# 第二轮旧表原本无节标题，显著注明其仍是原正确率/旧分数。
p=ROOT/'report-multilingual.md';t=p.read_text();first='\n\n';offset=t.index(first)
note='\n\n当前统一+5/−3/0及额外搜索−1的成绩见本页“当前统一计分结果”及[完整新报告]('+REL+'/report.md)。下方原始正确率与100分制表保留供回查，其分数不是当前统一计分。'
if note not in t:t=t[:offset]+note+t[offset:]
p.write_text(t)
# 补充当前完整计分入口，旧目录不替换任何历史文件。
p=ROOT/'results/2026-10-21-response-review/README.md';t=p.read_text();note='\n[当前统一+5/−3/0与额外搜索−1计分](../2026-10-21-unified-score/report.md)另存；为分清试猜与最终撤回，追加328份提交状态双盲审核，原402份四类分类不变。\n'
if note not in t:t+=note
p.write_text(t)
log=ROOT/'日志.md';t=log.read_text();heading='## 2026-10-21：按用户确认统一两轮计分与搜索成本'
if heading not in t:
 t+='\n\n'+heading+'\n\n用户要求答对+5、答错−3、不答/不知道及最终撤回0；确认从第二次搜索起每次扣1对答对、答错与弃答都生效，不设0分下限，并明确小语种第二轮同口径。README已写明原因：搜索是模型作答的次生能力，关键词命中但上下文不符不获奖励；弃答/撤回都未交付可采纳答案；错答会误导和伤害最终结果，故负分；额外搜索计入理解/检索效率、时间与资源成本，但次数本身不是逐题能力失败证明。\n\n保留原正确性裁决和已完成402份四类分类，追加328份提交状态独立双盲：153试猜/撤回、8不完整、144搜索组原判错、23原待核。原正确1631份沿用提交状态，原双盲145明确弃答和96确定断言复用。两位新agent各审328，分歧第三位独立裁决，未用DeepSeek判分API。同一基础模型独立上下文，不作跨模型或人工声明。判分员B一条独立自检修订的前票/回执与已发生的额外第三票保留superseded记录；最终采用独立自检后的两票及剩余分歧裁决。\n\n新增results/2026-10-21-unified-score，保存2200份逐题新分、第一轮96题/原100题/小语种120题视图、六语种各20题分数、按题配对连续bootstrap及来源散列凭据。两轮主文档与README均加入新总分/均分，旧100分制明确标历史；无原模型重跑、不扩展第一轮删题、不更改第二轮题集或原待核。\n'
 log.write_text(t)
print('unified scoring results added to README and both rounds; old metrics retained')
