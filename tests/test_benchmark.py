"""离线契约测试：不联网、不读钥匙串、不调用真实模型。"""
import datetime,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import common,bench,deepseek_search,search_budget,analyze,grade
class Tests(unittest.TestCase):
 @unittest.skipUnless((ROOT/'questions/questions.jsonl').exists(), '需先运行 python3 tools/restore_first_round.py 重建第一轮题库')
 def test_news_window_boundaries(self):
  qs=common.load_jsonl(ROOT/'questions/questions.jsonl');news=next(q for q in qs if q['set']=='news');today=datetime.date(2026,10,20)
  for age in (0,15,30):
   news['event_date']=(today-datetime.timedelta(days=age)).isoformat()
   self.assertFalse(any('新闻超出' in e for e in bench.validate(qs,strict=True,today=today)))
  for age in (31,-1):
   news['event_date']=(today-datetime.timedelta(days=age)).isoformat()
   self.assertTrue(any('新闻超出' in e for e in bench.validate(qs,strict=True,today=today)))
 def test_unknown_cutoffs_do_not_block(self):
  cfg=json.loads((ROOT/'tools/config.json').read_text())
  cfg['knowledge_cutoffs']={model:None for model in cfg['model_versions']}
  self.assertEqual(bench.validate_models(cfg),[])
  cfg['model_versions']['deepseek-flash']=None
  self.assertTrue(any('deepseek-flash' in e for e in bench.validate_models(cfg)))
 @unittest.skipUnless((ROOT/'questions/questions.jsonl').exists(), '需先运行 python3 tools/restore_first_round.py 重建第一轮题库')
 def test_same_pilot_all_groups(self):
  qs=common.load_jsonl(ROOT/'questions/questions.jsonl');chosen=bench.select(qs,'pilot')
  self.assertEqual(len(chosen),10);self.assertEqual(len({q['id'] for q in chosen}),10)
  self.assertEqual(bench.select(qs,'pilot'),chosen)
 def test_group_isolation_and_prompt(self):
  cfg=json.loads((ROOT/'tools/config.json').read_text())
  for g in cfg['groups'].values():
   cmd=bench.command(g,cfg);self.assertIn('--strict-mcp-config',cmd);self.assertIn('project,local',cmd);self.assertNotIn('--bare',cmd)
   self.assertEqual(cmd[cmd.index('--tools')+1],'WebSearch' if g['search']=='claude' else '')
   text=bench.prompt({'question':'测试题'},g,cfg);self.assertTrue(text.endswith('\n\n测试题'))
 def test_clear_conflicting_auth(self):
  with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'bad','ANTHROPIC_AUTH_TOKEN':'bad','ANTHROPIC_BASE_URL':'https://bad.example','DEEPSEEK_API_KEY':'bad','CLAUDE_CODE_USE_BEDROCK':'1'}):
   env=common.clean_env();self.assertNotIn('ANTHROPIC_API_KEY',env);self.assertNotIn('ANTHROPIC_BASE_URL',env);self.assertNotIn('DEEPSEEK_API_KEY',env);self.assertNotIn('CLAUDE_CODE_USE_BEDROCK',env)
 def test_prevent_secret_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'out';secret='unit-test-secret'
   with self.assertRaises(common.BenchError):common.write_text(p,secret,[secret])
   self.assertFalse(p.exists())
 def test_budget_sixth_denied_and_persistent(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'counter'
   for _ in range(5):self.assertEqual(search_budget.decide({'tool_name':'WebSearch'},p)[0],'allow')
   self.assertEqual(search_budget.decide({'tool_name':'WebSearch'},p)[0],'deny');self.assertEqual(p.read_text(),'5')
 def test_mcp_count_and_payload(self):
  calls=[]
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return json.dumps({'results':[{'title':'t','url':'https://example.org','snippet':'s','summary':'m','date':None,'content':'must not pass'}]}).encode()
  class Opener:
   def open(self,request,timeout):calls.append(json.loads(request.data));return Response()
  with patch.dict(os.environ,{'BENCH_DEEPSEEK_KEY':'fake-test-credential'}),patch('urllib.request.build_opener',return_value=Opener()):
   tool=deepseek_search.Search()
   for _ in range(5):self.assertFalse(tool.call({'query':'测试'})['isError'])
   self.assertTrue(tool.call({'query':'测试'})['isError']);self.assertEqual(len(calls),5)
   self.assertTrue(all(c=={'query':'测试','count':10,'need_content':False} for c in calls))
 def test_mcp_restart_keeps_budget(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'BENCH_DEEPSEEK_KEY':'fake-test-credential','BENCH_SEARCH_LOG':str(Path(tmp)/'search.jsonl')}),patch('urllib.request.build_opener',side_effect=TimeoutError) as network:
   for _ in range(5):
    tool=deepseek_search.Search();self.assertTrue(tool.call({'query':'测试'})['isError'])
   before=network.call_count
   self.assertTrue(deepseek_search.Search().call({'query':'测试'})['isError']);self.assertEqual(network.call_count,before)
   self.assertEqual((Path(tmp)/'mcp-count.txt').read_text(),'5')
 def test_mcp_failure_no_hidden_retry(self):
  with patch.dict(os.environ,{'BENCH_DEEPSEEK_KEY':'fake-test-credential'}),patch('urllib.request.build_opener',side_effect=TimeoutError):
   tool=deepseek_search.Search();self.assertTrue(tool.call({'query':'测试'})['isError']);self.assertEqual(tool.calls,1)
 def test_tool_audit(self):
  init={'type':'system','subtype':'init','tools':['Read']}
  with self.assertRaises(common.BenchError):bench.verify_events([init],{'search':'none'})
  with self.assertRaises(common.BenchError):bench.verify_events([],{'search':'none'})
 def test_stream_error_is_not_answer(self):
  for r in [{'type':'result','is_error':True,'result':'bad'},{'type':'result','subtype':'error_max_turns','result':'bad'}]:
   with self.assertRaises(common.BenchError):common.parse_stream(json.dumps(r))
 def test_native_rank_not_inferred_from_citations(self):
  events=[{'type':'system','subtype':'init','tools':['WebSearch']},{'message':{'content':[{'type':'tool_use','name':'WebSearch','id':'x'}]}},{'message':{'content':[{'type':'tool_result','tool_use_id':'x','content':[{'type':'text','text':'answer citation https://example.org'}]}]}}]
  calls,searches,_=bench.verify_events(events,{'search':'claude'});self.assertEqual(calls,['WebSearch']);self.assertFalse(searches[0]['ranking_observable'])
 def test_source_top_five_not_six(self):
  q={'source_urls':['https://example.org/gold#fragment']};rows=[{'url':f'https://example.org/{i}'} for i in range(5)]+[{'url':'https://example.org/gold'}]
  self.assertFalse(analyze.source_hit(q,{'search_calls':1,'searches':[{'results':rows}]}));rows[0]={'url':'http://www.example.org/gold?utm_source=abc'}
  self.assertTrue(analyze.source_hit(q,{'search_calls':1,'searches':[{'results':rows}]}));self.assertIsNone(analyze.source_hit(q,{'search_calls':1,'searches':[{'ranking_observable':False}]}))
 def test_paired_statistics(self):
  self.assertEqual(analyze.mcnemar([1]*5,[0]*5)['p_exact'],.0625)
  self.assertEqual(analyze.mcnemar([1,0],[1,0])['p_exact'],1)
  result=analyze.bootstrap([1]*10,draws=100);self.assertEqual(result['ci95'],[1,1]);self.assertEqual(result['estimate'],1)
 def test_blind_payload_schema(self):
  self.assertEqual(set(grade.SCHEMA['properties']),{'verdict','reason'})
 @unittest.skipUnless((ROOT/'questions/questions.jsonl').exists(), '需先运行 python3 tools/restore_first_round.py 重建第一轮题库')
 def test_bad_questions_block_live(self):
  qs=common.load_jsonl(ROOT/'questions/questions.jsonl');self.assertEqual(bench.validate(qs),[])
  qs[0]['review']['status']='pending';self.assertTrue(any('尚未核实' in e for e in bench.validate(qs,strict=True)))

