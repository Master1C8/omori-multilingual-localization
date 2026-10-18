/* Isolated native text-boundary tests. Canvas is a call recorder, not a renderer. */
'use strict';
const assert=require('node:assert/strict');
const api=require('./multilingual/delivery/arabic_runs.js');
const joining=require('./multilingual/delivery/arabic_joining.js');
const rtl=text=>'\u202b'+text+'\u202c';
function fixture(renderer=api,includeJoining=true) {
  const calls=[];
  function Bitmap(){this.width=200;this.height=100;this.fontSize=20;this._context={direction:'ltr'};}
  Bitmap.prototype.drawText=function(text,x,y,width,height,align){calls.push({text,x,y,width,height,align,direction:this._context.direction});};
  Bitmap.prototype.clearRect=function(){};Bitmap.prototype.fillRect=function(){};
  function Base(){this.contents=new Bitmap();this._wordWrap=true;}
  Base._iconWidth=32;
  Base.prototype.textWidth=text=>Array.from(text).filter(c=>c!=='\u200d').length*10;
  Base.prototype.wordwrapWidth=function(){return this.contents.width;};
  Base.prototype.processNormalCharacter=function(s){this.contents.drawText(s.text[s.index++],s.x,s.y,20,s.height,'left');s.x+=10;};
  Base.prototype.processNewLine=function(s){s.index++;s.x=s.left;s.y+=s.height;};
  Base.prototype.processDrawIcon=function(icon,s){calls.push({icon,x:s.x});s.x+=36;};
  Base.prototype.calcTextHeight=function(){return this._nativeHeight||25;};
  function Message(){Base.call(this);}Message.prototype=Object.create(Base.prototype);
  Message.prototype.calcTextHeight=function(s){return Base.prototype.calcTextHeight.call(this,s)-7;};
  function Shop(){Message.call(this);}Shop.prototype=Object.create(Message.prototype);
  Base.prototype.canCreateLetterEffectSprite=function(){return !!this.effects;};
  Base.prototype.createLetterEffectSprite=function(s){calls.push({effect:s._omoriRunText,index:s.index,x:s.x});};
  const env={Bitmap,Window_Base:Base,Window_Message:Message,WindowItemShopMessage:Shop,OmoriLocale:{},OmoriArabicJoining:joining};if(!includeJoining)delete env.OmoriArabicJoining;renderer.install(env);
  return {calls,env,window:new Base()};
}
{
  const f=fixture(),s={text:'سلام 123 (OMORI)',index:0,x:0,left:0,y:0,height:25};
  f.window.processNormalCharacter(s);
  assert.equal(f.calls.length,1);assert.equal(f.calls[0].text,rtl(s.text));
  assert.equal(f.calls[0].direction,'ltr');assert.equal(s.index,s.text.length);
  assert.equal(f.window.contents._context.direction,'ltr');
  assert.equal(s.text,'سلام 123 (OMORI)');assert.ok(s.height>=33);
}
{
  const f=fixture(),text='أهلاً\x1bC[4]بالعالم\x1b!\nالتالي';
  const s={text,index:0,x:0,left:0,y:0,height:25};f.window.processNormalCharacter(s);
  assert.equal(f.calls[0].text,rtl('أهلاً'));assert.equal(s.text[s.index],'\x1b');
  // The native dispatcher, not this adapter, owns style/pause/page side effects.
  s.index+=5;f.window.processNormalCharacter(s);assert.equal(f.calls[1].text,rtl('بالعالم'));
  assert.equal(s.text.slice(s.index,s.index+2),'\x1b!');
}
{
  const f=fixture(),s={text:'مرحبا بالعالم',index:0,x:150,left:0,y:0,height:25};
  f.window.processNormalCharacter(s);assert.equal(s.index,0);assert.equal(s.y,25);
  f.window.processNormalCharacter(s);assert.equal(s.index,s.text.length);
  assert.equal(f.calls.length,1);
}
{
  const f=fixture(),s={text:'اللّٰه',index:0,x:0,left:0,y:0,height:25};
  f.window.effects=true;f.window.processNormalCharacter(s);
  assert.equal(f.calls[0].effect,'اللّٰه');assert.equal(f.calls[0].index,0);
  assert.equal(s.index,s.text.length);assert.equal(s._omoriRunText,undefined);
}
{
  const f=fixture(),s={text:'سلام',index:0,x:40,left:20,y:0,height:25};
  f.window.processNormalCharacter(s);assert.equal(f.calls[0].x,120);
  const i={text:'سلام',index:0,x:40,left:20,y:0,height:25};f.window.processDrawIcon(2,i);
  assert.equal(f.calls[1].x,124);assert.equal(i.x,76);
  const second={text:'سلام',index:0,x:80,left:80,y:0,height:25};f.window.processNormalCharacter(second);
  assert.equal(f.calls[2].x,80); // Distinct native columns keep distinct mirrored anchors.
}
{
  const f=fixture(),s={text:'English',index:0,x:0,left:0,y:0,height:25};
  f.window.processNormalCharacter(s);assert.equal(f.calls[0].text,'E');assert.equal(s.index,1);
  f.window.contents.drawText('abc',0,0,30,25,'left');assert.equal(f.calls[1].direction,'ltr');
  const count=f.calls.length;api.install(f.env);f.window.processNormalCharacter(s);
  assert.equal(f.calls.length,count+1);assert.equal(s.index,2);
}
{
  const f=fixture();f.window.contents._context={};
  f.window.contents.drawText('سلام 123 (OMORI)',0,0,150,30,'left');
  assert.equal(f.calls[0].text,rtl('سلام 123 (OMORI)'));
  assert.equal('direction' in f.window.contents._context,false);
  f.window.contents._omoriRtlRun=true;
  f.window.contents.drawText('123 (OMORI)',0,0,150,30,'left');
  assert.equal(f.calls[1].text,rtl('123 (OMORI)'));
  f.window.contents._omoriRtlRun=false;
  f.window.contents._context={direction:'ltr'};
  f.window._text=['س','ا','م','ي'];f.window._textIndex=2;api.refreshName(f.window);
  assert.equal(f.calls[2].text,rtl('سامي'));assert.equal(f.calls[2].align,'right');
}
{
  assert.equal(joining.type('س'),'D');assert.equal(joining.type('ا'),'R');assert.equal(joining.type('َ'),'T');
  assert.equal(joining.type('\u200d'),'C');assert.equal(joining.type('\u200c'),'U');
  const text='س\x1bC[4]لام', f=fixture(), state={text,index:0,x:0,left:0,y:0,height:25};
  f.window.processNormalCharacter(state);assert.equal(f.calls[0].text,rtl('س\u200d'));assert.equal(state.index,1);
  state.index=6;f.window.processNormalCharacter(state);assert.equal(f.calls[1].text,rtl('\u200dلام'));
  assert.equal(state.index,text.length);assert.equal(state.text,text);
  assert.equal(api.contextualText({text:'د\x1bC[4]ار',index:0},'د',joining),'د');
  assert.equal(api.contextualText({text:'د\x1bC[4]ار',index:6},'ار',joining),'ار');
  assert.equal(api.contextualText({text:'س\x1bI[4]لام',index:0},'س',joining),'س');
  assert.equal(api.contextualText({text:'س \x1bC[4]لام',index:0},'س ',joining),'س ');
  assert.equal(api.contextualText({text:'سَ\x1b{لام',index:0},'سَ',joining),'سَ\u200d');
  assert.equal(api.lineHasArabic({text:'سلام\fEnglish',index:5}),false);
}
{
 const f=fixture(),message=new f.env.Window_Message();message._nativeHeight=56;
 assert.equal(message.calcTextHeight({text:'س\\{لام',index:0}),81);
 assert.equal(message.calcTextHeight({text:'Latin',index:0}),49);
}
{
 const f=fixture(),shop=new f.env.WindowItemShopMessage(),text='تسبب ضررا طفيفا لجميع الأعداء';
 shop._nativeHeight=43;shop.contents.fontSize=28;shop.contents.width=600;
 const state=()=>({text,index:0,x:0,left:0,y:24,height:36});
 assert.equal(shop.calcTextHeight(state()),60);
 shop._drawingItemText=true;
 assert.equal(shop.calcTextHeight(state()),36);
 let s=state();shop.processNormalCharacter(s);assert.equal(s.height,36);assert.equal(f.calls.at(-1).height,36);
 assert.equal(s.index,text.length);assert.equal(f.calls.at(-1).text,rtl(text));
 assert.equal(2*36,72);assert(2*60>72);
 shop._drawingItemText=false;s=state();shop.processNormalCharacter(s);assert.equal(s.height,47);
 const other=new f.env.Window_Message();other._drawingItemText=true;other._nativeHeight=43;other.contents.fontSize=28;
 assert.equal(other.calcTextHeight(state()),60);
}
console.log('10 Arabic contextual-run boundary groups passed; real Canvas/game rendering not exercised.');

module.exports={fixture};
