/* Call-boundary tests: Canvas pixels and the native engine are not replaced proof. */
'use strict';
const assert=require('node:assert/strict'),api=require('./multilingual/delivery/thai_clusters.js');
function fixture(){
 const calls=[];
 function Base(){this.contents={width:120,fontSize:24,drawText:(...args)=>calls.push(args)};this._wordWrap=true;}
 Base.prototype.textWidth=t=>t.length*10;
 Base.prototype.processNormalCharacter=function(s){calls.push(['native',s.text[s.index++]]);s.x+=10;};
 Base.prototype.processNewLine=function(s){s.index++;s.x=s.left;s.y+=s.height;};
 Base.prototype.canCreateLetterEffectSprite=function(){return !!this.effects;};
 Base.prototype.createLetterEffectSprite=function(s){calls.push(['effect',s._omoriRunText]);};
 const env={Window_Base:Base,OmoriLocale:{}};api.install(env);return {env,w:new Base(),calls};
}
const state=(text,x=0)=>({text,index:0,x,left:0,y:0,height:32});
{
 const f=fixture(),s=state('\u0e01\u0e33\u0e25\u0e31\u0e07');
 while(s.index<s.text.length)f.w.processNormalCharacter(s);
 assert.deepEqual(f.calls.map(c=>c[0]),['\u0e01\u0e33','\u0e25\u0e31','\u0e07']);
 assert.equal(s.text,'\u0e01\u0e33\u0e25\u0e31\u0e07');assert.equal(s.x,50);
}
{
 const f=fixture(),s=state('\u0e19\u0e49\u0e33\x1bC[4]x');f.w.effects=true;f.w.processNormalCharacter(s);
 assert.deepEqual(f.calls,[['effect','\u0e19\u0e49\u0e33']]);assert.equal(s.index,3);assert.equal(s.text[s.index],'\x1b');assert.equal(s._omoriRunText,undefined);
}
{
 const f=fixture(),s=state('\u0e01\u0e33',110);f.w.processNormalCharacter(s);
 assert.equal(s.index,0);assert.equal(s.y,32);assert.equal(f.calls.length,0);
 f.w.processNormalCharacter(s);assert.equal(s.index,2);assert.equal(f.calls[0][0],s.text);
}
{
 const f=fixture(),s=state('\u0e01\u0e33');f.w._checkWordWrapMode=true;f.w.processNormalCharacter(s);
 assert.equal(s.index,2);assert.equal(s.x,20);assert.equal(f.calls.length,0);
 const latin=state('ABC');f.w.processNormalCharacter(latin);assert.deepEqual(f.calls,[['native','A']]);
 api.install(f.env);f.w.processNormalCharacter(latin);assert.equal(latin.index,2);
}
console.log('PASS Thai base/SARA AM, stacked signs, escape boundary, effect sprite, cluster wrapping, measurement-only mode and native Latin fallback. Call fixtures do not prove native shaping.');
{
 const measure=(text,size)=>text.length*size/2;
 assert.equal(api.shopFontSize('กก<br>\nกก',28,482,72,measure),26);
 assert.equal(api.shopFontSize('กก',28,482,72,measure),28);
 assert.equal(api.shopFontSize('กก\nกก\nกก',28,482,90,measure),22);
 assert.equal(api.shopFontSize('ก'.repeat(60),28,482,72,measure),26);
 // Original28px cluster lines38px require76px, exceeding the real72px band.
 assert(2*Math.ceil(28*1.35)>72);assert.equal(2*Math.ceil(26*1.35),72);
 function Base(){}
 Base.prototype.processNormalCharacter=function(){};
 function Shop(){this.contents={width:592,height:96,fontSize:99};this._itemListWindow={item:()=>({description:'กก<br>\nกก'})};}
 Shop.prototype.resetFontSettings=function(){this.contents.fontSize=28;};
 Shop.prototype.textWidth=function(t){return measure(t,this.contents.fontSize);};
 const env={OmoriLocale:{},Window_Base:Base,WindowItemShopMessage:Shop};api.install(env);
 const w=new Shop();w.resetFontSettings();assert.equal(w.contents.fontSize,28);
 w._drawingItemText=true;w.resetFontSettings();assert.equal(w.contents.fontSize,26);
 w._itemListWindow.item=()=>({description:'English<br>\nhelp'});w.resetFontSettings();assert.equal(w.contents.fontSize,28);
}
console.log('PASS native shop band size calculation, explicit/native breaks, automatic cluster wrapping, scoped font-reset application and unchanged non-item/Latin paths; native page and readability proof still required.');
