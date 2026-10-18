"""Learned first-save to Mari advice route. Native input and Oculix guards only."""
import json,time,subprocess,importlib.util
from pathlib import Path
from runtime import RUN,state,save,check_desktop,check_saves
from vision import Vision
spec=importlib.util.spec_from_file_location('ack_input',Path(__file__).with_name('ack-input.py'))
ack=importlib.util.module_from_spec(spec);spec.loader.exec_module(ack)

def win(s,name):return next((w for w in s['windows'] if w['type']==name),{})
def signature(s):
 w=win(s,'Window_Message')
 return json.dumps([s['scene'],s.get('message'),w.get('pause'),w.get('textState')],sort_keys=True)

class MariRoute:
 def __init__(self,pid,directory):
  self.pid=pid;self.directory=Path(directory);self.v=Vision(directory);self.steps=[]
  owned=json.loads((RUN/'owned-game.json').read_text());self.game_path=Path(owned['statePath']+'.mari.json')
 def read(self):
  s=json.loads(self.game_path.read_text());base=state(allow_stale=True)
  assert not base.get('visibleError') and not base.get('engineStopped'),base
  ready=s.get('sceneStarted',True) and not s.get('fadeDuration',0)
  return s if ready and time.time()*1000-s['time']<3000 and time.time()*1000-base['time']<3000 else None
 def wait(self,predicate,timeout=45):
  end=time.monotonic()+timeout
  while True:
   s=self.read()
   if s and predicate(s):return s
   if time.monotonic()>=end:
    raw=json.loads(self.game_path.read_text());base=state(allow_stale=True)
    detail={k:raw.get(k) for k in ['scene','sceneStarted','fadeDuration','player']}
    detail['assets']=base.get('assetReadiness');detail['stateAgeSeconds']=round(time.time()-base['time']/1000,1)
    raise AssertionError('Expected state unavailable: '+json.dumps(detail))
   time.sleep(.1)
 def frame(self,label,marker=None):
  if marker:
   # Scene objects can be ready before WindowServer presents their first frame.
   # Wait for the actual visual marker as well as the fresh runtime scene.
   expected=self.wait(lambda s:bool(s['scene']))['scene']
   path,_,m,w=self.v.require(self.pid,marker,expected,30)
  else:path,_,w=self.v.capture(self.pid,label);m=None
  return path,m,w
 def act(self,label,key,before,after,marker=None,timeout=45):
  check_desktop();check_saves();s=self.wait(before,timeout)
  path,m,w=self.frame(label+'-before',marker);save(self.directory/(label+'-before.json'),s)
  assert before(self.read()),'Screen changed between recognition and input'
  native=ack.pulse(self.pid,key,self.directory/(label+'-input.json'))
  result=self.wait(after,timeout)
  save(self.directory/(label+'-semantic-result.json'),result)
  post,_,_=self.frame(label+'-after')
  save(self.directory/(label+'-after.json'),result)
  self.steps.append({'action':label,'key':key,'beforeFrame':str(path),'afterFrame':str(post),'marker':m,'resultScene':result['scene']})
  save(self.directory/'route.json',self.steps);return result
 def map_at(self,s,x,y):
  return s['scene']=='Scene_Map' and s['map']['id']==92 and s['player']['x']==x and s['player']['y']==y and not s['player']['moving'] and s['player']['canMove']
 def dialogue_ready(self,s):
  w=win(s,'Window_Message')
  return s['scene']=='Scene_Map' and s['message']['busy'] and w.get('openness')==255 and (w.get('pause') or w.get('textState') is not None)
 def load_first_save(self):
  title,t,_,_=self.v.require(self.pid,'title-logo','Title',180)
  end=time.monotonic()+30
  while not t.get('active'):
   assert time.monotonic()<end,'Title controls never became interactive'
   time.sleep(.2);title,t,_,_=self.v.require(self.pid,'title-logo','Title',5)
  assert t['active'] and t['canContinue']
  if t['index']!=1:
   assert t['index'] in [0,2]
   ack.pulse(self.pid,124 if t['index']==0 else 123,self.directory/'title-selection-input.json')
   title,t,_,_=self.v.require(self.pid,'title-logo','Title',10)
  assert t['index']==1
  self.act('continue',6,lambda s:s['scene']=='Scene_OmoriTitleScreen' and state()['active'] and state()['index']==1,lambda s:s['scene']=='Scene_OmoriFile' and s['file']['command']==1,'title-logo')
  self.act('select-load',6,lambda s:s['scene']=='Scene_OmoriFile' and not s['file']['canSelect'] and s['file']['command']==1,lambda s:s['file'].get('canSelect') is True,'load-portrait')
  s=self.read();index=s['file']['index'];assert 0<=index<=5
  for n in range(index,0,-1):
   self.act('slot-'+str(n)+'-to-'+str(n-1),126,lambda s,n=n:s['scene']=='Scene_OmoriFile' and s['file']['index']==n and s['file']['canSelect'],lambda s,n=n:s['file'].get('index')==n-1,'load-portrait')
  self.act('first-slot-prompt',6,lambda s:s['file'].get('index')==0 and s['file']['canSelect'] and s['file']['command']==1,lambda s:win(s,'Window_OmoriFilePrompt').get('active') and win(s,'Window_OmoriFilePrompt').get('openness')==255 and s['file']['prompt']==1,'load-portrait')
  self.act('choose-load-yes',126,lambda s:s['file']['command']==1 and s['file']['prompt']==1 and win(s,'Window_OmoriFilePrompt').get('active') and win(s,'Window_OmoriFilePrompt').get('openness')==255,lambda s:s['file'].get('prompt')==0 and win(s,'Window_OmoriFilePrompt').get('active'))
  self.act('load-first-save',6,lambda s:s['file'].get('index')==0 and s['file']['command']==1 and s['file']['prompt']==0 and win(s,'Window_OmoriFilePrompt').get('active'),lambda s:self.map_at(s,11,15),timeout=240)
  return self.read()
 def run(self):
  self.load_first_save()
  s=self.read();mari=next(e for e in s['map']['events'] if e['id']==6);assert (mari['x'],mari['y'],mari['page'])==(13,16,2),mari
  self.act('walk-down',125,lambda s:self.map_at(s,11,15),lambda s:self.map_at(s,11,16),'mari-picnic')
  self.act('walk-right',124,lambda s:self.map_at(s,11,16),lambda s:self.map_at(s,12,16) and s['player']['direction']==6,'mari-picnic')
  self.act('talk-mari',6,lambda s:self.map_at(s,12,16),lambda s:self.dialogue_ready(s),'mari-picnic')
  talks=1
  for i in range(40):
   s=self.wait(lambda s:s['scene']=='Scene_OmoriQuest' or self.dialogue_ready(s) or self.map_at(s,12,16),60)
   if s['scene']=='Scene_OmoriQuest':break
   if self.map_at(s,12,16):
    assert talks==1,'Unexpected repeated conversation end';talks=2
    self.act('talk-mari-again',6,lambda s:self.map_at(s,12,16),lambda s:self.dialogue_ready(s),'mari-picnic');continue
   assert not win(s,'Window_ChoiceList').get('active'),'Unexpected conversation choice'
   prior=signature(s)
   self.act('dialogue-'+str(i),6,self.dialogue_ready,lambda s:signature(s)!=prior,'mari-message-frame')
  else:raise RuntimeError('Quest scene not reached within guarded dialogue bound')
  s=self.wait(lambda s:s['scene']=='Scene_OmoriQuest' and win(s,'Window_OmoriQuestTypes').get('active'))
  types=win(s,'Window_OmoriQuestTypes');quests=win(s,'Window_OmoriQuestList')
  assert types['index']==0 and [v['symbol'] for v in types['list']]==['incomplete','complete']
  assert len(quests['list'])==2 and all(v['symbol']=='quest' for v in quests['list'])
  self.act('select-incomplete',6,lambda s:win(s,'Window_OmoriQuestTypes').get('active') and win(s,'Window_OmoriQuestTypes')['index']==0,lambda s:win(s,'Window_OmoriQuestList').get('active') and win(s,'Window_OmoriQuestList')['index']==0,'mari-quest-frame')
  self.act('open-basil-advice',6,lambda s:win(s,'Window_OmoriQuestList').get('active') and win(s,'Window_OmoriQuestList')['index']==0,lambda s:win(s,'Window_OmoriQuestMessage').get('openness')==255 and win(s,'Window_OmoriQuestMessage').get('textState') is None,'mari-quest-frame')
  time.sleep(1);path,m,w=self.frame('final-mari-quests','mari-quests-portrait');s=self.read()
  assert s['scene']=='Scene_OmoriQuest' and win(s,'Window_OmoriQuestList')['index']==0
  return {'frame':str(path),'marker':m,'window':w,'state':state(),'gameplay':s,'actions':len(self.steps),'saveSlotLoaded':1,'saveSlotsWritten':False,'backgroundMode':'Temporary native focus-pause adapter and Chromium occlusion flags; no activation calls'}
 def close(self):self.v.close()
