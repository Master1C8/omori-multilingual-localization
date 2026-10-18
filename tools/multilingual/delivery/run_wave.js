/* Deform an already shaped contextual run; never reshape isolated Arabic letters. */
(function(root){
 'use strict';
 function install(env){
  if(env.OmoriLocale._runWaveInstalled)return;
  var base=env.Window_Base.prototype,create=base.createLetterEffectSprite,apply=base.applyLetterEffectToSprite;
  if(typeof create!=='function'||typeof apply!=='function')throw Error('Native TDS effect APIs unavailable');
  base.createLetterEffectSprite=function(state){
   var contextual=state._omoriRunText;
   var eligible=(this._letterEffects||[]).filter(function(e){return e.active&&state.index>=e.startIndex&&state.index<e.endIndex;});
   // Keep native combined-effect behavior unchanged; this repair targets pure SINV.
   var wave=contextual&&eligible.some(function(e){return e.name==='SINV';})&&eligible.every(function(e){return e.name==='SINV';});
   var start=this._letterEffectSprites.length,result=create.apply(this,arguments);
   if(!wave)return result;
   var sprites=this._letterEffectSprites,original=sprites[start];
   if(sprites.length!==start+1||!original||!original.bitmap)throw Error('Contextual TDS sprite boundary changed');
   var bitmap=original.bitmap,width=bitmap.width,height=bitmap.height;
   if(width<2)return result;
   var count=Array.from(contextual.replace(/[\u200c\u200d\u202a-\u202e\u2066-\u2069]/g,'')).length;
   // Shared bitmap retains Canvas joining, bidi and marks. Two-pixel native
   // texture strips receive smoothly changing phases of the original SINV.
   var strips=[];
   for(var x=0;x<width;x+=2){
    var piece=Math.min(2,width-x),sprite=new env.Sprite(bitmap),data=original._effectData;
    sprite.setFrame(x,0,piece,height);sprite.x=original.x+x;sprite.y=original.y;
    sprite._effectData={origin:new env.Point(data.origin.x+x,data.origin.y),offset:new env.Point(),index:data.index,position:start+strips.length,tag:data.tag};
    sprite._omoriRunWavePhase=(x+piece/2)/width*Math.max(1,count);
    strips.push(sprite);
   }
   this._letterEffectContainerSprite.removeChild(original);sprites.pop();
   strips.forEach(function(sprite){sprites.push(sprite);this._letterEffectContainerSprite.addChild(sprite);},this);
   return result;
  };
  base.applyLetterEffectToSprite=function(effect,sprite){
   var result=apply.apply(this,arguments),index=sprite._effectData.index;
   if(sprite._omoriRunWavePhase!==undefined&&effect.name==='SINV'&&effect.active&&index>=effect.startIndex&&index<effect.endIndex)
    sprite.anchor.y=Math.sin((env.Graphics.frameCount+(index+sprite._omoriRunWavePhase)*effect.spacing)*effect.speed)*effect.amplitude;
   return result;
  };
  env.OmoriLocale._runWaveInstalled=true;
 }
 var api={install:install};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OmoriLocaleRunWave=api;
})(typeof globalThis!=='undefined'?globalThis:this);
