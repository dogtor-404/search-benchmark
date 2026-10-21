#!/usr/bin/env python3
"""从固定上游版本在本地重建第一轮题库，不调用被测模型。"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def restore(cache=None):
    sources=json.loads((ROOT/'questions/sources.json').read_text())['datasets']
    source=next(s for s in sources if s['set']=='chinese_simpleqa')
    cache=Path(cache) if cache else ROOT/'tmp/datasets/chinese_simpleqa.jsonl'
    if not cache.exists():
        data=urllib.request.urlopen(source['url'],timeout=60).read()
        if hashlib.sha256(data).hexdigest()!=source['sha256']: raise ValueError('上游文件 SHA256 不符')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
    data=cache.read_bytes()
    if hashlib.sha256(data).hexdigest()!=source['sha256']: raise ValueError('上游文件 SHA256 不符')
    upstream={str(r['id']):r for r in map(json.loads,data.decode().splitlines()) if r}
    rows=[json.loads(l) for l in (ROOT/'questions/first-round-template.jsonl').read_text().splitlines() if l.strip()]
    for row in rows:
        if row.pop('withheld',False):
            item=upstream[str(row['provenance']['source_id'])]
            row['question']=item['question'];row['answer']=item['answer']
    target=ROOT/'questions/questions.jsonl'
    content=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
    if target.exists() and target.read_text()!=content: raise ValueError('已有题库不同，拒绝覆盖')
    target.write_text(content)
    print(json.dumps({'questions':len(rows),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'local_only':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache');a=p.parse_args();restore(a.cache)
