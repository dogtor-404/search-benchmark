#!/usr/bin/env python3
"""按用户选定的每次5分，补充逐次搜索展示与资源惩罚分；不改变盲评。"""
import argparse,collections,datetime,json,sys
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import multilingual as m
from common import ROOT,BenchError,load_jsonl,parse_stream,sha256,write_json,write_text,dumps
OUT=ROOT/'tmp/archive-multilingual'
PENALTY=5
NAMES={'0':'Sonnet 不搜索','A':'Sonnet 原生搜索','B':'Sonnet + DeepSeek 搜索','D0':'Flash 不搜索','D2':'Flash + DeepSeek 搜索','0_prime':'Opus 不搜索','A_prime':'Opus 原生搜索','B_prime':'Opus + DeepSeek 搜索','D0_prime':'Pro 不搜索','D2_prime':'Pro + DeepSeek 搜索'}

def score(verdict,calls):
 if not isinstance(calls,int) or isinstance(calls,bool) or not 0<=calls<=5:raise BenchError('实际搜索次数不在0–5')
 if verdict not in ['correct','incorrect','uncertain',None]:raise BenchError('评分标签无效')
 if verdict in ['uncertain',None]:return None
 return max(0,100-PENALTY*max(0,calls-1)) if verdict=='correct' else 0

def search_details(events,run):
 uses={};order=[];returns={}
 for event in events:
  for b in event.get('message',{}).get('content',[]) if isinstance(event.get('message',{}).get('content'),list) else []:
   if b.get('type')=='tool_use':
    oid=b['id']
    if oid in uses and uses[oid]!=b:raise BenchError('调用ID重复且内容不同')
    if oid not in uses:order.append(oid);uses[oid]=b
   elif b.get('type')=='tool_result':
    oid=b['tool_use_id']
    if oid in returns and returns[oid]!=b:raise BenchError('返回ID重复且内容不同')
    returns[oid]=b
 result=[]
 for oid in order:
  block=returns.get(oid)
  if block is None:raise BenchError('搜索缺少对应返回')
  if block.get('is_error'):continue
  content=block.get('content')
  if isinstance(content,str):texts=[content]
  elif isinstance(content,list) and all(isinstance(b,dict) and b.get('type')=='text' and isinstance(b.get('text'),str) for b in content):texts=[b['text'] for b in content]
  else:raise BenchError('搜索返回不是已支持的文本结构')
  result.append({'ordinal':len(result)+1,'tool_use_id':oid,'query':uses[oid].get('input',{}).get('query'),'returned_text':'\n'.join(texts),'returned_characters':sum(len(t) for t in texts),'returned_utf8_bytes':sum(len(t.encode('utf-8')) for t in texts)})
 if len(result)!=run['search_calls']:raise BenchError('逐次搜索展示与审计次数不同')
 if collections.Counter(r['query'] for r in result)!=collections.Counter(r['query'] for r in run['searches']):raise BenchError('逐次查询与审计参数不同')
 return result

def summarize(records,groups):
 summary={}
 for g in groups:
  rows=[r for r in records if r['group']==g];graded=[r for r in rows if r['verdict'] is not None];n=len(graded);correct=sum(r['verdict']=='correct' for r in graded);unknown=[r for r in graded if r['verdict']=='uncertain'];lower=sum(r['adjusted_score'] or 0 for r in graded);upper=lower+sum(score('correct',r['search_calls']) for r in unknown)
  summary[g]={'name':NAMES[g],'answered':len(rows),'graded':n,'correct':correct,'incorrect':sum(r['verdict']=='incorrect' for r in graded),'uncertain':len(unknown),'ungraded':len(rows)-n,'accuracy_bounds_on_graded':None if not n else [100*correct/n,100*(correct+len(unknown))/n],'adjusted_score_bounds_on_graded':None if not n else [lower/n,upper/n],'deduction_on_known_correct_total':sum(100-r['adjusted_score'] for r in graded if r['verdict']=='correct'),'mean_search_calls':sum(r['search_calls'] for r in rows)/len(rows) if rows else None,'search_histogram':{str(c):sum(r['search_calls']==c for r in rows) for c in range(6)},'search_attempts':sum(r['search_attempts'] for r in rows),'budget_denials':sum(r['budget_denials'] for r in rows),'argument_rejections':sum(r['argument_rejections'] for r in rows)}
 return summary

def comparisons(records,ids):
 table={(r['group'],r['question_id']):r for r in records};result={}
 for a,b in [('A','B'),('A_prime','B_prime')]:
  common=[q for q in ids if (a,q) in table and (b,q) in table and table[a,q]['adjusted_score'] is not None and table[b,q]['adjusted_score'] is not None];values=[table[b,q]['adjusted_score']-table[a,q]['adjusted_score'] for q in common];lower=upper=0
  def interval(g,q):
   r=table.get((g,q))
   if r is None:return [0,100]
   s=r['adjusted_score'];return [s,s] if s is not None else [0,score('correct',r['search_calls'])]
  for q in ids:
   av=interval(a,q);bv=interval(b,q);lower+=bv[0]-av[1];upper+=bv[1]-av[0]
  result[a+'__'+b]={'all_question_difference_bounds_points':[lower/len(ids),upper/len(ids)],'conditional_bootstrap_points':m.analyze.bootstrap(values,seed=20261021) if values else None,'complete_n':len(common)}
 return result

