/* Presentation only: preserve logical Hindi strings, indices, commands and saves.
 * Chromium's Canvas shaper receives intact runs instead of separate code units.
 * Runtime readability/input remain unverified under the owner's static-first scope.
 */
(function(root) {
  'use strict';
  var script=/[\u0900-\u097f]/;
  var mark=/[\u0900-\u0903\u093a-\u093c\u093e-\u094f\u0951-\u0957\u0962\u0963]/;
  var consonant=/[\u0915-\u0939\u0958-\u095f]/;
  var style=/^\x1b(?:C\[\d+\]|FS\[\d+\]|FN<[^>]*>|FB|FI|FR|[{}])/i;
  function lineHasScript(state) {
    if(!state || typeof state.text!=='string')return false;
    var previous=Math.max(0,state.index-1);
    var start=Math.max(state.text.lastIndexOf('\n',previous),state.text.lastIndexOf('\f',previous))+1;
    var end=state.text.slice(state.index).search(/[\n\f]/);
    return script.test(state.text.slice(start,end<0?state.text.length:state.index+end));
  }
  function run(state,measure,available,wrap) {
    var tail=state.text.slice(state.index),end=tail.search(/[\x1b\n\r\f]/);
    var text=end<0?tail:tail.slice(0,end),matches=[],m,re=/\s+/g;
    if(wrap && measure(text)>available) {
      while((m=re.exec(text)))matches.push(m.index+m[0].length);
      var selected='';
      for(var i=matches.length-1;i>=0;i--)if(measure(text.slice(0,matches[i]))<=available){selected=text.slice(0,matches[i]);break;}
      text=selected || text.slice(0,matches.length?matches[0]:text.length);
    }
    var rendered=text,borrowed=[],pos=state.index+text.length;
    // A style escape may occur inside a cluster (six actual source-bound cases).
    // Paint the complete cluster in its base style, dispatch each escape natively,
    // then skip only marks/conjunct members that have already been painted.
    while(text && script.test(rendered.slice(-1))) {
      var cursor=pos,hit;
      while((hit=style.exec(state.text.slice(cursor))))cursor+=hit[0].length;
      if(cursor===pos)break;
      var begin=cursor,last=rendered.slice(-1);
      while(cursor<state.text.length) {
        var c=state.text[cursor];
        if(mark.test(c) || (last==='\u094d' && consonant.test(c))) {
          rendered+=c;last=c;cursor++;
        } else break;
      }
      if(cursor===begin)break;
      borrowed.push({index:begin,length:cursor-begin});pos=cursor;
    }
    return {text:text,rendered:rendered,borrowed:borrowed};
  }
  function install(env) {
    if(env.OmoriLocale._devanagariRunsInstalled)return;
    var base=env.Window_Base.prototype,original=base.processNormalCharacter;
    function compactItemHelp(win) {
      return !!(env.WindowItemShopMessage && win instanceof env.WindowItemShopMessage && win._drawingItemText);
    }
    if(typeof original!=='function')throw new Error('Hindi contextual renderer requires the pinned normal-character API');
    base.processNormalCharacter=function(state) {
      if(state._omoriIndicSkipSource!==state.text){state._omoriIndicSkipSource=state.text;state._omoriIndicSkips={};}
      var skipped=state._omoriIndicSkips[state.index];
      if(skipped){delete state._omoriIndicSkips[state.index];state.index+=skipped;return;}
      if(!lineHasScript(state))return original.apply(this,arguments);
      var width=typeof this.wordwrapWidth==='function'?this.wordwrapWidth():this.contents.width;
      var wrap=!!this._wordWrap && !this._checkWordWrapMode,left=state.left || 0;
      var result=run(state,this.textWidth.bind(this),Math.max(0,width-state.x),wrap);
      if(!result.text)return original.apply(this,arguments);
      var measured=this.textWidth(result.rendered);
      if(wrap && state.x>left && measured>width-state.x) {
        var index=state.index;this.processNewLine(state);state.index=index;return;
      }
      // Keep the compact shop's native leading inside its fixed help band.
      // Full contextual runs and their glyph sizes are preserved.
      if(!compactItemHelp(this))state.height=Math.max(state.height,Math.ceil(this.contents.fontSize*1.35));
      var effect=typeof this.canCreateLetterEffectSprite==='function' && this.canCreateLetterEffectSprite();
      if(effect) {
        state._omoriRunText=result.rendered;
        try {this.createLetterEffectSprite(state);} finally {delete state._omoriRunText;}
      } else {
        var blocked=this.contents._blockTextDrawing;this.contents._blockTextDrawing=false;
        try {this.contents.drawText(result.rendered,state.x,state.y,Math.max(1,Math.ceil(measured)+2),state.height,'left');}
        finally {this.contents._blockTextDrawing=blocked;}
      }
      result.borrowed.forEach(function(row){state._omoriIndicSkips[row.index]=row.length;});
      state.index+=result.text.length;state.x+=measured;
    };
    var depth=0;
    [env.Window_Base,env.Window_Message,env.Window_ChoiceList,env.Window_ScrollingTextSource].forEach(function(type) {
      if(!type || !Object.prototype.hasOwnProperty.call(type.prototype,'calcTextHeight'))return;
      var originalHeight=type.prototype.calcTextHeight;
      type.prototype.calcTextHeight=function(state) {
        var height;depth++;
        try {height=originalHeight.apply(this,arguments);} finally {depth--;}
        return depth===0 && lineHasScript(state) && !compactItemHelp(this)?Math.max(height,Math.ceil(height*1.35),Math.ceil(this.contents.fontSize*1.35)):height;
      };
    });
    env.OmoriLocale._devanagariRunsInstalled=true;
  }
  function refreshName(window) {
    var contents=window.contents,text=window._text.join('');
    contents.clearRect(0,34,contents.width,contents.height-34);contents.fontSize=24;
    contents.drawText(text,6,34,contents.width-12,32,'left');
    for(var i=0;i<window._text.length;i++) {
      contents.paintOpacity=window._textIndex===i?255:100;
      contents.fillRect(6+i*23,66,20,2,'rgba(255,255,255,1)');
    }
    contents.paintOpacity=255;
  }
  var api={install:install,refreshName:refreshName,run:run,lineHasScript:lineHasScript};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.OmoriLocaleDevanagari=api;
}(typeof globalThis!=='undefined'?globalThis:this));
