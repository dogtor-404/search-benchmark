#!/usr/bin/env python3
"""下载标准答案的证据页供人工核实。HTTP 200 和字面命中不等于事实核实。"""
import argparse,concurrent.futures,hashlib,html,json,re,time,urllib.request,urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from common import ROOT,load_jsonl,dumps,write_json
class Text(HTMLParser):
 def __init__(self):super().__init__();self.out=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.out.append(d)
def fetch(url):
 cache=ROOT/'tmp/sources';cache.mkdir(parents=True,exist_ok=True);name=hashlib.sha256(url.encode()).hexdigest();p=cache/(name+'.json')
 if p.exists():return json.loads(p.read_text())
 result={'url':url,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'unavailable','text':''}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ResearchSourceCheck/1.0)'})
  with urllib.request.urlopen(req,timeout=18) as r:
   data=r.read(3000000);charset=r.headers.get_content_charset() or 'utf-8';raw=data.decode(charset,errors='replace');result.update(final_url=r.url,http_status=r.status)
  parser=Text();parser.feed(raw);text=re.sub(r'\s+',' ',html.unescape(' '.join(parser.out)));result.update(status='fetched',text=text,content_sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:result['error']=type(e).__name__
 write_json(p,result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=6);a=p.parse_args()
 qs=load_jsonl(ROOT/'questions/questions.jsonl');urls=list(dict.fromkeys(u for q in qs for u in q['source_urls']))
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:pages=dict(zip(urls,ex.map(fetch,urls)))
 evidence=[]
 for q in qs:
  candidates=[q['answer'].strip('". '),*q['aliases']];matches=[]
  for url in q['source_urls']:
   page=pages[url];text=page['text'];pos=-1;match=None
   for answer in candidates:
    if answer and (pos:=text.casefold().find(answer.casefold()))>=0:match=answer;break
   matches.append({'url':url,'status':page['status'],'content_sha256':page.get('content_sha256'),'matched':match,'excerpt':text[max(0,pos-180):pos+len(match or '')+240] if match else ''})
  evidence.append({'id':q['id'],'sources':matches})
 write_json(ROOT/'tmp/source-check.json',evidence)
 print(dumps({'questions':len(qs),'sources':len(urls),'fetched':sum(x['status']=='fetched' for x in pages.values()),'literal_answer_match':sum(any(s['matched'] for s in q['sources']) for q in evidence)}))
