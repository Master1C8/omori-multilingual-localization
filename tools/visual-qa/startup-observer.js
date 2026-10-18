// Read-only startup evidence installed before styles and core scripts.
(function(){
 const fs=require('fs'),path=__STATE_PATH__+'.startup.json';
 function event(kind,value){try{fs.appendFileSync(path+'.events.jsonl',JSON.stringify({time:Date.now(),kind:kind,value:value})+'\n');}catch(ignore){}}
 window.addEventListener('error',function(e){event('error',{message:e.message,source:e.filename,line:e.lineno,resource:e.target&&(e.target.src||e.target.href),stack:e.error&&String(e.error.stack)});},true);
 window.addEventListener('unhandledrejection',function(e){event('rejection',String(e.reason&&e.reason.stack||e.reason));});
 document.addEventListener('DOMContentLoaded',function(){event('DOMContentLoaded',document.readyState);});
 window.addEventListener('load',function(){event('load',document.readyState);});
 function publish(){try{
  var resources=performance.getEntriesByType('resource').slice(-16).map(function(r){return {name:r.name,type:r.initiatorType,duration:r.duration,responseEnd:r.responseEnd};});
  var value={observer:'omori-startup-readonly-v1',time:Date.now(),readyState:document.readyState,
   scripts:Array.prototype.map.call(document.scripts,function(s){return s.src;}),resources:resources,
   globals:{PIXI:typeof PIXI,SceneManager:typeof SceneManager,DataManager:typeof DataManager,Input:typeof Input},
   scene:typeof SceneManager!=='undefined'&&SceneManager._scene&&SceneManager._scene.constructor.name};
  fs.writeFileSync(path+'.tmp',JSON.stringify(value));fs.renameSync(path+'.tmp',path);
 }catch(e){event('observer-error',String(e.stack||e));}}
 publish();setInterval(publish,500);
})();
