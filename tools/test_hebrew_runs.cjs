/* Fixture Canvas records actual draw calls; it cannot establish browser bidi/readability. */
'use strict';
const assert=require('node:assert/strict');
const {fixture}=require('./test_arabic_runs.cjs');
const shared=require('./multilingual/delivery/arabic_runs.js');
const api=shared.create({scriptPattern:/[\u0590-\u05ff]/,marker:'_hebrewRunsInstalled',joining:false});
const rtl=t=>'\u202b'+t+'\u202c';
{
 const f=fixture(api,false),s={text:'שָׁלוֹם OMORI 123',index:0,x:0,left:0,y:0,height:25};
 f.window.processNormalCharacter(s);assert.equal(f.calls.length,1);assert.equal(f.calls[0].text,rtl(s.text));assert.equal(s.index,s.text.length);assert.ok(!f.calls[0].text.includes('\u200d'));assert.ok(f.calls[0].text.includes('OMORI 123'));assert.equal(f.env.OmoriLocale._hebrewRunsInstalled,true);assert.equal(f.env.OmoriLocale._arabicRunsInstalled,undefined);
}
{
 const f=fixture(api,false),s={text:'שִׂים\x1bC[4]לב\x1b!\nשלום',index:0,x:0,left:0,y:0,height:25};
 f.window.processNormalCharacter(s);assert.equal(f.calls[0].text,rtl('שִׂים'));assert.equal(s.text[s.index],'\x1b');s.index+=5;f.window.processNormalCharacter(s);assert.equal(f.calls[1].text,rtl('לב'));assert.equal(s.text.slice(s.index,s.index+2),'\x1b!');
}
{
 const f=fixture(api,false),s={text:'שלום עולם',index:0,x:180,left:0,y:0,height:25};f.window.processNormalCharacter(s);assert.equal(s.index,0);assert.equal(s.y,25);f.window.processNormalCharacter(s);assert.equal(s.index,s.text.length);assert.equal(f.calls[0].text,rtl(s.text));
}
{
 const f=fixture(api,false),s={text:'שִׁיר',index:0,x:0,left:0,y:0,height:25};f.window.effects=true;f.window.processNormalCharacter(s);assert.equal(f.calls[0].effect,s.text);assert.equal(s.index,s.text.length);assert.equal(s._omoriRunText,undefined);
}
{
 const f=fixture(api,false),s={text:'Latin 123',index:0,x:0,left:0,y:0,height:25};f.window.processNormalCharacter(s);assert.equal(f.calls[0].text,'L');assert.equal(s.index,1);api.install(f.env);f.window.processNormalCharacter(s);assert.equal(s.index,2);assert.equal(f.calls.length,2);
}
{
 const f=fixture(api,false);f.window._text=['ש','ל','ו','ם'];f.window._textIndex=1;api.refreshName(f.window);assert.equal(f.calls[0].text,rtl('שלום'));assert.equal(f.calls[0].align,'right');
 const i={text:'שלום',index:0,x:40,left:0,y:0,height:25};f.window.processDrawIcon(2,i);assert.equal(f.calls[1].x,124);assert.equal(i.x,76);
}
console.log('6 Hebrew run/mark/mixed-text/escape/wrap/name boundary groups passed; no actual Canvas rendering.');
