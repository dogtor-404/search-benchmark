"""按逐请求usage去重汇总两轮正式测试与主agent/评分agent用量。"""
import collections,datetime,hashlib,json
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[3]))
SESSIONS=Path(__import__('os').environ.get('BENCH_SESSION_DIR', str(Path(__file__).resolve().parents[3])+'/tmp/private-sessions'))
OUT=ROOT/'results/2026-10-21-token-usage'
CUTOFF='2026-10-21T02:29:40.981Z'
ROOT_IDS={'codex-session-02':'第一轮主对话','codex-session-15':'第二轮及后续复核主对话'}
FIELDS=['input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens','total_tokens']
def rd(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sum_usage(rows):
 c=collections.Counter()
 for r in rows:
  for k in FIELDS:c[k]+=r.get(k,0) or 0
 return {k:c[k] for k in FIELDS}
def main():
 catalog=[]
 for day in ['20','21']:
  for p in (SESSIONS/day).glob('*.jsonl'):
   try:
    with p.open() as f:m=json.loads(f.readline()).get('payload',{})
   except (ValueError,OSError):continue
   cwd=m.get('cwd','')
   if 'PROJECT_ID_REMOVED' not in cwd and 'search-benchmark' not in cwd:continue
   src=m.get('source');sub=src.get('subagent',{}) if isinstance(src,dict) else {};catalog.append({'path':p,'id':m.get('id'),'parent':m.get('parent_thread_id'),'agent_path':sub.get('thread_spawn',{}).get('agent_path'),'is_background_helper':sub.get('other')=='guardian'})
 related=set(ROOT_IDS)
 while True:
  new=related|{m['id'] for m in catalog if m['parent'] in related}
  if new==related:break
  related=new
 per=[];global_seen={};excluded=[]
 for m in catalog:
  is_core=m['id'] in related and not m['is_background_helper'];records=[];duplicates=0;inherited=0
  for line in m['path'].open():
   try:r=json.loads(line)
   except ValueError:continue
   if r.get('timestamp','')>CUTOFF or r.get('type')!='token_usage_record':continue
   p=r['payload']
   if p.get('thread_id')!=m['id']:inherited+=1;continue
   u={k:p['usage'].get(k,0) or 0 for k in FIELDS};ident=p.get('response_id')
   assert ident and u['input_tokens']+u['output_tokens']==u['total_tokens']
   assert u['cached_input_tokens']+u['cache_write_input_tokens']<=u['input_tokens'] and u['reasoning_output_tokens']<=u['output_tokens']
   key=(is_core,ident)
   if key in global_seen:
    assert global_seen[key]==u;duplicates+=1;continue
   global_seen[key]=u;records.append({'timestamp':r['timestamp'],'response_id':ident,'usage':u})
  v={'thread_id':m['id'],'role':ROOT_IDS.get(m['id'],m['agent_path'] or '其他同项目对话'),'session_file':str(m['path']),'usage':sum_usage([r['usage'] for r in records]),'unique_requests':len(records),'duplicate_usage_records_skipped':duplicates,'inherited_usage_records_skipped':inherited,'usage_projection_sha256':digest(records)}
  if is_core:per.append(v)
  else:excluded.append(dict(v,excluded_reason='后台辅助审查用量，不纳入主对话/评分agent口径' if m['is_background_helper'] else '非这两条主任务及其评分子任务；同项目其他对话不纳入主口径'))
 main_threads=[r for r in per if r['thread_id'] in ROOT_IDS];workers=[r for r in per if r['thread_id'] not in ROOT_IDS];assert len(main_threads)==2 and len(workers)==11
 codex=sum_usage([r['usage'] for r in per]);codex_main=sum_usage([r['usage'] for r in main_threads]);codex_worker=sum_usage([r['usage'] for r in workers]);extra=sum_usage([r['usage'] for r in excluded]);formal=[];source_hashes={}
 for rd_,folder in [('first','tmp/archive'),('second','results/2026-10-21-multilingual')]:
  p=ROOT/folder/'analysis/resource-runs.jsonl';rows=jl(p);counts=collections.Counter()
  for r in rows:
   u=r['main_model_usage']
   if r['main_model'].startswith('claude-'):counts['claude_main_tokens']+=(u.get('total_input_tokens',0) or 0)+(u.get('outputTokens',0) or 0)
   else:
    counts['deepseek_reported_input_plus_output']+=(u.get('inputTokens',0) or 0)+(u.get('outputTokens',0) or 0)
    counts['deepseek_cache_possible_extra']+=(u.get('cacheReadInputTokens',0) or 0)+(u.get('cacheCreationInputTokens',0) or 0)
   for au in r['auxiliary_model_usage'].values():counts['reported_auxiliary_models_tokens']+=(au.get('total_input_tokens',0) or 0)+(au.get('outputTokens',0) or 0)
  low=counts['claude_main_tokens']+counts['deepseek_reported_input_plus_output']+counts['reported_auxiliary_models_tokens'];formal.append({'round':rd_,'answers':len(rows),**counts,'tokens_lower':low,'tokens_upper':low+counts['deepseek_cache_possible_extra']});source_hashes[str(p.relative_to(ROOT))]=sha(p)
 grading=[]
 for provider in ['claude','deepseek']:
  c=collections.Counter();proof=[]
  for p in sorted((ROOT/'tmp/archive/grading/raw'/provider).glob('*.jsonl')):
   result=[r for r in jl(p) if r.get('type')=='result'];assert len(result)==1;c['calls']+=1
   for u in result[0]['modelUsage'].values():
    c['reported_input_plus_output']+=(u.get('inputTokens',0) or 0)+(u.get('outputTokens',0) or 0)
    c['cache_read_and_write']+=(u.get('cacheReadInputTokens',0) or 0)+(u.get('cacheCreationInputTokens',0) or 0)
   proof.append({'file':str(p.relative_to(ROOT)),'sha256':sha(p)})
  low=c['reported_input_plus_output']+(c['cache_read_and_write'] if provider=='claude' else 0);high=low+(c['cache_read_and_write'] if provider!='claude' else 0)
  grading.append({'provider':provider,**c,'tokens_lower':low,'tokens_upper':high,'raw_files_projection_sha256':digest(proof)})
 formal_low=sum(x['tokens_lower'] for x in formal);formal_high=sum(x['tokens_upper'] for x in formal);grade_low=sum(x['tokens_lower'] for x in grading);grade_high=sum(x['tokens_upper'] for x in grading)
 low=formal_low+grade_low+codex['total_tokens'];high=formal_high+grade_high+codex['total_tokens']
 summary={'snapshot_at_utc':CUTOFF,'snapshot_at_beijing':'2026-10-21 10:29:40','scope':'两轮2200份正式答案及搜索辅助模型、第一轮2000次API判分、两轮主对话和其11个评分/复核agent。Codex用量只纳入本次用户要求统计之前的逐请求记录。','main_estimate_tokens_lower':low,'main_estimate_tokens_upper':high,'video_recommended':'三亿多 token','formal_answer_tokens_range':[formal_low,formal_high],'first_round_api_judging_tokens_range':[grade_low,grade_high],'codex':{'sessions':13,'main_threads':2,'worker_agents':11,'main_usage':codex_main,'worker_usage':codex_worker,'total_usage':codex,'cached_fraction_of_codex_input':codex['cached_input_tokens']/codex['input_tokens'],'per_session':per},'same_project_other_sessions_excluded_from_main_scope':{'usage':extra,'per_session':excluded,'expanded_estimate_tokens_range_including_these':[low+extra['total_tokens'],high+extra['total_tokens']]},'formal_rounds':formal,'first_round_api_grading':grading,'method':['按token_usage_record.payload.usage逐请求读取，以response_id去重，仅取thread_id匹配当前会话的记录；不把累计token_count快照相加。','总量=input_tokens+output_tokens；cached_input_tokens属于输入子集，reasoning_output_tokens属于输出子集，均不额外再加。','Claude原生搜索另外上报的辅助模型用量已计入；DeepSeek兼容接口input/cache映射未核实，以是否额外计算缓存构成小范围估值差。','这是累计token处理量，含缓存及多轮上下文重复读取，不是生成的新文本量或等价全价计费量。','删题不撤销已发生用量。试跑、失败重试和搜索服务内部未上报用量未全部并入，所以不是完整账户账单。'],'official_usage_reference':'https://developers.openai.com/api/docs/guides/prompt-caching','source_files_sha256':source_hashes}
 OUT.mkdir(exist_ok=True);wr(OUT/'summary.json',summary)
 lines=['# 两轮测试与Codex自身用量估算','','统计截点：北京时间2026年10月21日10:29:40，用户要求将Codex自身用量计入之前。','','**主口径合计约'+f'{low/1e8:.2f}亿～{high/1e8:.2f}亿 token。**','','| 部分 | 累计token约数 |','|---|---:|',f'| 两轮2200份正式作答，含已上报搜索辅助模型 | {formal_low/1e6:.1f}～{formal_high/1e6:.1f}百万 |',f'| 第一轮2000次API判分 | {grade_low/1e6:.1f}百万 |',f'| 两轮Codex主对话：执行、开发、分析、整理等 | {codex_main["total_tokens"]/1e6:.1f}百万 |',f'| 11个Codex评分/复核agent | {codex_worker["total_tokens"]/1e6:.1f}百万 |',f'| 合计 | {low/1e6:.1f}～{high/1e6:.1f}百万 |','','Codex自身合计约'+f'{codex["total_tokens"]/1e8:.2f}亿，其中缓存读取约{codex["cached_input_tokens"]/1e8:.2f}亿；缓存占Codex输入的{100*summary["codex"]["cached_fraction_of_codex_input"]:.1f}%。这解释了为何加入主agent后比仅作答/判分的五千多万高很多。','','这统计的是模型累计处理量，包括长上下文的多轮重复读取。不能说成“新生成了三亿token”，也不能按同等全价token直接换算现金。缓存是输入的一部分，推理token是输出的一部分，没有重复相加；参照 [OpenAI Docs：Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)。','','只纳入两轮主任务及其评分/复核agent。同一项目的其他独立对话及后台辅助审查另列，不混入主口径；若连这些可见记录一起计入，约'+f'{(low+extra["total_tokens"])/1e8:.2f}亿～{(high+extra["total_tokens"])/1e8:.2f}亿。','','试跑、失败重试、搜索服务内部未上报token未完整汇总。删题后的92/95题只是评分分母，已运行的2200份作答消耗没有扣回。不是账户账单，也不包含统计截点之后本轮核算继续发生的token。','','[逐项结构化统计及会话用量凭据](summary.json)。','']
 (OUT/'report.md').write_text('\n'.join(lines));(OUT/'ops').mkdir(exist_ok=True)
 import shutil
 shutil.copy2(Path(__file__),OUT/'ops/token_accounting.py')
 wr(OUT/'receipt.json',{'snapshot_at_utc':CUTOFF,'summary_sha256':sha(OUT/'summary.json'),'report_sha256':sha(OUT/'report.md'),'tool_sha256':sha(OUT/'ops/token_accounting.py'),'core_session_usage_projections':{r['thread_id']:r['usage_projection_sha256'] for r in per},'core_unique_requests':sum(r['unique_requests'] for r in per),'core_duplicate_usage_records_skipped':sum(r['duplicate_usage_records_skipped'] for r in per),'inherited_usage_records_skipped':sum(r['inherited_usage_records_skipped'] for r in per)})
 print(json.dumps({'main_estimate':[low,high],'codex_total':codex,'codex_main':codex_main,'codex_workers':codex_worker,'core_sessions':len(per),'core_requests':sum(r['unique_requests'] for r in per),'duplicates_skipped':sum(r['duplicate_usage_records_skipped'] for r in per),'inherited_skipped':sum(r['inherited_usage_records_skipped'] for r in per),'other_same_project_tokens':extra['total_tokens'],'expanded_estimate':[low+extra['total_tokens'],high+extra['total_tokens']],'report':str(OUT/'report.md')},ensure_ascii=False))
if __name__=='__main__':main()
