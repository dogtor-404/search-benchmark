import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import resources
from common import BenchError
class ResourceTests(unittest.TestCase):
 def test_multibyte_text_excludes_json_wrapper(self):
  self.assertEqual(resources.text_size('中文a'),{'characters':3,'utf8_bytes':7})
  self.assertEqual(resources.text_size([{'type':'text','text':'中'},{'type':'text','text':'文a'}]),{'characters':3,'utf8_bytes':7})
 def test_duplicate_results_not_counted_twice_and_errors_excluded(self):
  blocks=[{'type':'tool_use','id':'ok','name':'WebSearch'},{'type':'tool_use','id':'err','name':'WebSearch'},{'type':'tool_result','tool_use_id':'ok','content':'中文a'},{'type':'tool_result','tool_use_id':'err','content':'failure','is_error':True}]
  events=[{'message':{'content':blocks}},{'message':{'content':[blocks[2]]}}]
  self.assertEqual(resources.returns(events),[{'tool_use_id':'ok','characters':3,'utf8_bytes':7}])
  events.append({'message':{'content':[dict(blocks[2],content='different')]}})
  with self.assertRaises(BenchError):resources.returns(events)
 def test_cached_tokens_included_once_and_unverified_provider_not_summed(self):
  usage={'inputTokens':2,'cacheReadInputTokens':300,'cacheCreationInputTokens':100,'outputTokens':20,'thinkingTokens':5}
  self.assertEqual(resources.token_fields(usage,True)['total_input_tokens'],402)
  self.assertIsNone(resources.token_fields(usage)['total_input_tokens'])
  self.assertEqual(resources.token_fields(usage,True)['outputTokens'],20)
  with self.assertRaises(BenchError):resources.token_fields({})
if __name__=='__main__':unittest.main()
