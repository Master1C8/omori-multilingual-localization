// Temporary hidden native window policy. Never included in a player package.
(function(){
 if(window.__qaWindowPolicy)throw new Error('Duplicate QA window policy');
 var fs=require('fs'),phasePath=__STATE_PATH__+'.window-policy.json';
 function phase(name){fs.writeFileSync(phasePath+'.tmp',JSON.stringify({phase:name,time:Date.now()}));fs.renameSync(phasePath+'.tmp',phasePath);}
 phase('before-native-window-get');
 var nativeWindow=require('nw.gui').Window.get();
 var policy=window.__qaWindowPolicy={identity:'omori-hidden-native-window-v1',
  hiddenRequested:true,suppressedNativeFocus:0,suppressedShow:0,events:[]};
 var originalShow=nativeWindow.show;
 nativeWindow.focus=function(){policy.suppressedNativeFocus++;};
 nativeWindow.show=function(visible){
  if(visible===false)return originalShow.call(this,false);
  policy.suppressedShow++;
 };
 ['focus','blur','show','hide'].forEach(function(name){
  nativeWindow.on(name,function(){policy.events.push({event:name,time:Date.now()});if(policy.events.length>20)policy.events.shift();});
 });
 phase('installed');
})();
