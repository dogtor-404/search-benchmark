"""校验盲判输出、发布匿名分歧包；不做语义分类或新模型调用。"""
import collections, datetime, hashlib, json, shutil
from pathlib import Path

ROOT=Path(str(Path(__file__).resolve().parents[4]))
OUT=ROOT/'results/2026-10-21-response-review/no-search-double-blind'
STAGE=Path(__import__('os').environ.get('BENCH_WORKSPACE', str(Path(__file__).resolve().parents[4])+'/tmp/workspace'))
LABELS={'explicit_abstention','confident_incorrect_assertion','incomplete_answer','hedged_or_withdrawn_guess'}
FIELDS={'id','category','rationale','evidence_quote','reference_concern','reference_concern_reason'}

def read(p): return json.loads(p.read_text())
def jl(p): return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def text_file(p,text):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): assert p.read_text()==text, '不可变文件内容冲突：'+str(p)
    else: p.write_text(text)

def validate(path,source,reviewer):
    proof=path.with_suffix('.receipt.json')
    if not path.exists() or not proof.exists():return None
    receipt=read(proof);inputs=jl(source);rows=jl(path)
    assert receipt['input_sha256']==sha(source) and receipt['output_sha256']==sha(path)
    assert receipt['records']==len(inputs)==len(rows) and receipt['reviewer']==reviewer and receipt['human'] is False
    assert len({r['id'] for r in rows})==len(rows) and {r['id'] for r in rows}=={r['id'] for r in inputs}
    lookup={r['id']:r for r in inputs}
    for r in rows:
        assert set(r)==FIELDS and r['category'] in LABELS
        assert isinstance(r['rationale'],str) and r['rationale'].strip()
        assert isinstance(r['evidence_quote'],str) and r['evidence_quote'] and r['evidence_quote'] in lookup[r['id']]['candidate_answer']
        assert isinstance(r['reference_concern'],bool) and isinstance(r['reference_concern_reason'],str)
        if r['reference_concern']:assert r['reference_concern_reason'].strip()
    return rows

def collect():
    protocol=read(OUT/'protocol.json')
    assert sha(OUT/'rubric.md')==protocol['rubric_sha256'] and sha(STAGE/'rubric.md')==protocol['rubric_sha256']
    assert sha(OUT/'blind.jsonl')==protocol['blind_sha256'] and sha(OUT/'private-mapping.json')==protocol['mapping_sha256']
    batches=[];votes={'a':[],'b':[]};counts={};dispute_ids=[];ready_third=[];third=[]
    for n,part in enumerate(protocol['parts']):
        source=OUT/part['path'];assert sha(source)==part['sha256']
        assert sha(STAGE/'input'/source.name)==part['sha256']
        pair={}
        for letter in ['a','b']:
            path=STAGE/('reviewer-'+letter)/source.name
            rows=validate(path,source,'independent_response_judge_'+letter)
            if rows is None:continue
            pair[letter]={r['id']:r for r in rows};votes[letter]+=rows
            dest=OUT/'votes'/('reviewer-'+letter)/source.name
            for src,dst in [(path,dest),(path.with_suffix('.receipt.json'),dest.with_suffix('.receipt.json'))]:
                dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():assert sha(dst)==sha(src)
                else:shutil.copy2(src,dst)
        if len(pair)!=2:continue
        inputs=jl(source);disputes=[r for r in inputs if pair['a'][r['id']]['category']!=pair['b'][r['id']]['category']]
        counts[source.name]={'reviewed_by_both':len(inputs),'agreement':len(inputs)-len(disputes),'disagreement':len(disputes)}
        dispute_ids += [r['id'] for r in disputes]
        if not disputes:continue
        payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in disputes)
        canonical=OUT/'adjudicator-input'/source.name;staged=STAGE/'adjudicator-input'/source.name
        text_file(canonical,payload);text_file(staged,payload)
        rows=validate(STAGE/'adjudicator'/source.name,canonical,'independent_response_adjudicator')
        if rows is None:ready_third.append(source.name)
        else:
            third+=rows
            dest=OUT/'votes/adjudicator'/source.name
            for src,dst in [(STAGE/'adjudicator'/source.name,dest),(STAGE/'adjudicator'/source.with_suffix('.receipt.json').name,dest.with_suffix('.receipt.json'))]:
                dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():assert sha(src)==sha(dst)
                else:shutil.copy2(src,dst)
    for letter,rows in votes.items():
        if len(rows)==402:text_file(OUT/'votes'/('reviewer-'+letter+'.jsonl'),''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
    complete=len(votes['a'])==len(votes['b'])==402 and len(third)==len(dispute_ids)
    status={'updated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'reviewer_a_records':len(votes['a']),'reviewer_b_records':len(votes['b']),'paired_reviewed_records':sum(r['reviewed_by_both'] for r in counts.values()),'disagreement_records':len(dispute_ids),'adjudicated_records':len(third),'adjudicator_batches_ready':ready_third,'batches':counts,'complete':complete}
    write(OUT/'progress.json',status)
    if complete:
        a={r['id']:r for r in votes['a']};b={r['id']:r for r in votes['b']};c={r['id']:r for r in third};mapping=read(OUT/'private-mapping.json');final=[]
        for original in jl(OUT/'blind.jsonl'):
            oid=original['id'];disagree=a[oid]['category']!=b[oid]['category'];chosen=c[oid] if disagree else a[oid]
            final.append(dict(original,**mapping[oid],category=chosen['category'],rationale=chosen['rationale'],evidence_quote=chosen['evidence_quote'],reference_concern=any(r.get('reference_concern') for r in [a[oid],b[oid],c.get(oid,{})]),reference_concern_reasons={j:r['reference_concern_reason'] for j,r in [('a',a[oid]),('b',b[oid]),('c',c.get(oid,{}))] if r.get('reference_concern')},resolution='third_independent_adjudication' if disagree else 'two_independent_agreement',categories={'a':a[oid]['category'],'b':b[oid]['category'],**({'c':c[oid]['category']} if disagree else {})}))
        text_file(OUT/'resolved.jsonl',''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in final))
        text_file(OUT/'votes/adjudicator.jsonl',''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in third))
        write(OUT/'resolution-receipt.json',{'records':len(final),'disagreements':len(dispute_ids),'adjudicated':len(third),'rubric_sha256':protocol['rubric_sha256'],'blind_sha256':protocol['blind_sha256'],'mapping_sha256':protocol['mapping_sha256'],'resolved_sha256':sha(OUT/'resolved.jsonl'),'votes_sha256':{j:sha(OUT/'votes'/(name+'.jsonl')) for j,name in [('a','reviewer-a'),('b','reviewer-b'),('c','adjudicator')]},'method':protocol['scoring']})
    print(json.dumps(status,ensure_ascii=False))
    return status

if __name__=='__main__':collect()
