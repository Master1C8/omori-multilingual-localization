/* Temporary diagnostic: observe real bitmap calls and private Canvas ink bounds. */
(function(){
 var installed=false,rows=[];
 var timer=setInterval(function(){
  if(installed || typeof SceneManager==='undefined' || !SceneManager._scene || SceneManager._scene.constructor.name!=='Scene_OmoriTitleScreen')return;
  installed=true;clearInterval(timer);
  var original=Bitmap.prototype._drawTextBody;
  Bitmap.prototype._drawTextBody=function(text,tx,ty,maxWidth){
   if(SceneManager._scene && SceneManager._scene.constructor.name==='Scene_OmoriFile' && /[\u0600-\u06ff]/.test(String(text)) && rows.length<80){
    try{
     var source=this._context,c=document.createElement('canvas');c.width=1600;c.height=240;
     var x=c.getContext('2d');x.font=source.font;x.textAlign=source.textAlign;x.textBaseline=source.textBaseline;x.fillStyle='white';x.fillText(text,1000,120,maxWidth);
     var d=x.getImageData(0,0,c.width,c.height).data,b=[1600,240,-1,-1];
     for(var i=0;i<d.length;i+=4)if(d[i+3]){var p=i/4,xx=p%c.width,yy=Math.floor(p/c.width);b=[Math.min(b[0],xx),Math.min(b[1],yy),Math.max(b[2],xx),Math.max(b[3],yy)];}
     rows.push({text:String(text),tx:tx,ty:ty,maxWidth:maxWidth,bitmapWidth:this.width,canvasWidth:source.canvas.width,font:source.font,align:source.textAlign,measured:source.measureText(text).width,inkBoundsAt1000:b,translatedInkBounds:[b[0]+tx-1000,b[2]+tx-1000]});
     require('fs').writeFileSync(__STATE_PATH__+'.layout.json',JSON.stringify(rows,null,2));
    }catch(e){console.error('QA layout probe',e);}
   }
   return original.apply(this,arguments);
  };
 },200);
})();
