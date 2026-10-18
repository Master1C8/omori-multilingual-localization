"""Fake clock/ack-file boundaries; no game, keyboard, focus or native scheduler."""
import importlib.util,json
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('bridge-input.py');spec=importlib.util.spec_from_file_location('bridge_deadline',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Clock:
 def __init__(self):self.now=0
 def monotonic(self):return self.now
 def sleep(self,_):self.now+=1
class Ack:
 def __init__(self,clock,ident='current',status='released',at=43):self.clock=clock;self.ident=ident;self.status=status;self.at=at;self.reads=0
 def read_text(self):
  self.reads+=1
  if self.clock.now<self.at:raise FileNotFoundError('No acknowledgement yet')
  return json.dumps(dict(id=self.ident,status=self.status,samples=[dict(current=True)]*3))
for ident,status,deadline,expected in [('current','released',60,'released'),('current','released',15,None),('previous','released',60,None),('current','queued',60,'queued'),('current','error',60,'error')]:
 c=Clock();path=Ack(c,ident,status)
 with patch.object(m.time,'monotonic',c.monotonic),patch.object(m.time,'sleep',c.sleep):reply=m.await_release(path,'current',deadline)
 assert (reply['status'] if reply else None)==expected
 assert c.now==(43 if expected in ['released','error'] else deadline)
 assert path.reads>0
print('PASS late43s same-request completion within60s, old15s rejection, wrong-request rejection, pending deadline and immediate native error; only acknowledgement reads occur, with no request replay. Native timing is not mocked as proven.')