class PipelineTests(unittest.TestCase):
 def test_mcp_stdio_handshake(self):
  import subprocess
  requests=[{'jsonrpc':'2.0','id':1,'method':'initialize'},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'}]
  p=subprocess.run([sys.executable,str(ROOT/'tools/deepseek_search.py')],input='\n'.join(json.dumps(r) for r in requests)+'\n',capture_output=True,text=True,check=True)
  rows=[json.loads(s) for s in p.stdout.splitlines()];self.assertEqual(len(rows),2);self.assertEqual(rows[1]['result']['tools'][0]['name'],'search')
 @unittest.skipUnless((ROOT/'questions/questions.jsonl').exists(), '需先运行 python3 tools/restore_first_round.py 重建第一轮题库')
 def test_full_offline_pipeline(self):
  import subprocess
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'bin').mkdir();(root/'tools').mkdir();(root/'questions').mkdir();cfg=json.loads((ROOT/'tools/config.json').read_text());(root/'tools/config.json').write_text(json.dumps(cfg))
   qs=bench.select(common.load_jsonl(ROOT/'questions/questions.jsonl'),'pilot');(root/'questions/questions.jsonl').write_text(''.join(common.dumps(q)+'\n' for q in qs))
   fake=root/'bin/claude';fake.write_text('#!'+sys.executable+'\nimport json,sys\na=sys.argv\nprompt=sys.stdin.read()\nprint(json.dumps({"type":"system","subtype":"init","tools":[]}))\nprint(json.dumps({"type":"result","subtype":"success","is_error":False,"result":"fixture answer","usage":{"input_tokens":1,"output_tokens":1},"total_cost_usd":0}))\n');fake.chmod(0o700)
   out=root/'tmp/pilot';manifest={'phase':'pilot','seed':20261020,'all_groups':list(cfg['groups']),'question_ids':[q['id'] for q in qs],'question_sha256':common.sha256(root/'questions/questions.jsonl'),'config':cfg};common.write_json(out/'manifest.json',manifest)
   with patch.dict(os.environ,{'PATH':str(root/'bin')+os.pathsep+os.environ['PATH']}),patch.object(bench,'ROOT',root),patch.object(grade,'ROOT',root),patch.object(analyze,'ROOT',root),patch.object(bench,'keychain_key',return_value='fake-test-credential'):
    for gid,g in cfg['groups'].items():
     for q in qs:
      r=bench.execute_one(q,gid,g,cfg,out,10);self.assertEqual(r['status'],'ok')
    grade.prepare(out);mapping=json.loads((out/'grading/mapping.json').read_text());blind=common.load_jsonl(out/'grading/blind.jsonl');self.assertEqual(len(blind),100)
    self.assertTrue(all(set(r)=={'id','question','reference_answer','aliases','candidate_answer'} for r in blind))
    self.assertTrue(all(not any(k in r for k in ['group','model','source_urls','question_id']) for r in blind))
    first=blind[0]['id']
    for name in ['claude','deepseek']:
     rows=[{'id':r['id'],'verdict':'incorrect' if name=='deepseek' and r['id']==first else 'correct','reason':'fixture'} for r in blind]
     common.write_text(out/'jsonl/grades'/(name+'.jsonl'),''.join(common.dumps(r)+'\n' for r in rows))
    resolved,pending=grade.resolve(out);self.assertEqual(len(pending),1);self.assertEqual(len(resolved),99)
    with self.assertRaises(common.BenchError):analyze.analyze(out)
    common.write_text(out/'grading/human.jsonl',common.dumps({'id':first,'verdict':'correct','reason':'人工复核测试'})+'\n');analyze.analyze(out)
    summary=json.loads((out/'analysis/summary.json').read_text());self.assertEqual(len(summary['groups']),10);self.assertTrue(all(r['accuracy']==1 for r in summary['groups'].values()))
    common.write_text(out/'grading/blind.jsonl','tampered')
    with self.assertRaises(common.BenchError):grade.resolve(out)
 def test_budget_concurrency(self):
  import concurrent.futures
  with tempfile.TemporaryDirectory() as tmp:
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:decisions=list(ex.map(lambda _:search_budget.decide({'tool_name':'WebSearch'},Path(tmp)/'counter')[0],range(12)))
   self.assertEqual(decisions.count('allow'),5);self.assertEqual(decisions.count('deny'),7)

if __name__=='__main__':unittest.main()
