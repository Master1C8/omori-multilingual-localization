// Temporary QA cache fixture and passive request evidence. Never shipped.
(function(){
 var rows=window.__qaFileRequests=[],requests=new WeakMap(),serial=0;
 var proto=XMLHttpRequest.prototype,open=proto.open,send=proto.send;
 function target(url){try{url=decodeURIComponent(String(url));}catch(ignore){}return /(?:^|\/)img\/(?:faces\/(?:01_OMORI_BATTLE|01_FA_OMORI_BATTLE)|system\/mailbox(?:Legend)?)\.(?:png|rpgmvp)(?:[?#].*)?$/.test(url);}
 proto.open=function(method,url){
  var result=open.apply(this,arguments);
  if(target(url)){
   var row={id:++serial,method:method,url:String(url),baseURI:document.baseURI,events:[]};
   requests.set(this,row);rows.push(row);if(rows.length>8)rows.shift();
  }
  return result;
 };
 proto.send=function(){
  var request=this,row=requests.get(this);
  function note(kind){try{
   if(requests.get(request)!==row)return;
   row.events.push({event:kind,time:Date.now(),readyState:request.readyState,status:request.status,
    onloadPresent:typeof request.onload==='function',responseBytes:request.readyState===4&&request.response&&request.response.byteLength||0});
   if(row.events.length>24)row.events.shift();
  }catch(error){row.diagnosticError=String(error);}}
  if(row){
   ['readystatechange','load','loadend','error','abort','timeout'].forEach(function(name){request.addEventListener(name,function(){note(name);});});
   note('before-send');
  }
  var result=send.apply(this,arguments);if(row)note('send-return');return result;
 };
 var status=window.__qaFileAssets={identity:'omori-file-face-prefetch-v1',phase:'waiting-title',assets:[],
  scope:'Native reserved image cache only; no scene, save or actor mutation; warm-cache capture, not cold-load verification'};
 var held=null,timer=setInterval(function(){try{
  if(status.phase==='ready'||status.phase==='error')return;
  if(!held){
   if(typeof SceneManager==='undefined'||!SceneManager._scene||SceneManager._scene.constructor.name!=='Scene_OmoriTitleScreen'||!SceneManager._sceneStarted)return;
   if(typeof ImageManager.reserveNormalBitmap!=='function')throw Error('Native image reservation API unavailable');
   status.requestedAt=Date.now();status.phase='loading';
   held=['img/faces/01_OMORI_BATTLE.png','img/faces/01_FA_OMORI_BATTLE.png'].map(function(url){return {url:url,bitmap:ImageManager.reserveNormalBitmap(url,0,'omori-file-face-qa')};});
  }
  status.assets=held.map(function(entry){var b=entry.bitmap,i=b._image,c=b.__canvas;return {url:entry.url,state:b._loadingState,width:i?i.naturalWidth:c&&c.width,height:i?i.naturalHeight:c&&c.height,imageComplete:i?i.complete:!!c};});
  if(status.assets.every(function(a){return a.state==='loaded'&&a.imageComplete&&a.width>0&&a.height>0;})){
   status.phase='ready';status.readyAt=Date.now();clearInterval(timer);
  }
 }catch(error){status.phase='error';status.error=String(error.stack||error);clearInterval(timer);}},100);
})();
