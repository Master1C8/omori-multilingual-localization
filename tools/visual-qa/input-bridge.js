// Temporary QA input bridge. Normal DOM keys only; no scene/save/equipment APIs.
(function(){
 const fs=require('fs'),base=__STATE_PATH__;
 const requestPath=base+'.input-request.json',ackPath=base+'.input-ack.json';
 const keys={90:['z','KeyZ','ok'],88:['x','KeyX','escape'],37:['ArrowLeft','ArrowLeft','left'],39:['ArrowRight','ArrowRight','right'],38:['ArrowUp','ArrowUp','up'],40:['ArrowDown','ArrowDown','down']};
 var active=null,lastId=null;
 window.__qaInputBridge={identity:'omori-game-thread-dom-input-v1',completed:0};
 function write(value){fs.writeFileSync(ackPath+'.tmp',JSON.stringify(value));fs.renameSync(ackPath+'.tmp',ackPath);}
 function dispatch(type,code){
  var event=new KeyboardEvent(type,{key:keys[code][0],code:keys[code][1],bubbles:true,cancelable:true});
  Object.defineProperty(event,'keyCode',{value:code});Object.defineProperty(event,'which',{value:code});
  document.dispatchEvent(event);
 }
 function release(){if(active&&active.down){dispatch('keyup',active.keyCode);active.down=false;}}
 function proof(status,error){return {id:active.id,keyCode:active.keyCode,status:status,error:error||null,
  time:Date.now(),trusted:false,samples:active.samples,scene:typeof SceneManager!=='undefined'&&SceneManager._scene&&SceneManager._scene.constructor.name};}
 setInterval(function(){
  if(!fs.existsSync(requestPath))return;
  try{
   var request=JSON.parse(fs.readFileSync(requestPath,'utf8'));
   if(request.id===lastId)return;
   if(active)return; // Never replace a key that is still being sampled/released.
   if(request.type!=='keyPulse'||typeof request.id!=='string'||!keys[request.keyCode])return;
   lastId=request.id;active={id:request.id,keyCode:request.keyCode,down:false,samples:[],phase:'queued'};
   write(proof('queued'));
  }catch(error){console.error('QA input request',error);}
 },25);
 var timer=setInterval(function(){
  if(typeof Input==='undefined'||typeof Input.update!=='function')return;
  clearInterval(timer);var original=Input.update;
  if(typeof SceneManager!=='undefined'&&typeof SceneManager.catchException==='function'){
   var originalCatch=SceneManager.catchException;
   SceneManager.catchException=function(error){
    try{if(active){release();write(proof('error',String(error&&error.stack||error)));active=null;}}
    catch(bridgeError){console.error('QA input error acknowledgement',bridgeError);}
    return originalCatch.apply(this,arguments);
   };
  }
  Input.update=function(){
   if(active&&active.phase==='queued'){dispatch('keydown',active.keyCode);active.down=true;active.phase='held';}
   if(active&&active.phase==='held'&&active.samples.length===3){release();active.phase='releasing';}
   var result;
   try{result=original.apply(this,arguments);}
   catch(error){if(active){release();write(proof('error',String(error.stack||error)));active=null;}throw error;}
   if(active&&active.phase==='held'){
    var name=keys[active.keyCode][2];
    active.samples.push({frame:Graphics.frameCount,current:!!this._currentState[name],latestButton:this._latestButton,pressedTime:this._pressedTime});
    if(!this._currentState[name]){release();write(proof('error','Engine did not sample requested key'));active=null;}
    else write(proof('sampled'));
   }else if(active&&active.phase==='releasing'){
    var state=!!this._currentState[keys[active.keyCode][2]];
    write(proof(state?'error':'released',state?'Key remained down after release':null));
    if(!state)window.__qaInputBridge.completed++;
    active=null;
   }
   return result;
  };
 },25);
})();
