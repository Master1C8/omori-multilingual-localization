// Temporary capture-session adapter; original game files are never patched.
// Permit the normal engine update/render loop while the native window is behind
// another app. This does not spoof document.hasFocus or issue gameplay commands.
(function(){
 var timer=setInterval(function(){
  if(typeof SceneManager==='undefined'||typeof SceneManager.isFocus!=='function')return;
  clearInterval(timer);
  window.__qaBackgroundAdapter={originalFocusGate:SceneManager.isFocus.toString(),identity:'omori-background-capture-v1',status:'active'};
  SceneManager.isFocus=function(){return true;};
 },50);
})();
