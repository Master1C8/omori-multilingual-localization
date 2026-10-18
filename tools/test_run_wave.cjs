// Sprite/TDS fixtures verify wiring and phase bounds, not Canvas or native rendering.
const assert=require('assert/strict'),api=require('./multilingual/delivery/run_wave.js');
function setup(){
 function Point(x=0,y=0){this.x=x;this.y=y;}
 function Sprite(bitmap){this.bitmap=bitmap;this.anchor={x:0,y:0};}
 Sprite.prototype.setFrame=function(x,y,w,h){this.frame={x,y,w,h};};
 function Base(){this._letterEffects=[{name:'SINV',active:true,startIndex:2,endIndex:20,spacing:1,speed:.15,amplitude:.07}];this._letterEffectSprites=[];this.drawn=[];this.children=[];this._letterEffectContainerSprite={addChild:s=>this.children.push(s),removeChild:s=>this.children.splice(this.children.indexOf(s),1)};}
 Base.prototype.createLetterEffectSprite=function(s){this.drawn.push(s._omoriRunText||s.text[s.index]);let p=new Sprite({width:11,height:50});p.x=30;p.y=8;p._effectData={origin:new Point(30,8),offset:new Point(),index:s.index,tag:4,position:0};this._letterEffectSprites.push(p);this._letterEffectContainerSprite.addChild(p);return 37;};
 Base.prototype.applyLetterEffectToSprite=function(e,p){p.anchor.y=0;return 19;};
 const env={Window_Base:Base,Sprite,Point,Graphics:{frameCount:100},OmoriLocale:{}};api.install(env);return{env,w:new Base()};
}
{
 const {env,w}=setup(),state={text:'xxبخ!!',index:2,_omoriRunText:'بخ!!'};assert.equal(w.createLetterEffectSprite(state),37);assert.deepEqual(w.drawn,['بخ!!']);assert.equal(state.index,2);assert.equal(state._omoriRunText,'بخ!!');
 const s=w._letterEffectSprites;assert.equal(s.length,6);assert.equal(w.children.length,6);assert(s.every(p=>p.bitmap===s[0].bitmap&&p._effectData.index===2));
 assert.deepEqual(s.map(p=>p.frame.x),[0,2,4,6,8,10]);assert.deepEqual(s.map(p=>p.frame.w),[2,2,2,2,2,1]);assert.equal(s[5].x,40);
 const e=w._letterEffects[0];s.forEach(p=>assert.equal(w.applyLetterEffectToSprite(e,p),19));assert.notEqual(s[0].anchor.y,s[5].anchor.y);const before=s[0].anchor.y;env.Graphics.frameCount++;w.applyLetterEffectToSprite(e,s[0]);assert.notEqual(before,s[0].anchor.y);
 for(const change of [{active:false},{startIndex:3},{endIndex:2},{name:'SHAKE'}]){w.applyLetterEffectToSprite({...e,...change},s[0]);assert.equal(s[0].anchor.y,0);}
 const wrapped=env.Window_Base.prototype.createLetterEffectSprite;api.install(env);assert.equal(env.Window_Base.prototype.createLetterEffectSprite,wrapped);
}
for(const [text,contextual,effect] of [['A',undefined,'SINV'],['שיר','שיר','SHAKE'],['क्षेत्र','क्षेत्र','SINV']]){
 const {w}=setup();w._letterEffects[0].name=effect;w.createLetterEffectSprite({text,index:2,_omoriRunText:contextual});assert.equal(w._letterEffectSprites.length,contextual&&effect==='SINV'?6:1);assert.equal(w.drawn.length,1);
}
console.log('PASS full-run single draw/shared bitmap, exact strip coverage, unchanged logical indices, spatial/temporal wave, inactive/range/other-effect rejection, Latin delegation and install idempotence; native visual proof required.');

for(const extra of [{name:'SHAKE',active:true,startIndex:2,endIndex:20},{name:'SHAKE',active:false,startIndex:2,endIndex:20},{name:'SHAKE',active:true,startIndex:3,endIndex:20}]){
 const {w}=setup();w._letterEffects.push(extra);w.createLetterEffectSprite({text:'xxبخ!!',index:2,_omoriRunText:'بخ!!'});assert.equal(w._letterEffectSprites.length,extra.active&&extra.startIndex===2?1:6);assert.equal(w.drawn.length,1);
}
console.log('PASS active overlapping effects delegate unchanged; inactive/out-of-range effects do not block pure SINV.');
