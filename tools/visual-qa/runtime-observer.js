// Temporary QA observer. No save API, language mutation or game-state command.
(function(){
 const fs=require('fs');const statePath=__STATE_PATH__;const events=[];var rafTicks=0,inputUpdateSerial=0,inputConsumption=null;
 function diagnostic(kind,value){try{fs.appendFileSync(statePath+'.events.jsonl',JSON.stringify({time:Date.now(),kind:kind,value:value})+'\n');}catch(e){}}
 window.addEventListener('error',function(e){diagnostic('error',{message:e.message,file:e.filename,line:e.lineno,column:e.colno,stack:e.error&&String(e.error.stack)});});
 window.addEventListener('unhandledrejection',function(e){diagnostic('unhandledrejection',String(e.reason&&e.reason.stack||e.reason));});
 window.addEventListener('beforeunload',function(){diagnostic('beforeunload',document.visibilityState);});
 if(typeof SceneManager!=='undefined' && typeof SceneManager.catchException==='function'){
  const originalCatch=SceneManager.catchException;
  SceneManager.catchException=function(error){diagnostic('engine-exception',String(error&&error.stack||error));return originalCatch.apply(this,arguments);};
 }
 for(const type of ['keydown','keyup']) document.addEventListener(type,function(e){events.push({type:type,key:e.key,code:e.code,keyCode:e.keyCode,ctrl:e.ctrlKey,meta:e.metaKey,alt:e.altKey,trusted:e.isTrusted,time:Date.now(),frame:typeof Graphics!=='undefined'?Graphics.frameCount:null});if(events.length>40)events.shift();},true);
 function assetReadiness(){
  if(typeof ImageManager==='undefined')return null;
  function bitmap(b){var src=b&&b._image&&b._image.src;return b?{url:b._url,state:b._loadingState,imageSrc:src&&src.indexOf('data:')===0?src.slice(0,src.indexOf(',')+1)+'[payload omitted]':src,
   imageComplete:b._image&&b._image.complete,naturalWidth:b._image&&b._image.naturalWidth}:null;}
  var queue=ImageManager._requestQueue&&ImageManager._requestQueue._queue||[];
  var items=ImageManager._imageCache&&ImageManager._imageCache._items||{};
  var pending=Object.keys(items).filter(function(k){var b=items[k].bitmap;return b&&b._loadingState!=='loaded'&&b._loadingState!=='none';});
  var next=typeof SceneManager!=='undefined'&&SceneManager._nextScene;
  // Read fields only. Calling the atlas readiness predicate would itself load/cache assets.
  return {queueLength:queue.length,queue:queue.slice(0,128).map(function(q){return {key:q.key,bitmap:bitmap(q.value)};}),
   pendingCacheCount:pending.length,pendingCache:pending.slice(0,128).map(function(k){return {key:k,bitmap:bitmap(items[k].bitmap)};}),
   cacheItems:Object.keys(items).length,requiredNextAtlases:next&&next._requiredAtlasList,
   allNextAtlasesLoaded:next&&next._allAtlasLoaded,
   busyPredicate:typeof SceneManager!=='undefined'&&String(SceneManager.isCurrentSceneBusy)};
 }
 function publish(){try{
  const s=typeof SceneManager==='undefined'?null:SceneManager._scene;
  const value={observer:'omori-oculix-event-observer-v1',time:Date.now(),scene:s&&s.constructor.name,index:s&&s._commandIndex,active:s&&s._commandActive,canContinue:s&&s._canContinue,focused:document.hasFocus(),events:events,visibility:document.visibilityState,frame:typeof Graphics!=='undefined'?Graphics.frameCount:null,language:typeof ConfigManager!=='undefined'&&ConfigManager.language,fontProbe:window.__qaFontProbe||null,input:typeof Input!=='undefined'&&Input._currentState};
  value.fontStatus=document.fonts&&document.fonts.status;
  value.startupDiagnostics={rafTicks:rafTicks,focusGateType:typeof SceneManager!=='undefined'?typeof SceneManager.isFocus:null,
   focusGateValue:typeof SceneManager!=='undefined'&&typeof SceneManager.isFocus==='function'?SceneManager.isFocus():null,
   focusGateSource:typeof SceneManager!=='undefined'&&typeof SceneManager.isFocus==='function'?String(SceneManager.isFocus):null,
   backgroundAdapter:window.__qaBackgroundAdapter||null,frameScheduler:window.__qaFrameScheduler||null,windowPolicy:window.__qaWindowPolicy||null,locale:window.OmoriLocale&&window.OmoriLocale.siteLocale,
   renderer:typeof Graphics!=='undefined'&&!!Graphics._renderer,
   rendererInfo:typeof Graphics!=='undefined'&&Graphics._renderer?{type:Graphics._renderer.type,name:Graphics._renderer.constructor.name,webgl:!!Graphics._renderer.gl}:null,
   sceneStarted:typeof SceneManager!=='undefined'&&SceneManager._sceneStarted,
   steamInitialized:typeof SceneManager!=='undefined'&&SceneManager._steamInitialized,
   pluginErrors:typeof PluginManager!=='undefined'?PluginManager._errorUrls:null,
   database:typeof DataManager!=='undefined'&&DataManager._databaseFiles?DataManager._databaseFiles.map(function(row){return {name:row.name,loaded:window[row.name]!=null};}):null};
  value.engineStopped=typeof SceneManager!=='undefined'&&SceneManager._stopped;
  value.inputUpdateSerial=inputUpdateSerial;value.inputConsumption=inputConsumption;
  value.assetReadiness=assetReadiness();
  value.inputBridge=window.__qaInputBridge||null;
  value.equipmentAssets=window.__qaEquipmentAssets||null;value.atlasRequests=window.__qaAtlasRequests||null;
  value.transitionDiagnostics={nextScene:typeof SceneManager!=='undefined'&&SceneManager._nextScene&&SceneManager._nextScene.constructor.name,
   currentBusy:s&&typeof s.isBusy==='function'?s.isBusy():null,fadeDuration:s&&s._fadeDuration,
   movementBusy:s&&s.move&&typeof s.move.isMoving==='function'?s.move.isMoving():null,
   waitMode:s&&s._waitMode,waitCount:s&&s._waitCount};
  value.visibleError=typeof Graphics!=='undefined'&&Graphics._errorPrinter?Graphics._errorPrinter.innerText:null;
  fs.writeFileSync(statePath+'.tmp',JSON.stringify(value));fs.renameSync(statePath+'.tmp',statePath);
 }catch(e){console.error('QA observer',e)}}
 setInterval(publish,250);
 // Observe native input sampling before a dialogue transition can clear the
 // key in the same scene/frame. Delegate unchanged to the engine's real update.
 var inputTimer=setInterval(function(){
  if(typeof Input==='undefined'||typeof Input.update!=='function')return;
  clearInterval(inputTimer);var originalUpdate=Input.update;
  Input.update=function(){
   var result=originalUpdate.apply(this,arguments);inputUpdateSerial++;
   var e=events[events.length-1],names={90:'ok',88:'escape',37:'left',39:'right',40:'down',38:'up'};
   if(e&&e.type==='keydown'&&names[e.keyCode]&&this._currentState[names[e.keyCode]]) {
    inputConsumption={keydownTime:e.time,keyCode:e.keyCode,updateSerial:inputUpdateSerial,frame:Graphics.frameCount};publish();
   }
   return result;
  };
 },50);
 // During a native held key publish after each rendered frame. The driver can
 // release promptly after consumption without waiting for a throttled timer.
 function acknowledge(){rafTicks++;if(events.length&&events[events.length-1].type==='keydown')publish();requestAnimationFrame(acknowledge);}
 requestAnimationFrame(acknowledge);
})();
