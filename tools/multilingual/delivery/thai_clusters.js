/* Presentation only: submit a Thai base and its dependent signs together.
 * Native logical strings, escape dispatch, message indices and saves stay raw.
 */
(function(root){
  'use strict';
  var thai=/[\u0e00-\u0e7f]/;
  var dependent=/[\u0e31\u0e33-\u0e3a\u0e47-\u0e4e]/;
  function cluster(text,index){
    var end=index+1;
    if(!thai.test(text[index]||''))return '';
    while(end<text.length && dependent.test(text[end]))end++;
    return text.slice(index,end);
  }
  function shopFontSize(value,original,availableWidth,availableHeight,measure){
    // Native item help starts below its title at y24. <br> followed by a source
    // newline is one native rich-text break, not two. Measure the same clusters
    // used below, including automatic wraps, before choosing a bounded size.
    var lines=String(value).replace(/<br\s*\/?>(?:\r?\n)?/gi,'\n').replace(/<WordWrap>/gi,'').split(/\r?\n/);
    for(var size=original;size>=18;size--){
      var count=0;
      lines.forEach(function(line){
        var x=0;count++;
        for(var index=0;index<line.length;){
          var part=cluster(line,index)||line[index],w=measure(part,size);
          if(x>0&&x+w>availableWidth){count++;x=0;}
          x+=w;index+=part.length;
        }
      });
      if(count*Math.max(size+8,Math.ceil(size*1.35))<=availableHeight)return size;
    }
    return original; // Unknown oversized help retains its existing native path.
  }
  function install(env){
    if(env.OmoriLocale._thaiClustersInstalled)return;
    var base=env.Window_Base.prototype,original=base.processNormalCharacter;
    if(typeof original!=='function')throw new Error('Thai cluster renderer requires the pinned normal-character API');
    base.processNormalCharacter=function(state){
      var text=cluster(state.text,state.index);
      if(!text)return original.apply(this,arguments);
      var measured=this.textWidth(text),width=typeof this.wordwrapWidth==='function'?this.wordwrapWidth():this.contents.width;
      if(this._wordWrap && !this._checkWordWrapMode && state.x>(state.left||0) && measured>width-state.x){
        var index=state.index;this.processNewLine(state);state.index=index;return;
      }
      state.height=Math.max(state.height,Math.ceil(this.contents.fontSize*1.35));
      if(typeof this.canCreateLetterEffectSprite==='function' && this.canCreateLetterEffectSprite()){
        state._omoriRunText=text;
        try{this.createLetterEffectSprite(state);}finally{delete state._omoriRunText;}
      }else if(!this._checkWordWrapMode){
        var blocked=this.contents._blockTextDrawing;this.contents._blockTextDrawing=false;
        try{this.contents.drawText(text,state.x,state.y,Math.max(1,Math.ceil(measured)+2),state.height,'left');}
        finally{this.contents._blockTextDrawing=blocked;}
      }
      state.index+=text.length;state.x+=measured;
    };
    if(env.WindowItemShopMessage){
      var shop=env.WindowItemShopMessage.prototype,reset=shop.resetFontSettings;
      shop.resetFontSettings=function(){
        var result=reset.apply(this,arguments);
        if(this._drawingItemText&&this._itemListWindow){
          var item=this._itemListWindow.item(),win=this,originalSize=this.contents.fontSize;
          if(item&&thai.test(item.description||'')){
            var width=(typeof this.wordwrapWidth==='function'?this.wordwrapWidth():this.contents.width)-110;
            var selected=shopFontSize(item.description,originalSize,width,this.contents.height-24,function(part,size){win.contents.fontSize=size;return win.textWidth(part);});
            this.contents.fontSize=selected;
          }
        }
        return result;
      };
    }
    env.OmoriLocale._thaiClustersInstalled=true;
  }
  var api={install:install,cluster:cluster,shopFontSize:shopFontSize};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleThai=api;
}(typeof globalThis!=='undefined'?globalThis:this));
