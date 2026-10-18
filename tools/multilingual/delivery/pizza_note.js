/* Text-only pizza-note presentation; native house selection and images stay raw. */
(function(root){
  'use strict';
  function linesFor(text, measure, width) {
    var lines=[];
    String(text).split(/\r?\n/).forEach(function(paragraph){
      var line='';
      paragraph.split(/\s+/).filter(Boolean).forEach(function(word){
        if(measure(word)>width) {
          if(line){lines.push(line);line='';}
          Array.from(word).forEach(function(char){
            if(measure(char)>width)throw new Error('Locale pizza note glyph exceeds available width');
            if(line && measure(line+char)>width){lines.push(line);line='';}
            line+=char;
          });
        } else if(line && measure(line+' '+word)>width) {
          lines.push(line);line=word;
        } else line+=(line?' ':'')+word;
      });
      lines.push(line);
    });
    return lines;
  }
  function render(window, text) {
    var contents=window.contents;
    var width=Math.min(580,contents.width-24)-24;
    var height=contents.height-32;
    if(width<=0 || height<=0)throw new Error('Locale pizza note has no usable content area');
    window.resetFontSettings();
    var lines,size,lineHeight;
    for(size=32;size>=18;size-=2) {
      contents.fontSize=size;
      lines=linesFor(text,function(value){return window.textWidth(value);},width);
      lineHeight=size===32?64:size*2;
      if(lines.length*lineHeight<=height)break;
    }
    if(size<18)throw new Error('Locale pizza note text does not fit the original note window');
    contents.clear();window.visible=true;
    var bitmap=root.ImageManager.loadPicture('PIZZA-Background');
    contents.blt(bitmap,0,0,bitmap.width,bitmap.height,0,0);
    // Native text uses the GameFont face and its configured locale fallback.
    // Keep the original 24/32 inset and 580px right boundary; no word sprites.
    var previousColor=contents.textColor,previousOutline=contents.outlineWidth;
    contents.textColor='#000000';contents.outlineWidth=0;
    try {
      lines.forEach(function(line,index){
        contents.drawText(line,24,32+index*lineHeight,width,lineHeight,'left');
      });
    } finally {contents.textColor=previousColor;contents.outlineWidth=previousOutline;}
    return {lines:lines,fontSize:size,lineHeight:lineHeight,width:width};
  }
  var api={render:render,linesFor:linesFor};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocalePizzaNote=api;
}(typeof globalThis!=='undefined'?globalThis:this));
