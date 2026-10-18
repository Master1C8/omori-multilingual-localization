// Read-only gameplay evidence. Never calls load, save, movement or event APIs.
(function(){
 var fs=require('fs'),path=__STATE_PATH__+'.mari.json';
 setInterval(function(){try{
  var s=SceneManager._scene,p=typeof $gamePlayer!=='undefined'&&$gamePlayer,m=typeof $gameMap!=='undefined'&&$gameMap;
  var windows=[];
  function inspect(w,depth){
   if(!w||depth>4)return;
   if(w.constructor&&/^Window_/.test(w.constructor.name))windows.push({type:w.constructor.name,visible:w.visible,openness:w.openness,active:w.active,index:w._index,text:w._text,list:w._list&&w._list.map(function(c){return {name:c.name,symbol:c.symbol,enabled:c.enabled};}),textState:w._textState&&{index:w._textState.index,text:w._textState.text},pause:w.pause,opening:w._opening,x:w.x,y:w.y,width:w.width,height:w.height,contentsOpacity:w.contentsOpacity,actorId:w._actor&&w._actor.actorId&&w._actor.actorId(),actorIndex:w._actorIndex,helpItem:w._item&&{id:w._item.id,name:w._item.name,description:w._item.description},contents:w.contents&&{width:w.contents.width,height:w.contents.height}});
   if(w.children)w.children.forEach(function(c){inspect(c,depth+1);});
  }
  inspect(s,0);
  var ready=m&&m._interpreter,v={time:Date.now(),scene:s&&s.constructor.name,sceneStarted:SceneManager._sceneStarted,fadeDuration:s&&s._fadeDuration,file:s&&{index:s._saveIndex,canSelect:s._canSelect,command:s._commandWindow&&s._commandWindow._index,prompt:s._promptWindow&&s._promptWindow._index},player:ready&&p&&{x:p.x,y:p.y,direction:p.direction(),moving:p.isMoving(),canMove:p.canMove()},map:ready&&{id:m.mapId(),running:m.isEventRunning(),events:m.events().map(function(e){return {id:e.eventId(),name:e.event().name,x:e.x,y:e.y,page:e._pageIndex};}),interpreter:m._interpreter&&{index:m._interpreter._index,eventId:m._interpreter._eventId,code:m._interpreter._list&&m._interpreter.currentCommand()&&m._interpreter.currentCommand().code}},message:typeof $gameMessage!=='undefined'&&$gameMessage&&{texts:$gameMessage._texts,choices:$gameMessage._choices,busy:$gameMessage.isBusy()},windows:windows};
  var actor=typeof $gameParty!=='undefined'&&$gameParty&&$gameParty.members()[0];
  v.firstActor=actor&&{id:actor.actorId(),name:actor.name(),equips:actor.equips().map(function(e){return e&&{id:e.id,name:e.name,description:e.description};})};
  var equip=s&&s._actorEquipWindow,item=equip&&equip.equipmentAtIndex&&equip.equipmentAtIndex();
  v.equipment=equip&&{actorId:equip.actor()&&equip.actor().actorId(),actorIndex:equip._actorIndex,slotIndex:equip.index(),item:item&&{id:item.id,name:item.name,description:item.description},moving:s.move&&s.move.isMoving()};
  fs.writeFileSync(path+'.tmp',JSON.stringify(v));fs.renameSync(path+'.tmp',path);
 }catch(e){try{fs.writeFileSync(path+'.error',String(e.stack||e));}catch(ignore){}}},250);
})();
