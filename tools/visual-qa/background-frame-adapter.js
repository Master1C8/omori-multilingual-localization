// Temporary QA-only scheduler. Install before engine/PIXI scripts, never ship it.
// Timers remained live while native animation frames stalled under macOS occlusion.
(function(){
 if(window.__qaFrameScheduler)throw new Error('Duplicate QA frame scheduler');
 var nativeRequest=window.requestAnimationFrame.bind(window);
 var nativeCancel=window.cancelAnimationFrame.bind(window);
 var nextId=1,pending=Object.create(null);
 var evidence=window.__qaFrameScheduler={identity:'omori-background-frame-fallback-v1',nativeDeliveries:0,
   fallbackDeliveries:0,cancelled:0,lateCallbacksIgnored:0,lastDeliveryTime:null,fallbackDeadlineMs:100,suppressedFocusCalls:0};
 // Omori BASE calls window.focus() during plugin evaluation. Block it before
 // plugins run, only inside this temporary background QA session.
 window.focus=function(){evidence.suppressedFocusCalls++;};
 window.requestAnimationFrame=function(callback){
  if(typeof callback!=='function')throw new TypeError('Animation callback must be a function');
  var id=nextId++,entry={active:true,nativeId:null,timerId:null};pending[id]=entry;
  function deliver(kind,timestamp){
   if(!entry.active){evidence.lateCallbacksIgnored++;return;}
   entry.active=false;delete pending[id];
   if(kind==='native'){clearTimeout(entry.timerId);evidence.nativeDeliveries++;}
   else{nativeCancel(entry.nativeId);evidence.fallbackDeliveries++;}
   evidence.lastDeliveryTime=timestamp;
   callback.call(window,timestamp);
  }
  entry.nativeId=nativeRequest(function(timestamp){deliver('native',timestamp);});
  entry.timerId=setTimeout(function(){deliver('fallback',performance.now());},100);
  return id;
 };
 window.cancelAnimationFrame=function(id){
  var entry=pending[id];if(!entry)return;
  entry.active=false;delete pending[id];clearTimeout(entry.timerId);nativeCancel(entry.nativeId);evidence.cancelled++;
 };
})();