def fmt(value):return format(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'f')
def bounds(value):return '—' if value is None else fmt(value[0]) if value[0]==value[1] else fmt(value[0])+'–'+fmt(value[1])

def build(out=OUT,final=False):
 mf=m.read(out/'manifest.json');qfile=ROOT/mf['question_file']
 if sha256(qfile)!=mf['question_sha256']:raise BenchError('题库变化')
 qs={q['id']:q for q in load_jsonl(qfile)};mapping=m.read(out/'grading/mapping.json');gradefile=out/'jsonl/grades/independent.jsonl';grade_bytes=gradefile.read_bytes();grades=[json.loads(l) for l in grade_bytes.decode().splitlines() if l.strip()];votes={}
 for row in grades:
  meta=mapping[row['id']];key=(meta['group'],meta['question_id'])
  if key in votes:raise BenchError('同一作答重复评分')
  votes[key]=row['verdict']
 records=[];sources={}
 for g in mf['all_groups']:
  for qid in mf['question_ids']:
   p=out/'runs'/g/(qid+'.json')
   if not p.exists():continue
   run=m.read(p)
   if run['status']!='ok':continue
   run=m.check_run(out,g,qs[qid],mf['config']);raw=out/run['raw'];ids={b.get('tool_use_id') for b in run.get('budget_denials',[])};events,_=parse_stream(raw.read_text(),allowed_budget_denial_ids=ids);v=votes.get((g,qid));details=search_details(events,run)
   records.append({'group':g,'group_name':NAMES[g],'question_id':qid,'lang':qs[qid]['lang'],'question':qs[qid]['question'],'reference_answer':qs[qid]['answer'],'candidate_answer':run['answer'],'verdict':v,'search_calls':run['search_calls'],'search_attempts':run['search_attempts'],'budget_denials':run['search_budget_denials'],'argument_rejections':run['search_argument_rejections'],'adjusted_score':score(v,run['search_calls']),'possible_correct_score':score('correct',run['search_calls']),'searches':details,'raw':run['raw']})
   for path in [p,raw]:sources[str(path.relative_to(out))]=sha256(path)
 complete=len(records)==1200 and len(grades)==1200
 if final and not complete:raise BenchError('最终搜索得分要求1200份作答和1200份评分')
 policy={'user_authorization':'多次搜索也展示并扣分；每次扣5分（推荐）','adopted_during_run':True,'penalty_per_additional_search':5,'first_search_free':True,'incorrect_score':0,'no_search_correct_score':100,'score_formula':'correct: max(0,100-5*max(0,search_calls-1)); incorrect: 0; uncertain: [0,possible_correct_score]','notes':['运行中按用户要求新增的资源惩罚分，不替换原始正确率，不改变被测prompt、五次上限或盲评标准。','扣分只使用有效作答中的实际搜索调用；预算/参数拒绝未真正搜索不计，技术故障整次归档另列，不用基础设施故障扣答案分。','次数是模型可见工具调用口径；原生搜索内部如何改写、分发查询不可观测。文本块换行展示，原始结构保留在raw。','只按已评分样本计算阶段性分数，待评分与已评分但待核分开；待核给上下界，不按错题处理。','连续资源惩罚分使用按题配对bootstrap，不对它误用二元McNemar。原始正确率仍保留原McNemar。']}
 write_json(out/'analysis/search-score-policy.json',policy);summary={'generated_at':datetime.datetime.now().astimezone().isoformat(),'complete':complete,'answer_records':len(records),'grade_records':len(grades),'policy':policy,'groups':summarize(records,mf['all_groups']),'paired_comparisons':comparisons(records,mf['question_ids'])};write_json(out/'analysis/search-efficiency-summary.json',summary);write_text(out/'analysis/search-efficiency-records.jsonl',''.join(dumps(r)+'\n' for r in records))
 lines=['# 搜索次数与扣分','','状态：'+('全部作答与评分齐备。' if complete else '阶段性快照；各组题目进度不同，不能据此作最终排名。'),'','答对基础100分，首次搜索不扣，第二次起每次扣5分；答错0分。0次搜索且答对也为100分。待核分数为[0,假设答对时可得分]。原始正确率另保留。','','| 组 | 已作答/已评分 | 正确率范围% | 扣分后均分/100 | 待评分/待核 | 平均搜索次数 |','|---|---:|---:|---:|---:|---:|']
 for g,r in summary['groups'].items():lines.append(f'| {r["name"]} | {r["answered"]}/{r["graded"]} | {bounds(r["accuracy_bounds_on_graded"])} | {bounds(r["adjusted_score_bounds_on_graded"])} | {r["ungraded"]}/{r["uncertain"]} | {r["mean_search_calls"]:.2f} |' if r['answered'] else f'| {r["name"]} | 0/0 | — | — | 0/0 | — |')
 lines+=['','| 组 | 0次 | 1次 | 2次 | 3次 | 4次 | 5次 | 实际搜索合计 | 超限拒绝 | 参数拒绝 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for g,r in summary['groups'].items():lines.append('| '+r['name']+' | '+' | '.join(str(r['search_histogram'][str(i)]) for i in range(6))+f' | {sum(int(k)*v for k,v in r["search_histogram"].items())} | {r["budget_denials"]} | {r["argument_rejections"]} |')
 lines+=['','## 扣分后的同题比较','','差值为DeepSeek搜索减原生搜索，单位为0–100分上的分差。全题集范围计入待核/缺失的不确定性；条件bootstrap只用共同已判题。']
 for pair,r in summary['paired_comparisons'].items():
  boot=r['conditional_bootstrap_points'];lines+=['',f'- {pair}：全120题范围{bounds(r["all_question_difference_bounds_points"])}分。'+(f'条件n={boot["n"]}，差{boot["estimate"]:.2f}分，95%bootstrap区间[{boot["ci95"][0]:.2f}, {boot["ci95"][1]:.2f}]。' if boot else '共同已判样本不足。')]
 lines+=['','逐题扣分后取平均；答错始终0分，因此不能直接从正确率减去全组平均搜索次数对应的分数。不同工具每次返回量与摘要不同，按可见调用扣分衡量本工作流中的搜索效率，不等同于相同资料量下的检索能力或真实现金费用。','','## 逐题逐次返回','','[可展开的查询与返回摘要](search-efficiency.html)；[完整逐题明细](search-efficiency-records.jsonl)。每次查询、每次实际返回的文本与字节量均保留，并链接原始输出。原生搜索内部的查询拆分和改写不可观测，不能把可见调用次数当内部底层请求量。','','这是运行中按用户要求新增的评分，不是事先预注册指标。原始正确率、McNemar与全部原始结果保持可追溯。']
 write_text(out/'analysis/search-efficiency.md','\n'.join(lines)+'\n')
 template=(ROOT/'tools/search-efficiency-template.html').read_text();payload=json.dumps({'summary':summary,'records':records},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026');write_text(out/'analysis/search-efficiency.html',template.replace('/*__BENCHMARK_DATA__*/',payload))
 paths=[out/'analysis'/n for n in ['search-score-policy.json','search-efficiency-summary.json','search-efficiency-records.jsonl','search-efficiency.md','search-efficiency.html']]
 import hashlib
 receipt={'complete':complete,'answer_records':len(records),'grade_records':len(grades),'grade_snapshot_sha256':hashlib.sha256(grade_bytes).hexdigest(),'source_files_sha256':sources,'tool_sha256':sha256(ROOT/'tools/multilingual_search_efficiency.py'),'template_sha256':sha256(ROOT/'tools/search-efficiency-template.html'),'files':{str(p.relative_to(out)):sha256(p) for p in paths}};write_json(out/'analysis/search-efficiency-receipt.json',receipt)
 if final:
  main=out/'analysis/report.md';marker='\n## 搜索次数与扣分（运行中新增指标）\n';text=main.read_text().split(marker)[0]+marker+'\n按用户要求：答对100分，首次搜索不扣，第二次起每次扣5分；答错0分。待核另给范围。逐题扣分后取平均，非直接从正确率减去全组平均搜索的扣分。\n\n| 组 | 原正确率范围% | 扣分后均分/100 | 平均搜索次数 |\n|---|---:|---:|---:|\n'
  for g,r in summary['groups'].items():text+=f'| {r["name"]} | {bounds(r["accuracy_bounds_on_graded"])} | {bounds(r["adjusted_score_bounds_on_graded"])} | {r["mean_search_calls"]:.2f} |\n'
  text+='\n完整0–5次分布、扣分后配对区间见[搜索得分报告](search-efficiency.md)，[逐题逐次查询与返回](search-efficiency.html)。原正确率统计保留，不把运行中新增评分当事前指标；单次返回量和摘要不同，可见调用次数不等于内部请求量或现金费用。\n';write_text(main,text);completion=m.read(out/'analysis/completion-receipt.json');completion['search_efficiency_receipt_sha256']=sha256(out/'analysis/search-efficiency-receipt.json');completion['files'].update({str(p.relative_to(out)):sha256(p) for p in paths+[main,out/'analysis/search-efficiency-receipt.json']});write_json(out/'analysis/completion-receipt.json',completion)
 return {'complete':complete,'answers':len(records),'grades':len(grades),'report':str(out/'analysis/search-efficiency.md'),'viewer':str(out/'analysis/search-efficiency.html')}

if __name__=='__main__':
 try:
  p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');a=p.parse_args();print(dumps(build(final=a.final)))
 except (BenchError,ValueError,KeyError,FileNotFoundError) as e:print('搜索扣分报告停止：'+str(e),file=sys.stderr);sys.exit(1)
