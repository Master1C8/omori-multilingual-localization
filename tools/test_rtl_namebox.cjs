/* Native Canvas is replaced by a pixel rectangle fixture; real glyphs need QA. */
'use strict';
const assert=require('node:assert/strict');
const api=require('./multilingual/delivery/arabic_runs.js');
function fixture({inkWidth=24,inkHeight=18,empty=false,fail=false}={}) {
  const surfaces=[],calls=[];
  function Bitmap(w,h) {
    this.width=w;this.height=h;this.fontSize=20;this.paintOpacity=255;
    this.pixels=new Uint8ClampedArray(w*h*4);
    this._context={getImageData:()=>({data:this.pixels})};
    this._baseTexture={destroy:()=>{this.destroyed=true;}};surfaces.push(this);
  }
  Bitmap.prototype.drawText=function(text,x,y) {
    calls.push({text,x,y,bitmap:this});
    if(fail)throw new Error('native draw failed');
    if(empty)return;
    for(let py=y+24;py<y+24+inkHeight;py++)for(let px=x+4;px<x+4+inkWidth;px++)
      if(px>=0&&py>=0&&px<this.width&&py<this.height)this.pixels[(py*this.width+px)*4+3]=255;
  };
  Bitmap.prototype.blt=function(source,sx,sy,w,h,dx,dy) {
    this.blit={sx,sy,w,h,dx,dy};
    for(let y=0;y<h;y++)for(let x=0;x<w;x++)this.pixels[((dy+y)*this.width+dx+x)*4+3]=source.pixels[((sy+y)*source.width+sx+x)*4+3];
  };
  function Base(){}
  Base.prototype.processNormalCharacter=function(){};
  Base.prototype.calcTextHeight=function(){return 20;};
  function Name(){this.width=64;this.height=44;this.contents=new Bitmap(40,20);}
  Name.prototype=Object.create(Base.prototype);
  Name.prototype.createContents=function(){this.contents=new Bitmap(this.width-24,this.height-24);};
  Name.prototype.drawTextEx=function(text,x,y){this.contents.drawText(text,x,y);return 36;};
  const original=Name.prototype.drawTextEx;
  const env={Bitmap,Window_Base:Base,Window_NameBox:Name,OmoriLocale:{}};
  api.create({joining:false}).install(env);
  return {name:new Name(),surfaces,calls,original};
}
function ink(bitmap){let count=0;for(let i=3;i<bitmap.pixels.length;i+=4)if(bitmap.pixels[i])count++;return count;}
{
  const f=fixture(),name=f.name,target=name.contents,text='ماري';
  // The original draw baseline leaves only the last two bitmap rows visible.
  f.original.call(name,text,4,-6);assert.equal(ink(target),24*2);target.pixels.fill(0);
  assert.equal(name.drawTextEx(text,4,-6),36);
  assert.equal(ink(target),24*18);assert.equal(name.contents,target);
  assert.equal(name.width,64);assert.equal(name.height,44);
  assert.equal(target.blit.w,24);assert.equal(target.blit.h,18);
  assert.equal(f.calls.at(-1).text,'\u202b'+text+'\u202c');assert.equal(f.surfaces.at(-1).destroyed,true);
}
{
  const f=fixture({inkHeight:26}),name=f.name;
  name.drawTextEx('ماري',4,-6);
  assert.equal(ink(name.contents),24*26);assert.equal(name.height,52);
  assert.equal(name.contents.height,28);assert.equal(name.contents.fontSize,20);
  assert.equal(name.contents.blit.h,26); // No scaling to squeeze a tall glyph.
}
{
  const f=fixture(),name=f.name,target=name.contents;
  assert.equal(name.drawTextEx('ماري',0,target.height),36);
  assert.equal(f.surfaces.length,1);assert.equal(target.blit,undefined); // Native measurement path.
  assert.equal(name.drawTextEx('MARI',4,-6),36);
  assert.equal(f.surfaces.length,1);assert.equal(name.contents,target); // Latin positive control unchanged.
}
for(const options of [{empty:true},{fail:true}]) {
  const f=fixture(options),name=f.name,target=name.contents;
  assert.throws(()=>name.drawTextEx('ماري',4,-6),options.empty?/probe is empty or clipped/:/native draw failed/);
  assert.equal(name.contents,target);assert.equal(name._omoriNameInkProbe,false);
  assert.equal(f.surfaces.at(-1).destroyed,true);
}
console.log('RTL nameplate pixel-boundary fixtures passed; native glyph rendering not replaced by these tests.');
