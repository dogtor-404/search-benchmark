#!/usr/bin/env python3
"""配对统计、来源前五命中、成本记录；未复核和失败答案不当作错误答案。"""
import argparse,collections,datetime,json,math,random,statistics,sys,urllib.parse
from common import ROOT,BenchError,load_jsonl,dumps,write_json,write_text,sha256
from grade import resolve

def mcnemar(a,b):
 x=sum(u and not v for u,v in zip(a,b));y=sum(v and not u for u,v in zip(a,b));n=x+y
 return {'a_only':x,'b_only':y,'p_exact':min(1.0,2*sum(math.comb(n,i) for i in range(min(x,y)+1))/2**n) if n else 1.0}
def bootstrap(values,seed=20261020,draws=10000):
 if not values:raise BenchError('没有可比较的配对题。')
 rng=random.Random(seed);n=len(values);samples=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
 return {'estimate':statistics.mean(values),'ci95':[samples[int(draws*.025)],samples[min(draws-1,int(draws*.975))]],'n':n,'draws':draws}
def canonical(url):
 p=urllib.parse.urlsplit(url);host=(p.hostname or '').lower().removeprefix('www.').replace('en.m.wikipedia.org','en.wikipedia.org');path=urllib.parse.unquote(p.path).rstrip('/')
 query=urllib.parse.urlencode(sorted((k,v) for k,v in urllib.parse.parse_qsl(p.query) if not k.startswith('utm_')))
 return host,path,query

def source_hit(q,run):
 if not run['search_calls']:return None if run.get('searches') else False
 searches=run.get('searches',[])
 if not searches or any(s.get('ranking_observable') is False for s in searches):return None
 target={canonical(u) for u in q['source_urls']}
 return any(canonical(r['url']) in target for s in searches for r in s.get('results',[])[:5] if isinstance(r,dict) and 'url' in r)

def analyze(out):
 manifest=json.loads((out/'manifest.json').read_text())
 if manifest['question_sha256']!=sha256(ROOT/'questions/questions.jsonl'):raise BenchError('题库与运行时不一致。')
 resolved,pending=resolve(out)
 if pending:raise BenchError('还有人工复核未完成，不能给出最终准确率。')
 ids=manifest['question_ids'];groups=manifest['all_groups'];table={(r['group'],r['question_id']):int(r['correct']) for r in resolved}
 if len(table)!=len(ids)*len(groups) or any((g,q) not in table for g in groups for q in ids):raise BenchError('配对结果不完整。')
 qs={q['id']:q for q in load_jsonl(ROOT/'questions/questions.jsonl')};report={'phase':manifest['phase'],'groups':{},'comparisons':{}}
 for g in groups:
  runs=[json.loads((out/'runs'/g/(q+'.json')).read_text()) for q in ids]
  if any(r['status']!='ok' for r in runs):raise BenchError('存在失败运行。')
  hits=[source_hit(qs[q],r) for q,r in zip(ids,runs)] if manifest['config']['groups'][g]['search']!='none' else []
  observed=[h for h in hits if h is not None]
  report['groups'][g]={'n':len(ids),'accuracy':sum(table[g,q] for q in ids)/len(ids),'source_hit_at_5':sum(observed)/len(observed) if observed else None,'source_observable_n':len(observed),'mean_search_attempts':statistics.mean(r.get('search_attempts',r['search_calls']) for r in runs),'budget_denials':sum(r.get('search_budget_denials',0) for r in runs),'mean_search_calls':statistics.mean(r['search_calls'] for r in runs),'mean_seconds':statistics.mean(r['elapsed_seconds'] for r in runs),'search_cost_usd':sum(r['search_cost_usd'] for r in runs),'reported_model_cost_usd':sum(r.get('reported_cost_usd') or 0 for r in runs),'cost_note':'Claude 的 reported_model_cost 是 CLI 报告的名义 API 估值，不是订阅扣款；DeepSeek 的实际扣款需核对账单。'}
 for a,b in [('A','B'),('A_prime','B_prime')]:
  av=[table[a,q] for q in ids];bv=[table[b,q] for q in ids];report['comparisons'][f'{a}-{b}']={**bootstrap([u-v for u,v in zip(av,bv)]),**mcnemar(av,bv)}
 for name,gs in [('B-0 vs D2-D0',('B','0','D2','D0')),('B_prime-0_prime vs D2_prime-D0_prime',('B_prime','0_prime','D2_prime','D0_prime')),('Claude DeepSeek搜索 高档-中档',('B_prime','0_prime','B','0')),('DeepSeek 高档-中档',('D2_prime','D0_prime','D2','D0')),('Claude 原生搜索 高档-中档',('A_prime','0_prime','A','0'))]:
  a,b,c,d=gs;report['comparisons'][name]=bootstrap([table[a,q]-table[b,q]-table[c,q]+table[d,q] for q in ids])
 # 错误原因由人工看搜索轨迹填写，不能从“答错”自动猜成“没搜到”。
 failures=[{'group':g,'question_id':q,'error_type':None,'note':''} for g in groups for q in ids if not table[g,q]]
 fp=out/'analysis/error-review.jsonl'
 if not fp.exists():write_text(fp,''.join(dumps(r)+'\n' for r in failures))
 write_json(out/'analysis/summary.json',report)
 lines=['# '+('试跑结果' if manifest['phase']=='pilot' else '测试结果'),'','| 组 | 题数 | 答对率 | 前五来源命中率 | 平均搜索次数 | 平均秒数 |','|---|---:|---:|---:|---:|---:|']
 for g,r in report['groups'].items():
  hit='不可观测' if r['source_hit_at_5'] is None else f'{r["source_hit_at_5"]:.1%}（{r["source_observable_n"]}题）'
  lines.append(f'| {g} | {r["n"]} | {r["accuracy"]:.1%} | {hit} | {r["mean_search_calls"]:.2f} | {r["mean_seconds"]:.1f} |')
 lines+=['','配对差值及 95% bootstrap 区间：']
 for name,r in report['comparisons'].items():
  lo,hi=r['ci95'];lines.append(f'- {name}：{r["estimate"]:.1%}，[{lo:.1%}, {hi:.1%}]'+('；看不出区别。' if lo<=0<=hi else '。'))
 lines+=['','这份汇总尚未补人工错误原因和典型例子。来源命中只比较每次搜索的前五条 URL；无法读到原始排名时留空。订阅名义费用不等于现金支出。']
 if manifest['phase']=='pilot':lines+=['','试跑只有十道题，不作排名结论；全量时间和用量可按运行次数约十倍估计，但周额度百分比需用户在 Claude 中核对。']
 write_text(out/'analysis/report.md','\n'.join(lines)+'\n');print(dumps({'groups':len(groups),'questions':len(ids),'output':str(out/'analysis/report.md')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','full'],default='pilot');a=p.parse_args()
 try:analyze(ROOT/('tmp/pilot' if a.phase=='pilot' else 'tmp/archive'))
 except (BenchError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
