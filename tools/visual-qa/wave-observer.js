// Passive samples of the original TDS letter sprites. No engine state changes.
(function(){
 var fs=require('fs'),path=__STATE_PATH__+'.wave.json';
 setInterval(function(){try{
  var s=SceneManager._scene,w=s&&s._messageWindow;
  var v={time:Date.now(),frame:Graphics.frameCount,texts:$gameMessage&&$gameMessage._texts,
   fileAssets:window.__qaFileAssets,fileRequests:window.__qaFileRequests,
   complete:!!(w&&w.pause&&!w._textState),openness:w&&w.openness,
   effects:w&&(w._letterEffects||[]).map(function(e){return {name:e.name,active:e.active,amplitude:e.amplitude,speed:e.speed,spacing:e.spacing};}),
   sprites:w&&(w._letterEffectSprites||[]).map(function(p){return {x:p.x,y:p.y,anchorY:p.anchor.y,width:p.width,height:p.height,index:p._effectData&&p._effectData.index};})};
  fs.writeFileSync(path+'.tmp',JSON.stringify(v));fs.renameSync(path+'.tmp',path);
 }catch(e){fs.writeFileSync(path+'.error',String(e.stack||e));}},100);
})();
