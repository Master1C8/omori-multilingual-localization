"""First save -> original playground jack-in-the-box dialogue and native SINV proof."""
import json,time,subprocess
from pathlib import Path
from mari_route import MariRoute,win,ack
from runtime import RUN,state,save,check_desktop,check_saves


TEXT_REGION=(20,752,1258,890)
def native_text_changed(first,second):
 from PIL import ImageChops
 return bool(ImageChops.difference(first.convert('RGB').crop(TEXT_REGION),second.convert('RGB').crop(TEXT_REGION)).getbbox())

def wave_ready(s):
 return (s and s.get('complete') and s.get('openness')==255
         and any(e['name']=='SINV' and e['active'] and e['amplitude'] for e in s.get('effects') or [])
         and len(s.get('sprites') or [])>=2
         and max(p.get('anchorY',0) for p in s['sprites'])-min(p.get('anchorY',0) for p in s['sprites'])>1e-5)

class WaveRoute(MariRoute):
 def act(self,label,key,before,after,marker=None,timeout=45):
  if label=='continue':
   deadline=time.monotonic()+90
   while True:
    fixture=self.wave().get('fileAssets') or {}
    if fixture.get('phase')=='error':raise RuntimeError(fixture.get('error'))
    if fixture.get('phase')=='ready':break
    assert time.monotonic()<deadline,'Native save-list portrait cache did not decode: '+json.dumps(self.wave())
    time.sleep(.1)
  if label in ('continue','select-load','open-joker-jash'):
   return super().act(label,key,before,after,marker,timeout)
  # Fresh exact runtime scene/window/map fields guard the remaining native keys.
  # Preserve every input acknowledgement and semantic result without redundant
  # full-resolution diagnostic captures between adjacent map tiles.
  check_desktop();check_saves();prior=self.wait(before,timeout)
  save(self.directory/(label+'-before.json'),prior)
  ack.pulse(self.pid,key,self.directory/(label+'-input.json'))
  result=self.wait(after,timeout);save(self.directory/(label+'-semantic-result.json'),result)
  self.steps.append(dict(action=label,key=key,guard='fresh exact native semantic state',resultScene=result['scene']))
  save(self.directory/'route.json',self.steps);return result
 def wave(self):
  p=Path(json.loads((RUN/'owned-game.json').read_text())['statePath']+'.wave.json')
  v=json.loads(p.read_text());assert time.time()*1000-v['time']<3000,'Stale wave observer';return v
 def run(self):
  self.load_first_save()
  target=next(e for e in self.read()['map']['events'] if e['id']==18)
  assert (target['x'],target['y'])==(24,28),target
  # Follow the open central approach, then face the original event from its left.
  x,y=11,15
  for key,dx,dy,n in [(125,0,1,5),(124,1,0,10),(125,0,1,8),(123,-1,0,2),(124,1,0,4)]:
   for _ in range(n):
    nx,ny=x+dx,y+dy
    self.act('walk-%s-%s-to-%s-%s'%(x,y,nx,ny),key,
      lambda s,x=x,y=y:self.map_at(s,x,y),
      lambda s,x=nx,y=ny:self.map_at(s,x,y))
    x,y=nx,ny
  current=self.read();page=next(e['page'] for e in current['map']['events'] if e['id']==18)
  assert page in (3,4),'Unexpected first-save Jash state: '+str(page)
  if page==4:
   self.act('close-initially-open-jash',6,lambda s:self.map_at(s,23,28) and s['player']['direction']==6,
    lambda s:self.map_at(s,23,28) and next(e['page'] for e in s['map']['events'] if e['id']==18)==3,timeout=60)
  self.act('open-joker-jash',6,lambda s:self.map_at(s,23,28) and s['player']['direction']==6,
    lambda s:self.dialogue_ready(s) and s['map']['interpreter']['eventId']==18,timeout=60)
  end=time.monotonic()+60
  while not wave_ready(self.wave()):
   assert time.monotonic()<end,'Complete animated SINV dialogue unavailable';time.sleep(.1)
  s=self.read();assert self.dialogue_ready(s) and s['map']['interpreter']['eventId']==18
  samples=[];frames=[]
  for i in range(3):
   sample=self.wave();assert wave_ready(sample)
   path,_,window=self.frame('wave-phase-'+str(i));samples.append(sample);frames.append(str(path));time.sleep(.22)
  assert len({tuple(p['anchorY'] for p in v['sprites']) for v in samples})>1,'Wave sprite anchors did not animate'
  assert len({tuple(v['texts']) for v in samples})==1,'Dialogue changed during wave proof'
  from PIL import Image
  with Image.open(frames[0]) as first,Image.open(frames[1]) as second:
   assert native_text_changed(first,second),'Native dialogue pixels did not animate'
  native=json.loads(subprocess.check_output([str(RUN/'native-control'),str(self.pid),'state']))
  assert not native['targetActive'] and native['frontmostPid']!=self.pid
  save(self.directory/'wave-proof.json',dict(samples=samples,nativeFrames=frames,nativeDialoguePixelsChanged=True))
  return dict(frame=frames[-1],window=window,state=state(),gameplay=self.read(),actions=len(self.steps),
    waveProof=str(self.directory/'wave-proof.json'),inputMethod='game-thread-dom-bridge',nativeFocusAtCapture=native,
    saveSlotLoaded=1,saveSlotsWritten=False,reference='20261018-fifth-reference',originalEventId=18)
