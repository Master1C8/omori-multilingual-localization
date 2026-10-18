/* Private, detached Canvas evidence; no annotations or game-state commands. */
(function(){
 var code=__QA_LOCALE__,files={ar:'Locale-Arabic-Primary.ttf',fa:'Locale-Arabic-Primary.ttf',he:'Locale-Hebrew-Primary.ttf'};
 if(!files[code])return;
 var timer=setInterval(function(){
  if(typeof SceneManager==='undefined'||!SceneManager._scene||SceneManager._scene.constructor.name!=='Scene_OmoriTitleScreen')return;
  clearInterval(timer);
  function face(name,file){var f=new FontFace(name,'url("fonts/'+file+'")');return f.load().then(function(v){document.fonts.add(v);});}
  function render(family,value){
   var c=document.createElement('canvas');c.width=800;c.height=220;var x=c.getContext('2d');x.font='40px '+family;x.fillStyle='white';x.fillText(value,80,140);
   var d=x.getImageData(0,0,800,220).data,b=[800,220,-1,-1];
   for(var i=0;i<d.length;i+=4)if(d[i+3]){var p=i/4,xx=p%800,yy=Math.floor(p/800);b=[Math.min(b[0],xx),Math.min(b[1],yy),Math.max(b[2],xx),Math.max(b[3],yy)];}
   return {sha256:require('crypto').createHash('sha256').update(Buffer.from(d)).digest('hex'),bounds:b,advance:x.measureText(value).width};
  }
  Promise.all([face('QA_Script',files[code]),face('QA_Native','OMORI_GAME2.ttf')]).then(function(){
   var caption=String(LanguageManager.getMessageData('XX_BLUE.Omori_Title_Screen').commands[1]),hit=caption.match(/[\u0590-\u08ff]+/);if(!hit)throw new Error('Expected RTL caption');
   var actual=render('GameFont',hit[0]),derived=render('QA_Script',hit[0]),fallback=render('QA_Native',hit[0]),latin=render('GameFont','O'),nativeLatin=render('QA_Native','O');
   window.__qaFontProbe={status:actual.sha256===derived.sha256&&actual.sha256!==fallback.sha256&&latin.sha256===nativeLatin.sha256&&actual.bounds[0]>0&&actual.bounds[2]<799&&actual.bounds[2]>actual.bounds[0]?'passed':'failed',locale:code,fontFile:files[code],caption:caption,sample:hit[0],actual:actual,derived:derived,uncontrolledFallback:fallback,originalLatin:latin,nativeLatin:nativeLatin,boundary:'Actual native Canvas glyph pixel identity; detached canvases, no visible UI changes'};
  }).catch(function(e){window.__qaFontProbe={status:'error',message:String(e)};});
 },200);
})();
