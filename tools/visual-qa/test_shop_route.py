"""State-boundary fixtures, not proof of native navigation or rendering."""
import copy
from shop_route import shop_ready,shop_navigation_ready,native_path,mailbox_interaction_ready
s=dict(scene='Scene_OmoriItemShop',sceneStarted=True,shop=dict(shopType=0,list=dict(active=True,index=2,openness=255,visible=True,contentsOpacity=255),items=[dict(item=dict(id=i)) for i in [14,47,78,85]],selected=dict(id=78),message=dict(openness=255,visible=True,textState=None,pause=False),total=dict(active=False,openness=0),moving=False,shopkeeper=dict(visible=True,opacity=255,bitmapReady=True)))
assert shop_ready(s)
paused=copy.deepcopy(s);paused['shop']['message'].update(textState=dict(index=55),pause=True)
assert shop_navigation_ready(paused) and not shop_ready(paused)
paused['shop']['list']['active']=False;assert not shop_navigation_ready(paused)
paused=copy.deepcopy(s);paused['shop']['message']['pause']=True;assert not shop_ready(paused)
for section,key,value in [('list','index',1),('list','active',False),('list','openness',128),('message','textState',{'index':3}),('total','active',True),('total','openness',255),('selected','id',47),('shopkeeper','bitmapReady',False)]:
 v=copy.deepcopy(s);v['shop'][section][key]=value;assert not shop_ready(v),(section,key)
v=copy.deepcopy(s);v['shop']['shopType']=1;assert not shop_ready(v)
v=copy.deepcopy(s);v['shop']['items'][2]['item']['id']=79;assert not shop_ready(v)
v=copy.deepcopy(s);v['shop']['selected']=None;assert not shop_ready(v)
grid=dict(mapId=92,player=dict(x=0,y=0),width=3,height=2,directions=[[6],[2],[],[],[6],[]])
path=native_path(grid,(0,0),(2,1));assert path==[((0,0),(1,0),124),((1,0),(1,1),125),((1,1),(2,1),124)]
blocked=copy.deepcopy(grid);blocked['directions'][1]=[]
try:native_path(blocked,(0,0),(2,1))
except AssertionError as error:assert 'approach unavailable' in str(error)
else:raise AssertionError('Blocked native edge accepted')
print('PASS selected item/goods, completed description, active list, hidden purchase window, ready artwork and native directed collision path boundaries. Native capture/review still required.')
dialogue=dict(scene='Scene_Map',map=dict(interpreter=dict(eventId=24)),windows=[dict(type='Window_Message',openness=255,pause=False,textState=dict(index=4)),dict(type='Window_ChoiceList',active=False)])
assert not mailbox_interaction_ready(dialogue)
complete=copy.deepcopy(dialogue);complete['windows'][0].update(pause=True,textState=None);assert mailbox_interaction_ready(complete)
choice=copy.deepcopy(dialogue);choice['windows'][0].update(textState=None);choice['windows'][1]['active']=True;assert mailbox_interaction_ready(choice)
wrong=copy.deepcopy(choice);wrong['map']['interpreter']['eventId']=18;assert not mailbox_interaction_ready(wrong)
print('PASS typewriter rejects incomplete greeting; native automatic transition to choices passes without requiring a stale dialogue pause; unrelated event rejected.')
