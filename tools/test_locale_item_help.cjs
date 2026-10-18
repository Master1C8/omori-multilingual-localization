/* Tests presentation boundaries with a fake renderer; native Canvas is separate. */
'use strict';
const assert=require('assert'),ui=require('./multilingual/delivery/ui_layout.js');
function fixture(direction,mode='normal') {
 const probes=[],calls=[];
 function Bitmap(w,h){
  this.width=w;this.height=h;this.fontSize=20;this.shift=[0,0];this.destroyed=false;
  this._baseTexture={destroy:()=>{this.destroyed=true;}};
  this._context={translate:(x,y)=>{this.shift=[x,y];},getImageData:()=>{
   const data=new Uint8ClampedArray(w*h*4);
   const ink=this.ink||[];for(const [x,y] of ink)data[(y*w+x)*4+3]=255;
   return {data};
  }};probes.push(this);
 }
 function Help(){this._iconRate=1;this._item={description:'unchanged'};this.contents={width:450,height:101,fontSize:20,blt:(...a)=>calls.push(a)};}
 Help.prototype.wordwrapWidth=function(){return this.contents.width;};
 Help.prototype.drawTextEx=function(...args){
  calls.push({args,width:this.wordwrapWidth(),probe:this._omoriHelpInkProbe});
  if(mode==='throw')throw new Error('native-rich-text-failure');
  if(this._omoriHelpInkProbe){
   const [mx,my]=this.contents.shift,w=mode==='too-wide'?400:200,h=mode==='too-tall'?90:42;
   // Model Chromium RTL ink extending past the requested column; the detached
   // surface must preserve it and normalize only its final placement.
   this.contents.ink=[[mx+300,my+28],[mx+300+w-1,my+28+h-1]];
   if(mode==='edge')this.contents.ink.push([0,1]);
   if(mode==='empty')this.contents.ink=[];
   this.contents.fontBold=true;
  }
  return 123;
 };
 const native=Help.prototype.drawTextEx;ui.configure({Bitmap,Window_OmoMenuHelp:Help},{direction});ui.installItemHelp();
 return {Help,native,calls,probes};
}
const text='سكين جديدة لامعة.<br>\nيمكنك رؤية OMORI 12 على النصل.';
for(const own of [false,true]){
 const f=fixture('rtl'),h=new f.Help(),target=h.contents,item=JSON.stringify(h._item);
 if(own)Object.defineProperty(h,'wordwrapWidth',{value:()=>777,writable:true,configurable:true});
 const descriptor=Object.getOwnPropertyDescriptor(h,'wordwrapWidth');
 assert.equal(h.drawTextEx(text,6,28,28),123);
 assert.deepEqual(f.calls[0].args,[text,6,28,28]);assert.equal(f.calls[0].width,336);
 const blt=f.calls[1];assert.deepEqual(blt.slice(3),[200,42,136,28]);
 assert(blt[5]>=6&&blt[5]+blt[3]===336&&blt[6]+blt[4]<=101);
 assert.strictEqual(h.contents,target);assert.equal(h.contents.fontBold,true);
 assert.deepEqual(Object.getOwnPropertyDescriptor(h,'wordwrapWidth'),descriptor);
 assert.equal(JSON.stringify(h._item),item);assert(f.probes[0].destroyed);
 h._checkWordWrapMode=true;h.drawTextEx(text,6,28);assert.equal(f.probes.length,1);
}
for(const mode of ['too-wide','too-tall','empty','edge','throw']){
 const f=fixture('rtl',mode),h=new f.Help(),target=h.contents;
 assert.throws(()=>h.drawTextEx(text,6,28),mode==='throw'?/native-rich-text-failure/:/RTL item help/);
 assert.strictEqual(h.contents,target);assert.equal(h._omoriHelpInkProbe,false);
 assert(!Object.hasOwn(h,'wordwrapWidth'));assert(f.probes[0].destroyed);
 assert.equal(f.calls.length,1); // No partial text copied on failure.
}
const ltr=fixture('ltr');assert.strictEqual(ltr.Help.prototype.drawTextEx,ltr.native);
const h=new ltr.Help();assert.equal(h.drawTextEx('A shiny new knife.',6,28),123);assert.equal(ltr.probes.length,0);
console.log('PASS RTL item help native text/argument delegation, unscaled ink placement beside icon, inherited/own width restoration, native failure cleanup, empty/clipped/overflow rejection and untouched LTR control; actual Canvas/fonts require native review.');
