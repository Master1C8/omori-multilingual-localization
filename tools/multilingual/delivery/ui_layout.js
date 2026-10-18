/* Presentation geometry only. Logical strings, slot data and save APIs stay raw. */
(function(root) {
  'use strict';
  var env, rtl=false, inkCache=Object.create(null);
  function text(value) {return value==null?'':String(value);}
  function width(bitmap,value) {return Math.ceil(bitmap.measureTextWidth(text(value)));}
  function drawRightInk(b,value,right,y,w,height) {
    // Chromium65 can place RTL ink beyond its advance-aligned right anchor.
    // Probe the same Bitmap renderer; keep this cache local to the installed UI.
    var key=JSON.stringify([b.fontFace,b.fontSize,b.fontBold,b.fontItalic,value,w,height]);
    var offset=inkCache[key];
    if(offset===undefined) {
      var margin=Math.ceil(b.fontSize*12),anchor=margin+w;
      var probe=new env.Bitmap(anchor+margin,Math.ceil(b.fontSize*6));
      ['fontFace','fontSize','fontBold','fontItalic'].forEach(function(k){probe[k]=b[k];});
      probe.textColor='#ffffff';probe.outlineWidth=0;
      probe.drawText(value,anchor-w,b.fontSize*2,w,height,'right');
      var pixels=probe._context.getImageData(0,0,probe.width,probe.height).data;
      var first=probe.width,last=-1;
      for(var i=3;i<pixels.length;i+=4)if(pixels[i]) {
        var x=((i-3)/4)%probe.width;first=Math.min(first,x);last=Math.max(last,x);
      }
      if(probe._baseTexture)probe._baseTexture.destroy();
      if(last<first || first===0 || last===probe.width-1 || last-first+1>w+2)
        throw new Error('RTL file label ink exceeds its measured probe bounds');
      offset=last-anchor;inkCache[key]=offset;
    }
    b.drawText(value,right-1-offset-w,y,w,height,'right');
  }
  function sized(bitmap,parts,available,draw,allowCondensed) {
    var original=bitmap.fontSize, size=original, minimum=Math.min(original,18);
    function total() {return parts.reduce(function(n,p){return n+width(bitmap,p);},0)+(parts.length-1)*8;}
    try {
      while(total()>available && size>minimum)bitmap.fontSize=--size;
      if(total()>available && !allowCondensed)throw new Error('Localized file row exceeds its measured bounds');
      draw();
    } finally {bitmap.fontSize=original;}
  }
  function drawFileHeader(win,prefix,info,x,y,height) {
    var b=win.contents, chapter='';
    if(info)chapter=env.LanguageManager.getMessageData('XX_BLUE.Chapter_Names')[info.chapter]||info.chapter;
    prefix=text(prefix);chapter=text(chapter);
    var left=x,right=b.width-8;
    sized(b,[prefix,chapter],right-left,function() {
      var pw=width(b,prefix),cw=width(b,chapter);
      if(rtl) {
        drawRightInk(b,prefix,right,y,pw+1,height);
        if(chapter)b.drawText(chapter,left,y,Math.max(cw,right-pw-8-left),height,'left');
      } else {
        b.drawText(prefix,left,y,pw+1,height,'left');
        if(chapter)b.drawText(chapter,left+pw+8,y,right-left-pw-8,height,'left');
      }
    });
  }
  function drawFilePair(win,label,value,y,height) {
    var b=win.contents,left=118,right=b.width-8;
    label=text(label);value=text(value);
    sized(b,[label,value],right-left,function() {
      var lw=width(b,label),vw=width(b,value);
      if(rtl) {
        drawRightInk(b,label,right,y,lw+1,height);
        b.drawText(value,left,y,right-left-lw-8,height,'left');
      } else {
        b.drawText(label,left,y,lw+1,height,'left');
        b.drawText(value,left+lw+8,y,right-left-lw-8,height,'right');
      }
    });
  }
  function drawFileLevel(win,label,value,y,height) {
    var b=win.contents,right=b.width-8;
    label=text(label);value=text(value);
    sized(b,[label,value],b.width-230,function() {
      var lw=width(b,label),vw=width(b,value),left=right-lw-vw-8;
      if(rtl) {
        b.drawText(value,left,y,vw+1,height,'left');
        drawRightInk(b,label,right,y,lw+1,height);
      } else {
        b.drawText(label,left,y,lw+1,height,'left');
        b.drawText(value,right-vw,y,vw+1,height,'right');
      }
    });
  }
  function configure(target,options) {
    env=target;rtl=options.direction==='rtl';inkCache=Object.create(null);
  }
  function drawQuestLabel(win,value,x,y,available,height,align,allowCondensed) {
    var b=win.contents;
    value=text(value);available=Math.min(available,b.width-x-8);
    if(available<=0)throw new Error('Localized quest label has no drawable bounds');
    sized(b,[value],available,function() {
      if(rtl) {
        var measured=width(b,value);
        if(allowCondensed)measured=Math.min(measured,available-1);
        var right=align==='center'?x+(available+measured)/2:x+available;
        drawRightInk(b,value,right,y,measured+1,height);
      } else b.drawText(value,x,y,available,height,align||'left');
    },allowCondensed);
  }
  function installQuests() {
    if(env.Window_OmoriQuestHeader)env.Window_OmoriQuestHeader.prototype.refresh=function() {
      this.contents.clear();
      drawQuestLabel(this,env.LanguageManager.getPluginText('questMenu','header'),8,-6,this.contents.width-16,this.contents.height,'center');
    };
    [env.Window_OmoriQuestTypes,env.Window_OmoriQuestList,env.Window_MenuCommand].forEach(function(type) {
      if(!type)return;
      // Keep native command colors, opacity, cursor geometry and command logic.
      // The last main-menu field extends beyond the actual contents bitmap;
      // bound its text to the remaining drawable width just like quest labels.
      type.prototype.drawText=function(value,x,y,maximum,align) {
        // A single menu caption can use Bitmap's native horizontal fitting at
        // the minimum readable height. Multi-part save rows remain strict.
        drawQuestLabel(this,value,x,y,maximum,this.lineHeight(),align,type===env.Window_MenuCommand);
      };
    });
  }
  function installItemHelp() {
    if(!rtl || !env.Window_OmoMenuHelp)return;
    var help=env.Window_OmoMenuHelp.prototype,original=help.drawTextEx;
    help.drawTextEx=function(value,x,y) {
      if(!value || !this._item || this._checkWordWrapMode || this._omoriHelpInkProbe)
        return original.apply(this,arguments);
      // The native help bitmap includes the icon column. Its rich-text path
      // also uses advance-based RTL placement, which is not an ink boundary in
      // Chromium65. Render unchanged rich text with the native renderer, then
      // place its actual ink inside the description column without scaling.
      var target=this.contents,right=target.width-106*this._iconRate-8;
      var available=right-x,margin=Math.ceil(target.fontSize*12);
      if(available<=0 || y>=target.height)throw new Error('RTL item help has no drawable bounds');
      var probe=new env.Bitmap(target.width+margin*2,target.height+margin*2);
      var fields=['fontFace','fontSize','fontBold','fontItalic','textColor','outlineColor','outlineWidth','paintOpacity'];
      fields.forEach(function(k){probe[k]=target[k];});
      var own=Object.getOwnPropertyDescriptor(this,'wordwrapWidth'),advance;
      try {
        probe._context.translate(margin,margin);
        this.contents=probe;this._omoriHelpInkProbe=true;
        this.wordwrapWidth=function(){return right;};
        try {advance=original.apply(this,arguments);}
        finally {
          this.contents=target;this._omoriHelpInkProbe=false;
          if(own)Object.defineProperty(this,'wordwrapWidth',own);else delete this.wordwrapWidth;
        }
        var pixels=probe._context.getImageData(0,0,probe.width,probe.height).data;
        var left=probe.width,last=-1,top=probe.height,bottom=-1;
        for(var i=3;i<pixels.length;i+=4)if(pixels[i]) {
          var px=((i-3)/4)%probe.width,py=Math.floor((i-3)/4/probe.width);
          left=Math.min(left,px);last=Math.max(last,px);top=Math.min(top,py);bottom=Math.max(bottom,py);
        }
        if(last<left || left===0 || top===0 || last===probe.width-1 || bottom===probe.height-1)
          throw new Error('RTL item help ink probe is empty or clipped');
        var w=last-left+1,h=bottom-top+1;
        if(w>available || h>target.height-y)throw new Error('RTL item help exceeds its description column');
        target.blt(probe,left,top,w,h,right-w,y);
        fields.forEach(function(k){target[k]=probe[k];});
        return advance;
      } finally {if(probe._baseTexture)probe._baseTexture.destroy();}
    };
  }
  function install(target,options) {
    configure(target,options);
    installQuests();
    installItemHelp();
    if(rtl) {
      // The narrow native command field also compresses long RTL captions.
      // Align their rendered ink inside the field, preserving its native size.
      env.Window_OmoriFileCommand.prototype.drawItem=function(index) {
        var rect=this.itemRectForText(index);
        this.resetTextColor();this.changePaintOpacity(this.isCommandEnabled(index));
        drawRightInk(this.contents,this.commandName(index),rect.x+rect.width,
          rect.y,rect.width,this.lineHeight());
      };
    }
    var scene=env.Scene_OmoriTitleScreen.prototype, create=scene.createTitleCommands;
    var box=env.Window_OmoTitleScreenBox.prototype, refresh=box.refresh;
    box.refresh=function() {
      refresh.apply(this,arguments);
      if(this._localeTitleSize) {
        this.contents.clear();this.contents.fontSize=this._localeTitleSize;
        this.changePaintOpacity(this._enabled);
        var p=env.LanguageManager.getMessageData('XX_BLUE.Window_OmoTitleScreenBox').refresh_drawText_position;
        this.drawText(this._text,p[0],p[1],this.contents.width,'center');
      }
    };
    scene.createTitleCommands=function() {
      var result=create.apply(this,arguments),windows=this._titleCommands;
      var size=Number(env.LanguageManager.getMessageData('XX_BLUE.Window_OmoTitleScreenBox').refresh_contents_fontsize);
      var gap=36,available=env.Graphics.width-50-gap*(windows.length-1),sizes;
      function measure() {
        return windows.map(function(w) {
          w.contents.fontSize=size;
          return Math.ceil(w.contents.measureTextWidth(w._text))+w.standardPadding()*6;
        });
      }
      sizes=measure();
      while(sizes.reduce(function(a,b){return a+b;},0)>available && size>28) {size--;sizes=measure();}
      var total=sizes.reduce(function(a,b){return a+b;},0)+gap*(windows.length-1);
      if(total>env.Graphics.width-50)throw new Error('Localized title commands exceed measured bounds');
      var x=Math.max(40,Math.floor((env.Graphics.width-total)/2));
      if(x+total>env.Graphics.width-10)x=env.Graphics.width-10-total;
      windows.forEach(function(w,i) {
        w._localeTitleSize=size;w.width=sizes[i];w.createContents();w.x=x;w.refresh();x+=sizes[i]+gap;
      });
      return result;
    };
  }
  var api={configure:configure,install:install,installItemHelp:installItemHelp,drawFileHeader:drawFileHeader,drawFilePair:drawFilePair,drawFileLevel:drawFileLevel};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleUI=api;
}(typeof globalThis!=='undefined'?globalThis:this));
