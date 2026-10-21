#!/usr/bin/env python3
"""固定版本、固定种子抽题；不调用模型或搜索 API。"""
import ast,csv,hashlib,json,random,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEED=20261020
SOURCES=[('simpleqa_verified','google/simpleqa-verified','0dc97e0d28d8233463e005cdc4475cc2a13ba2dc','simpleqa_verified.csv',25),('chinese_simpleqa','OpenStellarTeam/Chinese-SimpleQA','336305fc5f1da8184e3f70aff4473408418383a0','chinese_simpleqa.jsonl',25),('frames','google/frames-benchmark','58d9fb6330f3ab1316d1eca12e5e8ef23dcc22ef','test.tsv',15)]
def clean_url(u):
 u=u.strip().rstrip('.')
 while u.endswith(')') and u.count(')')>u.count('('):u=u[:-1]
 return u
def build():
 cache=ROOT/'tmp/datasets';cache.mkdir(parents=True,exist_ok=True)
 decisions={r['id']:r for r in load(ROOT/'questions/review.jsonl')}
 selected=[]; provenance=[]
 for name,repo,rev,file,count in SOURCES:
  path=cache/file;url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/{file}'
  if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=60).read())
  rows=load(path) if file.endswith('jsonl') else list(csv.DictReader(path.open(),delimiter='\t' if file.endswith('tsv') else ','))
  order=list(range(len(rows)));random.Random(f'{SEED}:{name}').shuffle(order)
  accepted=0
  for rank,i in enumerate(order):
   r=rows[i]
   if name=='simpleqa_verified':
    if r['multi_step'].lower()=='true' or r['requires_reasoning'].lower()=='true':continue
    q,a=r['problem'],r['answer'];urls=[clean_url(u) for u in re.split(r',(?=https?://)',r['urls'])];sid=r['original_index']
   elif name=='chinese_simpleqa':q,a,urls,sid=r['question'],r['answer'],[u.replace('\\n','').replace('\\u003d','=') for u in r['urls']],r['id']
   else:
    urls=ast.literal_eval(r['wiki_links'])
    if len(set(urls)) not in (2,3):continue
    q,a,sid=r['Prompt'].strip(),r['Answer'],r['']
   qid=f'{name}-{sid}';review=decisions.get(qid,{})
   if review.get('status')=='rejected':continue
   urls=urls+review.get('extra_source_urls',[])
   selected.append(dict(id=qid,set=name,lang='zh' if name=='chinese_simpleqa' else 'en',question=q,answer=a,aliases=review.get('aliases',[]),source_urls=list(dict.fromkeys(u for u in urls if isinstance(u,str) and re.match(r'^https?://[^/]+',u))),provenance={'repository':repo,'revision':rev,'source_id':sid,'source_row':i,'shuffle_rank':rank,'wiki_count':len(set(urls)) if name=='frames' else None},review={'status':review.get('status','pending'),'note':review.get('note','待复核来源及答案有效性'),'checked_at':review.get('checked_at'),'method':'source_readback'}));accepted+=1
   if accepted==count:break
  provenance.append(dict(set=name,repository=repo,revision=rev,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),total_rows=len(rows),selected=accepted))
 for file in ['custom.jsonl','news.jsonl']:selected+=load(ROOT/'questions'/file)
 (ROOT/'questions/questions.jsonl').write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in selected))
 (ROOT/'questions/sources.json').write_text(json.dumps({'seed':SEED,'datasets':provenance},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'questions':len(selected),'sets':{s:sum(q['set']==s for q in selected) for s in sorted({q['set'] for q in selected})}},ensure_ascii=False))
def load(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
if __name__=='__main__':build()
