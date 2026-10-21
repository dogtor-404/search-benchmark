#!/usr/bin/env python3
"""离线汇总模型可见搜索返回量和CLI报告用量；不重跑模型。"""
import collections,json,statistics,sys
from common import ROOT,BenchError,load_jsonl,parse_stream,sha256,dumps,write_text,write_json

def text_size(content):
 if isinstance(content,str):parts=[content]
 elif isinstance(content,list) and all(isinstance(x,dict) and x.get('type')=='text' and isinstance(x.get('text'),str) for x in content):parts=[x['text'] for x in content]
 else:raise BenchError('搜索返回含未支持的非文本内容，不能静默漏计。')
 return {'characters':sum(len(x) for x in parts),'utf8_bytes':sum(len(x.encode('utf-8')) for x in parts)}

def returns(events):
 uses={};results={}
 for e in events:
  for b in e.get('message',{}).get('content',[]) if isinstance(e.get('message',{}).get('content'),list) else []:
   if b.get('type')=='tool_use':
    if b.get('id') in uses and uses[b['id']]!=b:raise BenchError('同一调用ID内容冲突。')
    uses[b['id']]=b
   elif b.get('type')=='tool_result':
    oid=b.get('tool_use_id')
    if oid in results and results[oid]!=b:raise BenchError('同一返回ID内容冲突。')
    results[oid]=b
 rows=[]
 for oid,b in results.items():
  if oid not in uses or uses[oid]['name'] not in ('WebSearch','mcp__deepseek-search__search'):raise BenchError('搜索返回缺少匹配调用。')
  if b.get('is_error'):continue
  rows.append(dict(tool_use_id=oid,**text_size(b.get('content'))))
 return rows

def token_fields(usage,anthropic=False):
 names=['inputTokens','cacheReadInputTokens','cacheCreationInputTokens','outputTokens','thinkingTokens']
 if any(not isinstance(usage.get(k),int) or usage[k]<0 for k in names):raise BenchError('模型用量字段缺失或无效，不当作零。')
 r={k:usage[k] for k in names}
 r['total_input_tokens']=sum(usage[k] for k in names[:3]) if anthropic else None
 return r

def run(out):
 manifest=json.loads((out/'manifest.json').read_text());cfg=manifest['config'];rows=[];sources={}
 for g,group in cfg['groups'].items():
  for qid in manifest['question_ids']:
   mp=out/'runs'/g/(qid+'.json');r=json.loads(mp.read_text())
   if r.get('status')!='ok':raise BenchError('作答尚未全部成功。')
   raw=out/r['raw'];events,final=parse_stream(raw.read_text(),allowed_budget_denial_ids={x.get('tool_use_id') for x in r.get('budget_denials',[])})
   if final['result']!=r['answer'] or final.get('modelUsage')!=r.get('model_usage') or final.get('usage')!=r.get('usage'):raise BenchError('作答元数据与原始输出不同。')
   calls=returns(events)
   if len(calls)!=r['search_calls']:raise BenchError('有效搜索返回数量与审计不同。')
   models=final.get('modelUsage',{});main=group['model']
   if main not in models:raise BenchError('未找到主模型用量。')
   fields={model:token_fields(v,anthropic=model.startswith('claude-')) for model,v in models.items()}
   rows.append({'group':g,'question_id':qid,'search_calls':len(calls),'returned_characters':sum(c['characters'] for c in calls),'returned_utf8_bytes':sum(c['utf8_bytes'] for c in calls),'returns':calls,'main_model':main,'main_model_usage':fields[main],'auxiliary_model_usage':{k:v for k,v in fields.items() if k!=main},'elapsed_seconds':r['elapsed_seconds']})
   for p in [mp,raw]:sources[str(p.relative_to(out))]=sha256(p)
 groups={}
 for g in cfg['groups']:
  items=[r for r in rows if r['group']==g];n=len(items);calls=sum(r['search_calls'] for r in items)
  models={};names=set(k for r in items for k in r['auxiliary_model_usage'])
  for name in sorted(names):
   values=[r['auxiliary_model_usage'][name] for r in items if name in r['auxiliary_model_usage']]
   models[name]={'questions_reported':len(values),'mean_input_tokens_per_question':sum(v['total_input_tokens'] for v in values)/n if all(v['total_input_tokens'] is not None for v in values) else None,'mean_output_tokens_per_question':sum(v['outputTokens'] for v in values)/n}
  total=[r['main_model_usage']['total_input_tokens'] for r in items]
  groups[g]={'n':n,'search_calls':calls,'mean_returned_utf8_bytes_per_question':statistics.mean(r['returned_utf8_bytes'] for r in items),'median_returned_utf8_bytes_per_question':statistics.median(r['returned_utf8_bytes'] for r in items),'mean_returned_utf8_bytes_per_call':sum(r['returned_utf8_bytes'] for r in items)/calls if calls else None,'mean_returned_characters_per_question':statistics.mean(r['returned_characters'] for r in items),'mean_main_input_tokens':statistics.mean(total) if all(x is not None for x in total) else None,'mean_main_reported_input_tokens':statistics.mean(r['main_model_usage']['inputTokens'] for r in items),'mean_main_cache_read_tokens':statistics.mean(r['main_model_usage']['cacheReadInputTokens'] for r in items),'mean_main_cache_write_tokens':statistics.mean(r['main_model_usage']['cacheCreationInputTokens'] for r in items),'mean_main_output_tokens':statistics.mean(r['main_model_usage']['outputTokens'] for r in items),'mean_main_thinking_tokens_reported':statistics.mean(r['main_model_usage']['thinkingTokens'] for r in items),'auxiliary_models':models}
 write_text(out/'analysis/resource-runs.jsonl',''.join(dumps(r)+'\n' for r in rows))
 write_json(out/'analysis/resources.json',{'groups':groups,'notes':['返回量统计原始tool_result中成功搜索的文本字符数和UTF-8字节数，不含外层JSON封装，不代表HTTP网络流量；每个tool_use_id只计一次。','token取每题最终result.modelUsage，不累加重复的assistant流事件。主模型与辅助模型分列，辅助模型仅为CLI可观测用量，服务端未上报的内部token无法补知。','Claude累计输入=未缓存输入+缓存读取+缓存写入，包含多轮重复上下文；不是去重文本大小，不是纯搜索内容token，也不是实际付费或Max额度。','不同模型tokenizer不可直接等量比较。DeepSeek Anthropic兼容接口的缓存字段相加口径未在公开文档中明确，本报告保留原字段，不推算合计。','搜索相对baseline的用量差含工具定义、调用、返回、历史重读及推理策略差异，不可归因为仅处理搜索文本。'],'claude_usage_source':'https://platform.claude.com/docs/en/build-with-claude/prompt-caching','deepseek_compatibility_source':'https://api-docs.deepseek.com/guides/anthropic_api/'})
 write_json(out/'analysis/resources-receipt.json',{'tool_sha256':sha256(ROOT/'tools/resources.py'),'manifest_sha256':sha256(out/'manifest.json'),'records':len(rows),'file_sha256':sources,'resource_runs_sha256':sha256(out/'analysis/resource-runs.jsonl'),'resources_sha256':sha256(out/'analysis/resources.json')})
 return groups
if __name__=='__main__':
 try:print(dumps(run(ROOT/'tmp/archive')))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
