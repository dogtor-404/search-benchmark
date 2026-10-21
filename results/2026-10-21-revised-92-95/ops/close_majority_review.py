import collections,datetime,hashlib,json,shutil
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[3]));OUT=ROOT/'results/2026-10-21-revised-92-95'
def rd(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
rows=[]
for rel,field in [('results/2026-10-21-response-review/no-search-double-blind','category'),('results/2026-10-21-unified-score','decision')]:
 p=ROOT/rel;votes={who:{r['id']:r for r in jl(p/'votes'/name)} for who,name in [('a','reviewer-a.jsonl'),('b','reviewer-b.jsonl'),('third','adjudicator.jsonl')]}
 for r in jl(p/'resolved.jsonl'):
  if r['resolution']!='third_independent_adjudication':continue
  vals=[votes[k][r['id']][field] for k in ['a','b','third']];count=collections.Counter(vals);label,n=count.most_common(1)[0];assert n==2 and label==r[field]
  rows.append({'id':r['id'],'field':field,'question_id':r['question_id'],'majority_label':label,'votes_for':2,'votes_against':1,'existing_result_unchanged':True})
assert len(rows)==20
closure={'confirmed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'authorization':'不是已经有2:1的票了嘛？我觉得就按照这个来就好了？','method':'采用已有两位独立票及分歧第三票的2:1多数意见结案，不再要求额外人工投票。只涉及本次分类及最终提交状态补评，不替换原正确性裁决。','closed_disagreements':20,'human_pending':0,'scores_changed':False,'results':rows}
if not (OUT/'judgment-closure.json').exists():wr(OUT/'judgment-closure.json',closure)
lookup={r['id']:r for r in rows};p=OUT/'disagreements.json';d=rd(p)
for r in d['all']+d['priority']:r.update(majority_label=lookup[r['id']]['majority_label'],majority_votes=2,minority_votes=1,status='closed_by_majority')
d['counts'].update(closed_by_majority=20,human_pending=0);d['note']='全部20次分歧已按已有三票的2:1多数意见结案；三票及原裁决保留，当前得分未变，无待人工判断事项。';wr(p,d)
p=OUT/'disagreements.md';t=p.read_text();t=t.replace('# 判决分歧：先看会改变分数的两份','# 判决分歧记录：全部按2∶1多数票结案',1).replace('下面“当前裁决”仍是第三位AI的结果，未冒充人工确认。','20次分歧最终全部形成2∶1；按用户确认采用多数意见，已全部结案，不再等待人工判断。下列两份保留用于说明分歧，当前得分不变。').replace('如果人工采用另一票，作答分在−3与0之间改变。本页未自动改票。','已按2∶1多数票结案。');p.write_text(t)
p=OUT/'summary.json';s=rd(p);s['judgment_resolution']={'status':'closed_by_2_of_3_majority','disagreements':20,'human_pending':0,'scores_changed':False,'closure_file':'judgment-closure.json'};wr(p,s)
note='本次回答分类与最终提交状态的20处分歧，已核验三票全部形成2∶1，并按用户确认采用多数意见结案；不再等待人工投票。此前分数已经采用相同结果，得分保持不变。'
for name in ['README.md','report.md','report-first-round.md','report-multilingual.md',str((OUT/'report.md').relative_to(ROOT))]:
 p=ROOT/name;t=p.read_text()
 if note not in t:
  anchor='## 当前统一计分规则与原因' if name=='README.md' else '## 当前得分'
  assert anchor in t,name;t=t.replace(anchor,anchor+'\n\n'+note,1)
 p.write_text(t)
p=ROOT/'日志.md';t=p.read_text();heading='## 2026-10-21：用户确认已有2∶1判决直接结案'
if heading not in t:t+='\n\n'+heading+'\n\n核对原13份四类分歧与7份最终提交状态分歧，第三票全部与前两票之一相同，共20次均已形成2∶1。按用户要求直接采用多数票，不再要求人工再判。家电称呼案例维持-3分，韩语用语最终撤回案例维持0分；所有得分、当前92/95题分母及原票不变。新增judgment-closure.json，分歧页及主文档明确全部已结案。\n'
p.write_text(t)
shutil.copy2(Path(__file__),OUT/'ops/close_majority_review.py')
p=OUT/'receipt.json';receipt=rd(p);receipt['judgment_majority_closure_sha256']=sha(OUT/'judgment-closure.json');receipt['files']={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='receipt.json'};receipt['documents_sha256']={n:sha(ROOT/n) for n in ['README.md','report.md','report-first-round.md','report-multilingual.md','tools/README.md','日志.md']};wr(p,receipt)
assert [(r['human_review_number'],r['current_final_points']) for r in d['priority']]==[(1,-3),(2,0)]
assert sha(OUT/'score-records.jsonl')==receipt['files']['score-records.jsonl']
print('20次分歧均按2:1结案；两例维持-3/0分，所有成绩不变，无待人工事项。')
