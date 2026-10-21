import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from email.message import Message
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import multilingual as m
import build_multilingual as b
from common import BenchError
class MultilingualTests(unittest.TestCase):
 def test_same_six_native_questions_without_gold_leak(self):
  rows=[{'id':f'{l}-{i}','lang':l,'question':f'คำถาม-{l}-{i}','answer':'SECRET GOLD','aliases':['SECRET ALIAS'],'source_urls':['https://gold.example/source'],'review':{'status':'verified'}} for l in b.LANGS for i in range(20)]
  with patch.object(m,'load_jsonl',return_value=rows):
   first=m.questions('pilot');second=m.questions('pilot')
  self.assertEqual(first,second);self.assertEqual({q['lang'] for q in first},set(b.LANGS));self.assertEqual(len(first),6)
  payload=m.bench.prompt(first[0],{'search':'deepseek'},{'search_prompt':'原提示词'})
  self.assertIn('คำถาม',payload);self.assertNotIn('SECRET',payload);self.assertNotIn('gold.example',payload)
 def test_wrong_quota_stops_before_any_model_call(self):
  with patch.object(m,'load_jsonl',return_value=[]),self.assertRaises(BenchError):m.questions('full')
 def test_six_reviewed_questions_only_allow_pilot(self):
  rows=[{'id':l,'lang':l,'question':'原文'+l,'source_urls':['https://example.org/'+l],'review':{'status':'verified'}} for l in b.LANGS]
  with patch.object(m,'load_jsonl',return_value=rows):
   self.assertEqual(m.questions('pilot'),rows)
   with self.assertRaises(BenchError):m.questions('full')
 def test_uncertain_never_counts_as_binary_vote(self):
  self.assertIsNone(m.majority(['correct','incorrect','uncertain']))
  self.assertIsNone(m.majority(['uncertain','uncertain','incorrect']))
  self.assertEqual(m.majority(['correct','correct','uncertain']),'correct')
  self.assertEqual(m.majority(['incorrect','correct','incorrect']),'incorrect')
 def test_source_urls_are_cleaned_without_search_pages(self):
  self.assertEqual(b.urls('https://cn.bing.com/search?q=x'),[])
  self.assertEqual(b.urls('《书名》'),[])
  self.assertEqual(b.urls('https://ru.wikipedia.org/wiki/'),[])
  self.assertEqual(b.urls('https://a.example/page#anchor,https://b.example/next?utm_source=x&n=2'),['https://a.example/page','https://b.example/next?n=2'])
 def test_native_sampling_deterministic_and_all_candidates_retained(self):
  rows=[{'id':f'{l}{i}','language':l+'-XX'} for l in b.LANGS for i in range(22)]
  order=b.ordered(rows)
  self.assertEqual(order,b.ordered(rows));self.assertEqual(len(order),len(rows));self.assertEqual(len({r['id'] for r in order}),len(rows))
 def test_long_page_keeps_padded_poem_number_evidence(self):
  text='网页前言'*12000+' 後拾遺集 巻十：哀傷 00536 よもすから−ちきりしことを−わすれすは '
  self.assertIn('00536',b.extract(text,'後拾遺和歌集 巻第十「哀傷」536番','「よもすから ちきりしことを わすれすは」の出典は？'))
 def test_invalid_charset_header_does_not_hide_readable_source(self):
  class Response:
   status=200;url='https://example.org/source'
   headers=Message();headers['Content-Type']='text/html; charset=none'
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,n):return ('<meta charset="utf-8"><p>'+'有意义的原文资料。'*40+'</p>').encode()
  with tempfile.TemporaryDirectory() as d,patch.object(b,'CACHE',Path(d)),patch.object(b.urllib.request,'urlopen',return_value=Response()):
   self.assertEqual(b.fetch(Response.url)['status'],'fetched')
if __name__=='__main__':unittest.main()
