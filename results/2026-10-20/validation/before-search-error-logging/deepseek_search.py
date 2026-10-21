#!/usr/bin/env python3
"""零依赖 stdio MCP：只提供搜索，固定 10 条、无正文、每题最多五次。"""
import json,os,sys,time,urllib.request,urllib.error
from common import BenchError,check_secret,write_text,dumps
ENDPOINT='https://api.deepseek.com/v1/tools/search'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class Search:
 def __init__(self):self.calls=0
 def save(self,record,key):
  ledger=os.environ.get('BENCH_SEARCH_LOG')
  if ledger:
   from pathlib import Path
   p=Path(ledger);old=p.read_text() if p.exists() else ''
   write_text(p,old+dumps(record)+'\n',(key,))
 def denied(self,query,key):
  try:self.save({'call':None,'query':query,'status':'budget_exhausted','results':[],'billable':False,'elapsed_seconds':0},key)
  except Exception:return {'content':[{'type':'text','text':'搜索审计记录无法安全保存，本题无效。'}],'isError':True}
  return {'content':[{'type':'text','text':dumps({'error':{'code':'search_budget_exhausted','message':'本题已经达到五次搜索上限，请用已有信息作答。'}})}],'isError':True}
 def call(self,args):
  if set(args)!={'query'} or not isinstance(args.get('query'),str) or not args['query'].strip() or len(args['query'])>128:
   return {'content':[{'type':'text','text':'query 必须是 1–128 个字符的非空字符串。'}],'isError':True}
  key=os.environ.get('BENCH_DEEPSEEK_KEY')
  if not key:return {'content':[{'type':'text','text':'本题未提供钥匙串凭据。'}],'isError':True}
  if self.calls>=5:return self.denied(args['query'],key)
  ledger=os.environ.get('BENCH_SEARCH_LOG')
  if ledger:
   # Claude 重连 MCP 也共用本题的持久计数，不重置五次预算。
   from pathlib import Path
   from search_budget import decide
   try:
    budget=Path(ledger).with_name('mcp-count.txt');decision,_=decide({'tool_name':'WebSearch'},budget)
    if decision!='allow':return self.denied(args['query'],key)
    self.calls=int(budget.read_text())
   except Exception:return {'content':[{'type':'text','text':'搜索计数器不可用，本题停止。'}],'isError':True}
  else:self.calls+=1
  start=time.monotonic();query=args['query']
  record={'call':self.calls,'query':query,'status':'failed','results':[],'billable':False}
  try:
   req=urllib.request.Request(ENDPOINT,data=json.dumps({'query':query,'count':10,'need_content':False}).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
   with urllib.request.build_opener(NoRedirect).open(req,timeout=60) as response:data=json.load(response)
   if not isinstance(data.get('results'),list):raise BenchError('搜索响应缺少 results 数组。')
   results=[]
   for item in data['results']:
    if not isinstance(item,dict) or not all(isinstance(item.get(k),str) for k in ['title','url','snippet','summary']):raise BenchError('搜索响应字段不完整。')
    results.append({k:item.get(k) for k in ['title','url','snippet','summary','date']})
   check_secret(dumps(results),(key,));record.update(status='ok',results=results,billable=bool(results))
   result={'content':[{'type':'text','text':dumps({'results':results})}],'isError':False}
  except urllib.error.HTTPError as exc:
   record['http_status']=exc.code;result={'content':[{'type':'text','text':f'搜索请求失败，HTTP {exc.code}。本次计入五次上限。'}],'isError':True}
  except Exception:
   result={'content':[{'type':'text','text':'搜索失败或响应无效。本次计入五次上限。'}],'isError':True}
  record['elapsed_seconds']=round(time.monotonic()-start,4)
  try:self.save(record,key)
  except Exception:return {'content':[{'type':'text','text':'搜索审计记录无法安全保存，本题无效。'}],'isError':True}
  return result

def main():
 search=Search()
 for line in sys.stdin:
  try:
   req=json.loads(line);method=req.get('method');rid=req.get('id')
   if rid is None:continue
   if method=='initialize':result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'deepseek-search-benchmark','version':'1.0.0'}}
   elif method=='ping':result={}
   elif method=='tools/list':result={'tools':[{'name':'search','description':'搜索网页，每题最多五次；只返回搜索摘要，不抓取网页。','inputSchema':{'type':'object','properties':{'query':{'type':'string','minLength':1,'maxLength':128}},'required':['query'],'additionalProperties':False}}]}
   elif method=='tools/call' and req.get('params',{}).get('name')=='search':result=search.call(req['params'].get('arguments',{}))
   else:
    print(dumps({'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'未支持的方法'}}),flush=True);continue
   print(dumps({'jsonrpc':'2.0','id':rid,'result':result}),flush=True)
  except Exception:print(dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32603,'message':'请求无效'}}),flush=True)
if __name__=='__main__':main()
