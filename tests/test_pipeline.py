import json,unittest
from pathlib import Path
from stoic_shorts.pipeline import select
class PipelineTests(unittest.TestCase):
 def test_scripts_schema(self):
  bank=json.loads((Path(__file__).parents[1]/'content/scripts.json').read_text())
  self.assertGreaterEqual(len(bank),5)
  for x in bank:
   for k in ('id','title','hook','scenes','narration','source'):self.assertIn(k,x)
 def test_same_day_rotation(self):
  bank=json.loads((Path(__file__).parents[1]/'content/scripts.json').read_text());first=bank[0]
  chosen=select('2026-01-01',{'videos':[{'date':'2026-01-01','script_id':first['id']}]})
  self.assertNotEqual(chosen['id'],first['id'])
if __name__=='__main__':unittest.main()
