import collections,hashlib,json,math,re,urllib.parse
from pathlib import Path
ROOT=Path(str(Path(__file__).resolve().parents[3]));OUT=ROOT/'results/2026-10-21-unified-score';OLD=ROOT/'results/2026-10-21-response-review/no-search-double-blind'
def rd(p):return json.loads(p.read_text())
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checked=0
for folder,receipt in [(ROOT/'tmp/archive/analysis','report-receipt.json'),(ROOT/'results/2026-10-21-multilingual','analysis/completion-receipt.json'),(ROOT/'results/2026-10-20-supplement','receipt.json'),(ROOT/'results/2026-10-21-response-review','receipt.json'),(OLD,'report-receipt.json'),(OUT,'report-receipt.json')]:
 for rel,d in rd(folder/receipt)['files'].items():assert sha(folder/rel)==d,(folder,rel);checked+=1
for folder in [OLD,OUT]:
 p=rd(folder/'protocol.json')
 for rel,d in p['source_files_sha256'].items():assert sha(ROOT/rel)==d,rel;checked+=1
 for part in p['parts']:
  source=folder/part['path'];inp=jl(source);assert sha(source)==part['sha256'];lookup={r['id']:r for r in inp}
  for who in ['reviewer-a','reviewer-b']:
   path=folder/'votes'/who/source.name;proof=rd(path.with_suffix('.receipt.json'));v=jl(path)
   assert len(v)==proof['records']==len(inp);assert [r['id'] for r in v]==[r['id'] for r in inp];assert sha(source)==proof['input_sha256'] and sha(path)==proof['output_sha256']
   assert all(r['evidence_quote'] and r['evidence_quote'] in lookup[r['id']]['candidate_answer'] for r in v)
  third=folder/'votes/adjudicator'/source.name
  if third.exists():
   tin=folder/'adjudicator-input'/source.name;proof=rd(third.with_suffix('.receipt.json'));assert sha(tin)==proof['input_sha256'] and sha(third)==proof['output_sha256']
s=rd(OUT/'summary.json');rs=jl(OUT/'score-records.jsonl');assert len(rs)==len({(r['round'],r['group'],r['question_id']) for r in rs})==2200
for r in rs:
 run=rd(ROOT/r['source_run']);assert run['answer']==r['candidate_answer'] and run['search_calls']==r['search_calls'];penalty=max(run['search_calls']-1,0);assert penalty==r['search_penalty']
 if r['decision'] in ['no_answer','withdrawn_answer']:lo=hi=0
 elif r['original_correct'] is True:lo=hi=5
 elif r['original_correct'] is False:lo=hi=-3
 else:lo,hi=-3,5
 assert (r['score_lower'],r['score_upper'])==(lo-penalty,hi-penalty)
 assert (r['base_lower'],r['base_upper'])==(lo,hi)
policy=rd(ROOT/'results/2026-10-20-revised-96/policy.json');exclude=set(policy['exclusions'])
for view,c in s['cohorts'].items():
 filtered=[r for r in rs if r['round']==('second' if view=='second_120' else 'first') and (view!='first_96' or r['question_id'] not in exclude)]
 for group,v in c['groups'].items():
  group_rows=[r for r in filtered if r['group']==group];n=len(group_rows);assert n==v['n']==c['questions_per_group'];assert sum(v['outcome_counts'].values())==n
  assert sum(r['score_lower'] for r in group_rows)==v['total_lower'];assert sum(r['score_upper'] for r in group_rows)==v['total_upper'];assert math.isclose(v['mean_lower'],v['total_lower']/n);assert sum(r['search_penalty'] for r in group_rows)==v['search_penalty_total']
  for k,count in v['outcome_counts'].items():assert sum(r['scoring_outcome']==k for r in group_rows)==count
 for cmp in c['comparisons'].values():
  a={r['question_id']:r for r in filtered if r['group']==cmp['a']};b={r['question_id']:r for r in filtered if r['group']==cmp['b']};assert a.keys()==b.keys();ids=list(a)
  assert math.isclose(sum(b[q]['score_lower']-a[q]['score_upper'] for q in ids)/len(ids),cmp['mean_difference_lower'])
  assert math.isclose(sum(b[q]['score_upper']-a[q]['score_lower'] for q in ids)/len(ids),cmp['mean_difference_upper'])
for group in s['cohorts']['second_120']['groups']:
 assert sum(s['cohorts']['second_120']['languages'][l][group]['total_lower'] for l in s['cohorts']['second_120']['languages'])==s['cohorts']['second_120']['groups'][group]['total_lower']
files=[ROOT/n for n in ['README.md','report.md','report-first-round.md','report-multilingual.md','results/2026-10-21-response-review/README.md']]+[OUT/'report.md',OLD/'report.md'];broken=[]
for path in files:
 for target in re.findall(r'\[[^\]]*\]\(([^()\s]+)\)',path.read_text()):
  if target.startswith(('http:','https:','mailto:','#','codex:')):continue
  target=urllib.parse.unquote(target.split('#')[0]);dest=(path.parent/target).resolve()
  if not dest.exists():broken.append((str(path.relative_to(ROOT)),target))
assert not broken,broken
print(json.dumps({'score_answers':2200,'primary_answers':2160,'new_review_records':328,'new_disagreements':s['review']['third_adjudications'],'preserved_source_and_receipted_files_checked':checked,'documents_with_valid_links':len(files),'all_arithmetic_valid':True,'original_grade_receipts_intact':True},ensure_ascii=False))
