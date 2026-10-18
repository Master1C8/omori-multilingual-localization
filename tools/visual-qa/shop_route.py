"""First save -> mailbox buy menu -> Jacks; no item confirmation or purchase."""
import json,time,subprocess
from pathlib import Path
from collections import deque
from mari_route import MariRoute,win,ack,signature
from runtime import RUN,state,save,check_desktop,check_saves

def shop_navigation_ready(s,index=2):
 if not s or s.get('scene')!='Scene_OmoriItemShop' or not s.get('sceneStarted'):return False
 shop=s.get('shop') or {};listing=shop.get('list') or {};message=shop.get('message') or {};keeper=shop.get('shopkeeper') or {}
 return (shop.get('shopType')==0 and listing.get('active') and listing.get('index')==index
  and listing.get('openness')==255 and listing.get('visible') and listing.get('contentsOpacity')==255
  and [v['item']['id'] for v in shop.get('items',[])]==[14,47,78,85]
  and (shop.get('selected') or {}).get('id')==[14,47,78,85][index]
  and message.get('openness')==255 and message.get('visible')
  and not shop.get('moving') and not (shop.get('total') or {}).get('active')
  and (shop.get('total') or {}).get('openness')==0
  and keeper.get('visible') and keeper.get('opacity')==255 and keeper.get('bitmapReady'))

def shop_ready(s,index=2):
 if not shop_navigation_ready(s,index):return False
 message=s['shop']['message']
 return message.get('textState') is None and message.get('pause') is False

def mailbox_interaction_ready(s):
 if not s or s.get('scene')!='Scene_Map' or s.get('map',{}).get('interpreter',{}).get('eventId')!=24:return False
 message=win(s,'Window_Message')
 return bool(win(s,'Window_ChoiceList').get('active') or (message.get('openness')==255 and message.get('pause') and message.get('textState') is None))

def native_path(grid,start,goal):
 assert grid['mapId']==92 and (grid['player']['x'],grid['player']['y'])==start
 width,height=grid['width'],grid['height'];parents={start:None};queue=deque([start]);moves=[(2,0,1,125),(6,1,0,124),(8,0,-1,126),(4,-1,0,123)]
 while queue:
  x,y=queue.popleft()
  if (x,y)==goal:break
  for direction,dx,dy,key in moves:
   nx,ny=x+dx,y+dy
   if not(0<=nx<width and 0<=ny<height) or (nx,ny) in parents:continue
   if direction not in grid['directions'][y*width+x]:continue
   parents[(nx,ny)]=((x,y),key);queue.append((nx,ny))
 assert goal in parents,'Mailbox approach unavailable in actual native collision grid'
 result=[];v=goal
 while parents[v]:
  previous,key=parents[v];result.append((previous,v,key));v=previous
 result.reverse();assert len(result)<=100;return result

class ShopRoute(MariRoute):
 def shop(self):
  path=Path(json.loads((RUN/'owned-game.json').read_text())['statePath']+'.shop.json');v=json.loads(path.read_text());assert time.time()*1000-v['time']<3000,'Stale native shop observer';return v
 def shop_wait(self,predicate,timeout=90):
  end=time.monotonic()+timeout
  while True:
   v=self.shop()
   if predicate(v):return v
   assert time.monotonic()<end,'Expected native shop state unavailable: '+json.dumps(v)
   time.sleep(.1)
 def act(self,label,key,before,after,marker=None,timeout=45):
  if label=='continue':self.shop_wait(lambda s:(s.get('fileAssets') or {}).get('phase')=='ready' and (s.get('shopAssets') or {}).get('phase')=='ready',180)
  if label in ('continue','select-load','talk-mailbox'):return super().act(label,key,before,after,marker,timeout)
  check_desktop();check_saves();prior=self.wait(before,timeout);save(self.directory/(label+'-before.json'),prior)
  ack.pulse(self.pid,key,self.directory/(label+'-input.json'));result=self.wait(after,timeout)
  save(self.directory/(label+'-semantic-result.json'),result);self.steps.append(dict(action=label,key=key,guard='fresh exact native semantic state',resultScene=result['scene']));save(self.directory/'route.json',self.steps);return result
 def run(self):
  loaded=self.load_first_save();baseline=self.shop()['inventory'];save(self.directory/'loaded-inventory.json',baseline)
  target=next(e for e in loaded['map']['events'] if e['id']==24);assert (target['x'],target['y'])==(20,39)
  grid_path=Path(json.loads((RUN/'owned-game.json').read_text())['statePath']+'.shop-route-map.json');end=time.monotonic()+10
  while not grid_path.exists():assert time.monotonic()<end;time.sleep(.1)
  path=native_path(json.loads(grid_path.read_text()),(11,15),(20,41));path.append(((20,41),(20,40),126));save(self.directory/'planned-route.json',path)
  for (x,y),(nx,ny),key in path:
   self.act('walk-%s-%s-to-%s-%s'%(x,y,nx,ny),key,lambda s,x=x,y=y:self.map_at(s,x,y),lambda s,x=nx,y=ny:self.map_at(s,x,y))
  self.act('talk-mailbox',6,lambda s:self.map_at(s,20,40) and s['player']['direction']==8,mailbox_interaction_ready,timeout=90)
  # The original event offers Buy/Sell/Leave. Advance only complete dialogue;
  # refuse an unexpected choice list instead of guessing its meaning.
  for i in range(8):
   s=self.wait(mailbox_interaction_ready,90)
   choices=win(s,'Window_ChoiceList')
   if choices.get('active'):
    assert len(s['message']['choices'])==3 and choices['index']==0;break
   prior=signature(s)
   self.act('mailbox-dialogue-'+str(i),6,lambda s:mailbox_interaction_ready(s) and not win(s,'Window_ChoiceList').get('active'),lambda s:signature(s)!=prior or win(s,'Window_ChoiceList').get('active'))
  else:raise AssertionError('Mailbox Buy/Sell/Leave choice unavailable')
  self.act('choose-buy',6,lambda s:win(s,'Window_ChoiceList').get('active') and win(s,'Window_ChoiceList')['index']==0,lambda s:s['scene']=='Scene_OmoriItemShop' and shop_navigation_ready(self.shop(),0),timeout=180)
  for index in (0,1):
   self.act('shop-item-%s-to-%s'%(index,index+1),125,lambda s,i=index:s['scene']=='Scene_OmoriItemShop' and shop_navigation_ready(self.shop(),i),lambda s,i=index+1:s['scene']=='Scene_OmoriItemShop' and shop_navigation_ready(self.shop(),i))
  shop=self.shop_wait(shop_ready);assert shop['inventory']==baseline,'Shop view changed inventory/gold';assert shop['shop']['price']==25 and shop['shop']['owned']==0 and baseline['gold']==72
  path,_,window=self.frame('final-mailbox-jacks','mailbox-shop' if (RUN/'templates/mailbox-shop.png').exists() else None);after=self.shop();assert shop_ready(after) and after['inventory']==baseline
  native=json.loads(subprocess.check_output([str(RUN/'native-control'),str(self.pid),'state']));assert not native['targetActive'] and native['frontmostPid']!=self.pid
  return dict(frame=str(path),window=window,state=state(),gameplay=self.read(),shopEvidence=after,inputMethod='game-thread-dom-bridge',nativeFocusAtCapture=native,actions=len(self.steps),saveSlotLoaded=1,saveSlotsWritten=False,inventoryChanged=False,purchaseConfirmed=False,reference='20261018-sixth-reference',originalEventId=24)
