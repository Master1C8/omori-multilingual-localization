/* Native text-boundary fixtures; no actual Canvas, input or game rendering. */
'use strict';
const assert=require('node:assert/strict'),api=require('./multilingual/delivery/devanagari_runs.js');
function fixture(){
 const calls=[];
 function Bitmap(){this.width=400;this.height=100;this.fontSize=28;}
 Bitmap.prototype.drawText=function(text,x,y,width,height,align){calls.push({text,x,y,width,height,align});};
 Bitmap.prototype.clearRect=function(){};Bitmap.prototype.fillRect=function(){};
 function Base(){this.contents=new Bitmap();this._wordWrap=true;}
 Base.prototype.wordwrapWidth=function(){return this.contents.width;};
 Base.prototype.textWidth=t=>Array.from(t).length*10;
 Base.prototype.processNormalCharacter=function(s){this.contents.drawText(s.text[s.index++],s.x,s.y,20,s.height,'left');s.x+=10;};
 Base.prototype.processNewLine=function(s){s.index++;s.x=s.left;s.y+=s.height;};
 Base.prototype.calcTextHeight=function(){return 40;};
 Base.prototype.canCreateLetterEffectSprite=function(){return !!this.effects;};
 Base.prototype.createLetterEffectSprite=function(s){calls.push({effect:s._omoriRunText,index:s.index});};
 function Message(){Base.call(this);}Message.prototype=Object.create(Base.prototype);
 Message.prototype.calcTextHeight=function(s){return Base.prototype.calcTextHeight.call(this,s)-5;};
 function Shop(){Message.call(this);}Shop.prototype=Object.create(Message.prototype);
 const env={Window_Base:Base,Window_Message:Message,WindowItemShopMessage:Shop,OmoriLocale:{}};api.install(env);
 return {env,calls,window:new Base()};
}
function state(text,x=0){return {text,index:0,x,left:0,y:0,height:35};}
{
 const f=fixture(),s=state('हिन्दी क्ष त्र ज्ञ कि कु क़');f.window.processNormalCharacter(s);
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].text,s.text);assert.equal(s.index,s.text.length);
 assert.equal(s.text,'हिन्दी क्ष त्र ज्ञ कि कु क़');assert.equal(f.calls[0].align,'left');assert(s.height>=38);
}
{
 const f=fixture(),s=state('हिन्दी\x1bC[4] text');f.window.processNormalCharacter(s);
 assert.equal(f.calls[0].text,'हिन्दी');assert.equal(s.text[s.index],'\x1b');
 s.index+=5;f.window.processNormalCharacter(s);assert.equal(f.calls[1].text,' text');
}
{
 const f=fixture(),s=state('हा\x1b{ाह');f.window.processNormalCharacter(s);
 assert.equal(f.calls[0].text,'हाा');assert.equal(s.index,2);assert.equal(s.text[s.index],'\x1b');
 const x=s.x;s.index+=2;f.window.contents.fontSize+=12;f.window.processNormalCharacter(s);
 assert.equal(s.index,5);assert.equal(s.x,x);assert.equal(f.calls.length,1);
 f.window.processNormalCharacter(s);assert.equal(f.calls[1].text,'ह');assert.equal(s.index,s.text.length);
}
{
 const f=fixture(),s=state('क्\x1bC[4]षि');f.window.processNormalCharacter(s);
 assert.equal(f.calls[0].text,'क्षि');assert.equal(s.index,2);s.index+=5;f.window.processNormalCharacter(s);
 assert.equal(s.index,s.text.length);assert.equal(f.calls.length,1);
}
{
 const f=fixture(),s=state('हिन्दी शब्द',390);f.window.processNormalCharacter(s);
 assert.equal(s.index,0);assert.equal(s.y,35);f.window.processNormalCharacter(s);assert.equal(s.index,s.text.length);
 assert.equal(f.calls.length,1);
}
{
 const f=fixture(),s=state('क्षेत्र');f.window.effects=true;f.window.processNormalCharacter(s);
 assert.equal(f.calls[0].effect,s.text);assert.equal(f.calls[0].index,0);assert.equal(s._omoriRunText,undefined);
}
{
 const f=fixture(),s=state('Latin');f.window.processNormalCharacter(s);assert.equal(f.calls[0].text,'L');
 api.install(f.env);f.window.processNormalCharacter(s);assert.equal(s.index,2);assert.equal(f.calls.length,2);
 assert.equal(new f.env.Window_Message().calcTextHeight(state('हिन्दी')),48);
 assert.equal(new f.env.Window_Message().calcTextHeight(state('Latin')),35);
 assert.equal(api.lineHasScript({text:'हिन्दी\fLatin',index:7}),false);
}
{
 const f=fixture();f.window._text=Array.from('हिन्दी');f.window._textIndex=2;api.refreshName(f.window);
 assert.equal(f.calls[0].text,'हिन्दी');assert.equal(f.window._text.join(''),'हिन्दी');
}
{
 const f=fixture(),shop=new f.env.WindowItemShopMessage(),s=state('सभी दुश्मनों को थोड़ा नुकसान');
 assert.equal(shop.calcTextHeight(s),48);shop._drawingItemText=true;
 assert.equal(shop.calcTextHeight(s),35);shop.processNormalCharacter(s);
 assert.equal(s.height,35);assert.equal(f.calls.at(-1).height,35);assert.equal(s.index,s.text.length);
 shop._drawingItemText=false;assert.equal(shop.calcTextHeight(state('हिन्दी')),48);
 const other=new f.env.Window_Message();other._drawingItemText=true;assert.equal(other.calcTextHeight(state('हिन्दी')),48);
}
console.log('9 Devanagari run/escape/cluster/name groups passed; Canvas/game are fixtures.');
