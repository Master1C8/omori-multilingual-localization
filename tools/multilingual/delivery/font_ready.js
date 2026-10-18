/* Wait for the exact packaged CSS faces before the first game text layout. */
(function(root) {
  'use strict';
  function install(env, probes) {
    if(!probes.length)return;
    var document=env.document, fonts=document && document.fonts,
        original=env.Scene_Boot && env.Scene_Boot.prototype.isReady,
        start=env.Date.now(), ready=false, failure=null;
    if(!fonts || typeof fonts.load!=='function' || typeof original!=='function' || !probes.length)
      throw new Error('OMORI locale fallback font loading API is unavailable');
    env.Scene_Boot.prototype.isReady=function() {
      var nativeReady=original.apply(this,arguments);
      if(failure)throw failure;
      if(!ready && env.Date.now()-start>=60000) {
        failure=new Error('OMORI locale fallback fonts timed out');throw failure;
      }
      return nativeReady && ready;
    };
    var link=document.createElement('link');
    link.rel='stylesheet';link.href='fonts/locale-fallback.css';
    link.onerror=function() {failure=new Error('OMORI locale fallback stylesheet failed');};
    link.onload=function() {
      Promise.all(probes.map(function(probe) {
        return Promise.resolve().then(function() {
          return fonts.load('16px '+probe.family,probe.text);
        }).then(function(faces) {
          if(!faces || !faces.length || faces.some(function(face) {return face.status!=='loaded';}))
            throw new Error('OMORI locale fallback font is unavailable: '+probe.family+'/'+probe.file);
        });
      })).then(function() {ready=true;},function(error) {failure=error;});
    };
    document.head.appendChild(link);
  }
  var api={install:install};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleFonts=api;
}(typeof globalThis!=='undefined'?globalThis:this));
