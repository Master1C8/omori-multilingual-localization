// Temporary diagnostic only: delegate native rendering exactly and record calls.
(function(){
 var fs=require('fs'),rows=[],installed=false,last=0,probeDone=false;
 function row(layer,b,text,x,y,width,height,align){
  if(!SceneManager._scene||SceneManager._scene.constructor.name!=='Scene_OmoriItemShop'||rows.length>=150)return;
  var c=b._context,v={layer:layer,time:Date.now(),text:String(text),x:x,y:y,width:width,height:height,align:align,bitmapWidth:b.width,bitmapHeight:b.height,fontFace:b.fontFace,fontSize:b.fontSize,blocked:b._blockTextDrawing,contextFont:c.font,contextAlign:c.textAlign,globalAlpha:c.globalAlpha};
  if(layer==='body'&&c.textAlign==='right'){
   var canvas=document.createElement('canvas');canvas.width=2400;canvas.height=240;var probe=canvas.getContext('2d');probe.font=c.font;probe.textAlign=c.textAlign;probe.textBaseline=c.textBaseline;probe.fillStyle='white';probe.fillText(text,1200,120,width);
   var pixels=probe.getImageData(0,0,canvas.width,canvas.height).data,left=canvas.width,right=-1;
   for(var i=3;i<pixels.length;i+=4)if(pixels[i]){var px=((i-3)/4)%canvas.width;left=Math.min(left,px);right=Math.max(right,px);}
   v.measured=c.measureText(text).width;v.privateInkAt1200=[left,right];
  }
  rows.push(v);
 }
 var timer=setInterval(function(){try{
  if(!installed&&typeof Bitmap!=='undefined'&&Bitmap.prototype){
   installed=true;var draw=Bitmap.prototype.drawText,body=Bitmap.prototype._drawTextBody;
   Bitmap.prototype.drawText=function(text,x,y,width,height,align){row('call',this,text,x,y,width,height,align);return draw.apply(this,arguments);};
   Bitmap.prototype._drawTextBody=function(text,x,y,width){row('body',this,text,x,y,width,null,this._context.textAlign);return body.apply(this,arguments);};
  }
  if(installed&&!probeDone&&SceneManager._scene&&SceneManager._scene.constructor.name==='Scene_OmoriTitleScreen'&&SceneManager._sceneStarted){
   probeDone=true;var b=new Bitmap(230,64);b.fontFace='GameFont, Verdana, Arial, Courier New';b.fontSize=20;b.drawText('25 C',42,0,190,27,'right');
   var actual=b._context.getImageData(0,0,b.width,b.height).data,count=0;for(var i=3;i<actual.length;i+=4)if(actual[i])count++;
   fs.writeFileSync(__STATE_PATH__+'.shop-title-probe.json',JSON.stringify({time:Date.now(),priceFormatted:'%1 %2'.format(25,'C'),ownedFormatted:'(%1: %2)'.format(LanguageManager.getPluginText('itemShopMenu','ownedText'),0),formatSource:String.prototype.format.toString(),rightLiteralInkPixels:count,font:b._context.font}));
   fs.writeFileSync(__STATE_PATH__+'.shop-title-probe.png',Buffer.from(b._canvas.toDataURL('image/png').split(',')[1],'base64'));if(b._baseTexture)b._baseTexture.destroy();
  }
  if(rows.length!==last){last=rows.length;var p=__STATE_PATH__+'.shop-draw.json';fs.writeFileSync(p+'.tmp',JSON.stringify(rows));fs.renameSync(p+'.tmp',p);}
 }catch(error){fs.writeFileSync(__STATE_PATH__+'.shop-draw.error',String(error.stack||error));}},200);
})();
