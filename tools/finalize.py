#!/usr/bin/env python3
"""仅在完整运行、双判分和人工复核后归档；不执行任何公开或推送。"""
import argparse,datetime,json,shutil,sys
from common import ROOT,BenchError,check_secret,sha256
from analyze import analyze

def finalize(execute=False):
 out=ROOT/'tmp/archive';manifest=json.loads((out/'manifest.json').read_text())
 if manifest['phase']!='full' or len(manifest['question_ids'])!=100 or len(manifest['all_groups'])!=10:raise BenchError('只允许归档完整十组、100 道题的正式运行。')
 if manifest['question_sha256']!=sha256(ROOT/'questions/questions.jsonl'):raise BenchError('题库已变化。')
 analyze(out)
 for g in manifest['all_groups']:
  for qid in manifest['question_ids']:
   path=out/'jsonl'/g/(qid+'.jsonl')
   if not path.exists() or not path.stat().st_size:raise BenchError('有原始输出缺失。')
 for path in out.rglob('*'):
  if path.is_file():check_secret(path.read_text())
 date=datetime.datetime.fromisoformat(manifest['started_at']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
 dest=ROOT/'results'/date
 if dest.exists():raise BenchError('目标日期目录已存在，拒绝覆盖。')
 print('归档检查通过：'+str(dest))
 if execute:
  dest.parent.mkdir(exist_ok=True);shutil.move(str(out),str(dest));shutil.copyfile(ROOT/'questions/LICENSE',dest/'LICENSE');shutil.copyfile(ROOT/'questions/NOTICE',dest/'NOTICE')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
 try:finalize(a.execute)
 except (BenchError,FileNotFoundError) as e:print('停止：'+str(e),file=sys.stderr);sys.exit(1)
