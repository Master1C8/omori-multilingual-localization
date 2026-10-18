// Passive native shop evidence; no scene, movement, inventory or save mutation.
(function(){
 var fs=require('fs'),prefix=__STATE_PATH__,gridWritten=false,helpHooks=false,helpSerial=0,helpProof;
 function item(v){return v&&{id:v.id,name:v.name,description:v.description,iconIndex:v.iconIndex};}
 function windowState(w){return w&&{type:w.constructor.name,active:w.active,visible:w.visible,openness:w.openness,index:w._index,x:w.x,y:w.y,width:w.width,height:w.height,contentsOpacity:w.contentsOpacity,textState:w._textState&&{text:w._textState.text,index:w._textState.index},pause:w.pause,contents:w.contents&&{width:w.contents.width,height:w.contents.height,fontFace:w.contents.fontFace,fontSize:w.contents.fontSize}};}
 function write(path,v){fs.writeFileSync(path+'.tmp',JSON.stringify(v));fs.renameSync(path+'.tmp',path);}
 setInterval(function(){try{
  if(!helpHooks&&typeof WindowItemShopMessage!=='undefined'){
   helpHooks=true;var proto=WindowItemShopMessage.prototype,draw=proto.drawItem,page=proto.newPage;
   proto.drawItem=function(value){if(value)helpProof={serial:++helpSerial,itemId:value.id,newPages:0,pages:[]};return draw.apply(this,arguments);};
   proto.newPage=function(text){var result=page.apply(this,arguments);if(helpProof){helpProof.newPages++;helpProof.pages.push({index:text.index,y:text.y,height:text.height,fontSize:this.contents.fontSize});}return result;};
  }
  var s=SceneManager._scene,p=typeof $gameParty!=='undefined'&&$gameParty,m=typeof $gameMap!=='undefined'&&$gameMap,player=typeof $gamePlayer!=='undefined'&&$gamePlayer;
  var v={time:Date.now(),scene:s&&s.constructor.name,sceneStarted:SceneManager._sceneStarted,inventory:p&&{gold:p.gold(),items:p.allItems().map(function(i){return {id:i.id,kind:DataManager.isItem(i)?'item':DataManager.isWeapon(i)?'weapon':'armor',count:p.numItems(i)};})},fileAssets:window.__qaFileAssets,fileRequests:window.__qaFileRequests,shopAssets:window.__qaShopAssets};
  if(v.scene==='Scene_Map'&&v.sceneStarted&&m.mapId()===92&&player.canMove()&&!m.isEventRunning()&&!gridWritten){
   var cells=[];for(var y=0;y<m.height();y++)for(var x=0;x<m.width();x++)cells.push([2,4,6,8].filter(function(d){return player.canPass(x,y,d);}));
   write(prefix+'.shop-route-map.json',{time:Date.now(),mapId:92,width:m.width(),height:m.height(),player:{x:player.x,y:player.y},directions:cells,method:'Passive native Game_Player.canPass; current event collisions, no movement'});gridWritten=true;
  }
  if(v.scene==='Scene_OmoriItemShop'){
   var list=s._itemListWindow,selected=list&&list.item(),data=$gameTemp._shopData,k=s._shopKeeperSprite;
   v.shop={key:data&&data.name,shopType:data&&data.shopType,goods:data&&data.goods,list:windowState(list),items:list&&list._data.map(function(row,i){return {item:item(row.item),price:list.price(i)};}),selected:item(selected),price:list&&list.price(),owned:selected&&p.numItems(selected),header:windowState(s._shopHeaderWindow),gold:windowState(s._goldWindow),message:windowState(s._messageWindow),total:windowState(s._totalWindow),descriptionDrawProof:helpProof,moving:s.move&&s.move.isMoving(),shopkeeper:k&&{visible:k.visible,opacity:k.opacity,bitmapReady:k.bitmap&&k.bitmap.isReady(),width:k.width,height:k.height}};
  }
  write(prefix+'.shop.json',v);
 }catch(error){try{write(prefix+'.shop.error.json',{time:Date.now(),error:String(error.stack||error)});}catch(ignore){}}},250);
})();
