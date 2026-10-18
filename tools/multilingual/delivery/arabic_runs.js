/* Arabic presentation only. Logical strings, commands and game identifiers stay intact.
 * Canvas receives contextual runs; it owns joining, marks and bidi inside each run.
 * Native escape commands remain separate steps. Typewriter/effect granularity is a run.
 * This adapter is a static candidate, not evidence of in-game readability.
 */
(function(root) {
  'use strict';
  function create(options) {
  options=options || {};
  var marker=options.marker || '_arabicRunsInstalled';
  var arabic=options.scriptPattern || /[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]/;
  var transparentControls=/\x1b(?:C\[\d+\]|COM\[\d+\]|QUAKE\[\d+\]|SINV?\[\d+\]|FN<[^>]*>|FS\[\d+\]|MSGCORE\[\d+\]|FB|FI|FR|OOOO|[.!^><{}|$])/gi;
  function contextualText(state,text,joining) {
    function edge(value,reverse) {
      var chars=Array.from(value.replace(transparentControls,''));
      if(reverse)chars.reverse();
      for(var i=0;i<chars.length;i++)if(joining.type(chars[i])!=='T')return chars[i];
      return '';
    }
    function connects(left,right) {
      return 'DLC'.indexOf(joining.type(left))>=0 && 'DRC'.indexOf(joining.type(right))>=0;
    }
    var before=edge(state.text.slice(0,state.index),true),first=edge(text,false);
    var last=edge(text,true),after=edge(state.text.slice(state.index+text.length),false);
    return (connects(before,first)?'\u200d':'')+text+(connects(last,after)?'\u200d':'');
  }
  function lineHasArabic(state) {
    if(!state || typeof state.text!=='string')return false;
    var previous=Math.max(0,state.index-1);
    var start=Math.max(state.text.lastIndexOf('\n',previous),state.text.lastIndexOf('\f',previous))+1;
    var end=state.text.slice(state.index).search(/[\n\f]/);
    return arabic.test(state.text.slice(start,end<0?state.text.length:state.index+end));
  }
  function contextualRun(state, measure, available, wrap) {
    var tail=state.text.slice(state.index), end=tail.search(/[\x1b\n\r\f]/);
    var text=end<0?tail:tail.slice(0,end);
    if(!text || !wrap || measure(text)<=available)return text;
    // Never split an Arabic word or its combining marks into isolated glyph calls.
    var breaks=[],match,re=/\s+/g;
    while((match=re.exec(text)))breaks.push(match.index+match[0].length);
    for(var i=breaks.length-1;i>=0;i--) {
      var prefix=text.slice(0,breaks[i]);
      if(measure(prefix)<=available)return prefix;
    }
    // An overlong word stays whole. Canvas receives its real width, without distortion.
    return text.slice(0,breaks.length?breaks[0]:text.length);
  }
  function install(env) {
    if(env.OmoriLocale[marker])return;
    var joining=options.joining===false?null:env.OmoriArabicJoining;
    if(options.joining!==false && (!joining || typeof joining.type!=='function'))throw new Error('Arabic contextual runs require the pinned Unicode joining table');
    var base=env.Window_Base.prototype, bitmap=env.Bitmap.prototype;
    function compactItemHelp(win) {
      return !!(env.WindowItemShopMessage && win instanceof env.WindowItemShopMessage && win._drawingItemText);
    }
    var originalCharacter=base.processNormalCharacter, originalDraw=bitmap.drawText;
    if(typeof originalCharacter!=='function' || typeof originalDraw!=='function')
      throw new Error('Arabic contextual-run renderer requires the pinned window/bitmap APIs');
    bitmap.drawText=function(text,x,y,width,height,align) {
      var rtl=this._omoriRtlRun || arabic.test(String(text));
      if(!rtl)return originalDraw.apply(this,arguments);
      // Chromium65 gates context.direction behind ExperimentalCanvasFeatures.
      // Its native DrawBidiText already handles Unicode embeddings. These default
      // ignorable controls need no font glyph and never enter stored game text.
      var args=Array.prototype.slice.call(arguments);
      args[0]='\u202b'+String(text)+'\u202c';
      return originalDraw.apply(this,args);
    };
    base.processNormalCharacter=function(state) {
      if(!lineHasArabic(state))return originalCharacter.apply(this,arguments);
      var left=state.left || 0, width=typeof this.wordwrapWidth==='function'?this.wordwrapWidth():this.contents.width;
      var wrap=!!this._wordWrap && !this._checkWordWrapMode;
      var text=contextualRun(state,this.textWidth.bind(this),Math.max(0,width-state.x),wrap);
      if(!text)return originalCharacter.apply(this,arguments);
      var rendered=joining?contextualText(state,text,joining):text,measured=this.textWidth(rendered);
      if(wrap && state.x>left && measured>width-state.x) {
        var index=state.index;
        this.processNewLine(state);
        state.index=index; // A soft wrap consumes no logical character or escape command.
        return;
      }
      // Item-shop descriptions share a fixed 72px band with native paging.
      // Preserve its native leading; dialogue's extra leading would page after
      // the first line. Contextual shaping and glyph sizes remain unchanged.
      if(!compactItemHelp(this))state.height=Math.max(state.height,Math.ceil(this.contents.fontSize*1.65));
      var logicalX=state.x, physicalX=width-logicalX-measured;
      var effect=typeof this.canCreateLetterEffectSprite==='function' && this.canCreateLetterEffectSprite();
      if(effect) {
        state._omoriRunText=rendered;state.x=physicalX;
        try {this.createLetterEffectSprite(state);} finally {delete state._omoriRunText;state.x=logicalX;}
      } else {
        var blocked=this.contents._blockTextDrawing, forced=this.contents._omoriRtlRun;
        this.contents._blockTextDrawing=false;this.contents._omoriRtlRun=true;
        try {this.contents.drawText(rendered,physicalX,state.y,Math.max(1,Math.ceil(measured)+2),state.height,'left');}
        finally {this.contents._blockTextDrawing=blocked;this.contents._omoriRtlRun=forced;}
      }
      state.index+=text.length;state.x=logicalX+measured;
    };
    var originalIcon=base.processDrawIcon;
    if(typeof originalIcon==='function')base.processDrawIcon=function(icon,state) {
      if(!lineHasArabic(state))return originalIcon.apply(this,arguments);
      var x=state.x, advance=env.Window_Base._iconWidth+4;
      var width=typeof this.wordwrapWidth==='function'?this.wordwrapWidth():this.contents.width;
      var physical=width-x-advance;state.x=physical;
      try {return originalIcon.apply(this,arguments);} finally {state.x=x+(state.x-physical);}
    };
    var heightDepth=0;
    [env.Window_Base,env.Window_Message,env.Window_ChoiceList,env.Window_ScrollingTextSource].forEach(function(type) {
      if(!type || !Object.prototype.hasOwnProperty.call(type.prototype,'calcTextHeight'))return;
      var original=type.prototype.calcTextHeight;
      type.prototype.calcTextHeight=function(state) {
        var height;heightDepth++;
        try {height=original.apply(this,arguments);} finally {heightDepth--;}
        return heightDepth===0 && lineHasArabic(state) && !compactItemHelp(this)?Math.max(height,Math.ceil(height*1.65),Math.ceil(this.contents.fontSize*1.65)):height;
      };
    });
    // NameBox is a compact single-line bitmap. The dialogue leading above can
    // put its baseline below that bitmap. Render through the unchanged native
    // rich-text path on a detached surface, then place all actual ink in the
    // nameplate without scaling glyphs or rewriting the logical name.
    if(env.Window_NameBox) {
      var name=env.Window_NameBox.prototype, originalName=name.drawTextEx;
      name.drawTextEx=function(text,x,y) {
        if(!arabic.test(String(text)) || this._checkWordWrapMode || y>=this.contents.height || this._omoriNameInkProbe)
          return originalName.apply(this,arguments);
        var target=this.contents, margin=Math.ceil(target.fontSize*6);
        var probe=new env.Bitmap(target.width+margin*2,target.height+margin*2);
        var fields=['fontFace','fontSize','fontBold','fontItalic','textColor','outlineColor','outlineWidth','paintOpacity'];
        fields.forEach(function(k){probe[k]=target[k];});
        var advance;
        try {
          this._omoriNameInkProbe=true;
          try {
            this.contents=probe;
            advance=originalName.call(this,text,margin,margin);
          } finally {this.contents=target;this._omoriNameInkProbe=false;}
          var pixels=probe._context.getImageData(0,0,probe.width,probe.height).data;
          var left=probe.width,right=-1,top=probe.height,bottom=-1;
          for(var i=3;i<pixels.length;i+=4)if(pixels[i]) {
            var px=((i-3)/4)%probe.width,py=Math.floor((i-3)/4/probe.width);
            left=Math.min(left,px);right=Math.max(right,px);top=Math.min(top,py);bottom=Math.max(bottom,py);
          }
          if(right<left || left===0 || top===0 || right===probe.width-1 || bottom===probe.height-1)
            throw new Error('RTL nameplate ink probe is empty or clipped');
          var inkWidth=right-left+1,inkHeight=bottom-top+1;
          var extraWidth=Math.max(0,inkWidth+4-target.width),extraHeight=Math.max(0,inkHeight+2-target.height);
          if(extraWidth || extraHeight) {
            this.width+=extraWidth;this.height+=extraHeight;this.createContents();target=this.contents;
          }
          fields.forEach(function(k){target[k]=probe[k];});
          target.blt(probe,left,top,inkWidth,inkHeight,Math.floor((target.width-inkWidth)/2),Math.floor((target.height-inkHeight)/2));
          return advance;
        } finally {if(probe._baseTexture)probe._baseTexture.destroy();}
      };
    }
    env.OmoriLocale[marker]=true;
  }
  function refreshName(window) {
    var contents=window.contents, text=window._text.join('');
    contents.clearRect(0,34,contents.width,contents.height-34);
    contents.fontSize=24;
    contents.drawText(text,6,34,contents.width-12,28,'right');
    for(var i=0;i<window._text.length;i++) {
      contents.paintOpacity=window._textIndex===i?255:100;
      contents.fillRect(contents.width-6-(i+1)*23,62,20,2,'rgba(255,255,255,1)');
    }
    contents.paintOpacity=255;
  }
  return {install:install,refreshName:refreshName,contextualRun:contextualRun,contextualText:contextualText,transparentControlPattern:transparentControls.source,lineHasArabic:lineHasArabic};
  }
  var api=create();api.create=create;
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleArabic=api;
}(typeof globalThis!=='undefined'?globalThis:this));
