"""预算拒绝与启动环境回归：全程使用假 CLI、假 HTTP，不调用真实模型。"""
import io,json,os,subprocess,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import common,bench,deepseek_search,grade

class RegressionTests(unittest.TestCase):
 def test_structured_output_only_allowed_for_judges(self):
  events=[{'type':'system','subtype':'init','tools':['StructuredOutput']},{'message':{'content':[{'type':'tool_use','id':'format','name':'StructuredOutput','input':{'verdict':'correct','reason':'fixture'}}]}}]
  with self.assertRaises(common.BenchError):bench.verify_events(events,{'search':'none'})
  calls,_,_=bench.verify_events(events,{'search':'none','structured_output':True})
  self.assertEqual(calls,['StructuredOutput'])
  events[0]['tools'].append('Read')
  with self.assertRaises(common.BenchError):bench.verify_events(events,{'search':'none','structured_output':True})
 def test_grading_reuses_valid_raw_without_model_call(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);out=root/'pilot';cfg={'judges':{'deepseek':'fixture-model'}}
   common.write_json(out/'manifest.json',{'config':cfg})
   row={'id':'opaque','question':'q','reference_answer':'a','aliases':[],'candidate_answer':'a'}
   common.write_text(out/'grading/blind.jsonl',common.dumps(row)+'\n')
   common.write_json(out/'grading/receipt.json',{'blind_sha256':common.sha256(out/'grading/blind.jsonl')})
   events=[{'type':'system','subtype':'init','tools':['StructuredOutput']},{'message':{'content':[{'type':'tool_use','name':'StructuredOutput','id':'format','input':{'verdict':'correct','reason':'fixture'}}]}},{'type':'result','subtype':'success','result':'','structured_output':{'verdict':'correct','reason':'fixture'}}]
   raw=out/'grading/raw/deepseek/opaque.jsonl';common.write_text(raw,''.join(common.dumps(e)+'\n' for e in events));original=raw.read_bytes()
   with patch.object(grade,'keychain_key',side_effect=AssertionError('不应重读凭据')),patch.object(grade.subprocess,'run',side_effect=AssertionError('不应重复调用模型')):
    grade.run(out,'deepseek',True,True,10)
    grade.run(out,'deepseek',True,True,10)
   records=common.load_jsonl(out/'jsonl/grades/deepseek.jsonl');self.assertEqual(len(records),1);self.assertTrue(records[0]['reused_raw']);self.assertEqual(raw.read_bytes(),original)
 def test_clean_all_claude_and_ide_context(self):
  injected={k:'inherited-setting' for k in ['CLAUDECODE','CLAUDE_EFFORT','CLAUDE_CODE_SESSION_ID','CLAUDE_UNKNOWN_FUTURE_SETTING','VSCODE_IPC_HOOK_CLI','CURSOR_TRACE_ID','WINDSURF_SESSION','JETBRAINS_CLIENT','IDEA_INITIAL_DIRECTORY','PYCHARM_HOSTED','WEBSTORM_FLAGS','GOLAND_FLAGS','CLION_FLAGS','FLEET_SESSION','ZED_TERM','ELECTRON_RUN_AS_NODE','NODE_OPTIONS','GIT_ASKPASS','SSH_ASKPASS']}
  injected.update(TERM_PROGRAM='vscode',TERM_PROGRAM_VERSION='test',TERM_SESSION_ID='test',HTTPS_PROXY='http://127.0.0.1:9999')
  with patch.dict(os.environ,injected):
   env=common.clean_env()
   self.assertFalse(set(injected)-{'HTTPS_PROXY'} & set(env))
   self.assertEqual(env['HTTPS_PROXY'],injected['HTTPS_PROXY']);self.assertEqual(env['PATH'],os.environ['PATH'])
   self.assertEqual({k:v for k,v in env.items() if k.startswith('CLAUDE')},{'CLAUDE_CODE_DISABLE_AUTO_MEMORY':'1'})
 def test_unrelated_permission_denial_still_fails(self):
  final={'type':'result','subtype':'success','result':'answer','permission_denials':[{'tool_name':'WebSearch','tool_use_id':'other'}]}
  with self.assertRaises(common.BenchError):common.parse_stream(json.dumps(final),allowed_budget_denial_ids={'sixth'})
  final['permission_denials']=[{'tool_name':'Read','tool_use_id':'sixth'}]
  with self.assertRaises(common.BenchError):common.parse_stream(json.dumps(final),allowed_budget_denial_ids={'sixth'})
 def test_sixth_and_later_searches_do_not_stop_next_question(self):
  cfg=json.loads((ROOT/'tools/config.json').read_text())
  fake_source=r'''
import io,json,os,sys
sys.path.insert(0,TOOLS)
from search_budget import decide
import deepseek_search
assert not any(k in os.environ for k in ('CLAUDECODE','CLAUDE_EFFORT','CLAUDE_CODE_SESSION_ID','VSCODE_IPC_HOOK_CLI'))
args=sys.argv;sys.stdin.read();native=args[args.index('--tools')+1]=='WebSearch';name='WebSearch' if native else 'mcp__deepseek-search__search'
print(json.dumps({'type':'system','subtype':'init','tools':[name]}))
network_calls=[]
class Opener:
 def open(self,request,timeout):
  network_calls.append(request)
  return io.BytesIO(json.dumps({'results':[{'title':'fixture','url':'https://example.org/answer','snippet':'fixture','summary':'fixture','date':None}]}).encode())
deepseek_search.urllib.request.build_opener=lambda *args:Opener()
search=deepseek_search.Search();denials=[]
for i in range(8):
 tid=f'tool-{i}';query=f'query-{i}'
 print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':tid,'name':name,'input':{'query':query}}]}}))
 if native:
  decision,reason=decide({'tool_name':name,'tool_use_id':tid,'tool_input':{'query':query}},os.environ['BENCH_NATIVE_BUDGET'],os.environ['BENCH_NATIVE_AUDIT'])
  denied=decision=='deny'
  if denied:denials.append({'tool_name':name,'tool_use_id':tid,'tool_input':{'query':query}})
  content=[{'type':'text','text':reason if denied else 'Links: [{"title":"fixture","url":"https://example.org/answer"}]'}]
 else:
  response=search.call({'query':query});denied=response['isError'];content=response['content']
 print(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':tid,'is_error':denied,'content':content}]}}))
if not native:assert len(network_calls)==5
print(json.dumps({'type':'result','subtype':'success','is_error':False,'result':'fixture answer','permission_denials':denials,'total_cost_usd':0,'usage':{}}))
'''
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'bin').mkdir();fake=root/'bin/claude';fake.write_text('#!'+sys.executable+'\nTOOLS='+repr(str(ROOT/'tools'))+'\n'+fake_source);fake.chmod(0o700)
   injected={'PATH':str(root/'bin')+os.pathsep+os.environ['PATH'],'CLAUDECODE':'1','CLAUDE_EFFORT':'max','CLAUDE_CODE_SESSION_ID':'parent','VSCODE_IPC_HOOK_CLI':'ide'}
   with patch.dict(os.environ,injected),patch.object(bench,'ROOT',root),patch.object(bench,'keychain_key',return_value='fake-test-credential'):
    for gid in ['A','B','D2']:
     for qid in ['first','next']:
      r=bench.execute_one({'id':qid,'question':'fixture question'},gid,cfg['groups'][gid],cfg,root/'out',10)
      self.assertEqual(r['status'],'ok',r.get('error'));self.assertEqual(r['search_attempts'],8);self.assertEqual(r['search_calls'],5);self.assertEqual(r['search_budget_denials'],3)
      self.assertEqual(len(r['searches']),5);self.assertEqual(len(r['budget_denials']),3)
      self.assertTrue(all(not d['billable'] and not d['results'] for d in r['budget_denials']))
      if gid!='A':self.assertAlmostEqual(r['search_cost_usd'],5*cfg['search_price_usd'])
      self.assertTrue((root/'out/jsonl'/gid/(qid+'.jsonl')).exists())
 def test_unaccounted_or_actual_sixth_search_is_invalid(self):
  events=[{'message':{'content':[{'type':'tool_use','name':'mcp__deepseek-search__search','id':str(i),'input':{'query':str(i)}}]}} for i in range(6)]
  with tempfile.TemporaryDirectory() as tmp:
   aux=Path(tmp)
   with self.assertRaises(common.BenchError):bench.audit_searches(events,{'search':'deepseek'},aux,[])
   rows=[{'call':i+1,'query':str(i),'status':'ok','results':[],'billable':False} for i in range(6)]
   common.write_text(aux/'search.jsonl',''.join(common.dumps(r)+'\n' for r in rows))
   with self.assertRaises(common.BenchError):bench.audit_searches(events,{'search':'deepseek'},aux,[])
 def test_failure_audit_adds_types_without_changing_model_error(self):
  for kind in ['network','schema']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'search.jsonl'
    class Opener:
     def open(self,request,timeout):
      if kind=='network':raise urllib.error.URLError(ConnectionResetError('fixture'))
      return io.BytesIO(b'{"unexpected":true}')
    with patch.dict(os.environ,{'BENCH_DEEPSEEK_KEY':'fixture-credential','BENCH_SEARCH_LOG':str(path)}),patch.object(deepseek_search.urllib.request,'build_opener',return_value=Opener()):
     result=deepseek_search.Search().call({'query':'fixture query'})
    self.assertTrue(result['isError']);self.assertEqual(result['content'][0]['text'],'搜索失败或响应无效。本次计入五次上限。')
    rows=common.load_jsonl(path);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'failed');self.assertFalse(rows[0]['billable'])
    if kind=='network':self.assertEqual(rows[0]['error_type'],'URLError');self.assertEqual(rows[0]['reason_type'],'ConnectionResetError')
    else:self.assertEqual(rows[0]['error_type'],'BenchError');self.assertEqual(rows[0]['error_detail'],'搜索响应缺少 results 数组。')
 def test_secret_pattern_does_not_match_inside_public_url_words(self):
  common.check_secret('https://example.org/newsdesk-katie-ledecky-world-record-800m')
  with self.assertRaises(common.BenchError):common.check_secret('token: sk-abcdefghijkl1234567890')
  with self.assertRaises(common.BenchError):common.check_secret('Authorization: Bearer abcdefghijkl1234567890')
  with self.assertRaises(common.BenchError):common.check_secret('prefixsk-abcdefghijkl1234567890',('sk-abcdefghijkl1234567890',))
 def test_server_success_is_billable_even_when_secret_guard_blocks_content(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'search.jsonl'
   class Opener:
    def open(self,request,timeout):return io.BytesIO(json.dumps({'results':[{'title':'fixture','url':'https://example.org','snippet':'fixture','summary':'fixture-credential'}]}).encode())
   with patch.dict(os.environ,{'BENCH_DEEPSEEK_KEY':'fixture-credential','BENCH_SEARCH_LOG':str(path)}),patch.object(deepseek_search.urllib.request,'build_opener',return_value=Opener()):result=deepseek_search.Search().call({'query':'fixture query'})
   self.assertTrue(result['isError']);self.assertNotIn('fixture-credential',path.read_text());row=common.load_jsonl(path)[0]
   self.assertEqual(row['status'],'failed');self.assertTrue(row['billable']);self.assertEqual(row['results'],[])
 def test_invalid_query_is_logged_and_model_can_correct_it(self):
  cfg=json.loads((ROOT/'tools/config.json').read_text())
  fake_source=r"""
import io,json,sys
sys.path.insert(0,TOOLS)
import deepseek_search
sys.stdin.read();name='mcp__deepseek-search__search';network=[]
class Opener:
 def open(self,request,timeout):
  network.append(1);return io.BytesIO(json.dumps({'results':[{'title':'fixture','url':'https://example.org','snippet':'s','summary':'s'}]}).encode())
deepseek_search.urllib.request.build_opener=lambda *args:Opener()
search=deepseek_search.Search();print(json.dumps({'type':'system','subtype':'init','tools':[name]}))
for i,query in enumerate(['x'*129,'valid query']):
 tid=str(i);print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','id':tid,'name':name,'input':{'query':query}}]}}))
 response=search.call({'query':query});print(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':tid,'is_error':response['isError'],'content':response['content']}]}}))
assert len(network)==1
print(json.dumps({'type':'result','subtype':'success','result':'fixture answer','usage':{}}))
"""
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'bin').mkdir();fake=root/'bin/claude';fake.write_text('#!'+sys.executable+'\nTOOLS='+repr(str(ROOT/'tools'))+'\n'+fake_source);fake.chmod(0o700)
   with patch.dict(os.environ,{'PATH':str(root/'bin')+os.pathsep+os.environ['PATH']}),patch.object(bench,'ROOT',root),patch.object(bench,'keychain_key',return_value='fixture-credential'):
    r=bench.execute_one({'id':'q','question':'fixture'},'B',cfg['groups']['B'],cfg,root/'out',10)
   self.assertEqual(r['status'],'ok',r.get('error'));self.assertEqual(r['search_calls'],1);self.assertEqual(r['search_attempts'],2);self.assertEqual(r['search_argument_rejections'],1);self.assertEqual(r['search_budget_denials'],0);self.assertAlmostEqual(r['search_cost_usd'],cfg['search_price_usd'])
 def test_valid_search_cannot_be_disguised_as_parameter_rejection(self):
  events=[{'message':{'content':[{'type':'tool_use','name':'mcp__deepseek-search__search','id':'x','input':{'query':'valid'}}]}},{'message':{'content':[{'type':'tool_result','tool_use_id':'x','is_error':True}]}}]
  with tempfile.TemporaryDirectory() as tmp:
   aux=Path(tmp);common.write_text(aux/'search.jsonl',common.dumps({'status':'invalid_arguments','input':{'query':'valid'},'query':'valid','call':None,'results':[],'billable':False})+'\n')
   with self.assertRaises(common.BenchError):bench.audit_searches(events,{'search':'deepseek'},aux,[])
 def test_real_search_failure_still_fails(self):
  events=[{'message':{'content':[{'type':'tool_use','name':'mcp__deepseek-search__search','id':'x','input':{'query':'q'}}]}}]
  with tempfile.TemporaryDirectory() as tmp:
   aux=Path(tmp);common.write_text(aux/'search.jsonl',common.dumps({'call':1,'query':'q','status':'failed','results':[],'billable':False})+'\n')
   with self.assertRaises(common.BenchError):bench.audit_searches(events,{'search':'deepseek'},aux,[])
if __name__=='__main__':unittest.main()
