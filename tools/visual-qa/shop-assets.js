// Temporary native reserved-cache fixture; no callbacks or game state replaced.
(function(){
 var status=window.__qaShopAssets={identity:'omori-shop-mailbox-prefetch-v1',phase:'waiting-title',assets:[],scope:'Reserved original mailbox image cache; warm-cache capture only'},held;
 var timer=setInterval(function(){try{
  if(!held){
   if(typeof SceneManager==='undefined'||!SceneManager._scene||SceneManager._scene.constructor.name!=='Scene_OmoriTitleScreen'||!SceneManager._sceneStarted)return;
   held=['mailbox','mailboxLegend'].map(function(name){return {name:name,bitmap:ImageManager.reserveSystem(name,0,'omori-shop-qa')};});status.phase='loading';
  }
  status.assets=held.map(function(v){var b=v.bitmap,i=b._image;return {name:v.name,state:b._loadingState,width:i&&i.naturalWidth,height:i&&i.naturalHeight,imageComplete:i&&i.complete};});
  if(status.assets.every(function(v){return v.state==='loaded'&&v.imageComplete&&v.width>0&&v.height>0;})){status.phase='ready';status.readyAt=Date.now();clearInterval(timer);}
 }catch(error){status.phase='error';status.error=String(error.stack||error);clearInterval(timer);}},100);
})();
