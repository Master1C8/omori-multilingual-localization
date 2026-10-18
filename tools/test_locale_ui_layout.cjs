/* Geometry regression only. Native Canvas/font rendering is verified separately. */
'use strict';
const assert=require('assert');
const ui=require('./multilingual/delivery/ui_layout.js');
function bitmap(width=430){return {width,fontSize:24,calls:[],measureTextWidth(t){return String(t).length*this.fontSize/2;},drawText(t,x,y,w,h,align){this.calls.push({text:String(t),x,y,w,h,align,size:this.fontSize});},clear(){}};}
function setup(direction,commands=['NEW GAME LONG','CONTINUE','OPTIONS']){
 function InkProbe(w,h){this.width=w;this.height=h;this._context={getImageData:()=>{
  const data=new Uint8ClampedArray(w*h*4),right=Math.round(this.anchor+25),left=right-this.inkWidth+1;
  data[(w+left)*4+3]=255;data[(w+right)*4+3]=255;return {data};
 }};}
 InkProbe.prototype.drawText=function(t,x,y,w,h,align){assert.equal(align,'right');this.anchor=x+w;this.inkWidth=Math.max(1,Math.floor(w-1));};
 function Box(t){this._text=t;this._enabled=true;this.contents=bitmap(200);this.width=208;}
 Box.prototype.refresh=function(){};
 Box.prototype.standardPadding=function(){return 4;};
 Box.prototype.createContents=function(){this.contents=bitmap(this.width-8);};
 Box.prototype.changePaintOpacity=function(){};
 Box.prototype.drawText=function(...args){this.contents.drawText(...args);};
 function Scene(){}
 function FileCommand(){}
 function QuestHeader(){this.contents=bitmap(164);this.contents.height=44;this.contents.measureTextWidth=function(t){return t.length*this.fontSize/2.6;};}
 function QuestTypes(){this.contents=bitmap(168);this.contents.measureTextWidth=function(t){return t.length*this.fontSize/2.6;};}
 QuestTypes.prototype.lineHeight=()=>28;
 function QuestList(){QuestTypes.call(this);}
 QuestList.prototype.lineHeight=()=>28;
 function MenuCommand(){this.contents=bitmap(590);this.contents.measureTextWidth=function(t){return t.length*this.fontSize/2.6;};}
 MenuCommand.prototype.lineHeight=()=>24;
 Scene.prototype.createTitleCommands=function(){this._titleCommands=commands.map(t=>new Box(t));};
 const env={Bitmap:InkProbe,Scene_OmoriTitleScreen:Scene,Window_OmoTitleScreenBox:Box,Window_OmoriFileCommand:FileCommand,Window_OmoriQuestHeader:QuestHeader,Window_OmoriQuestTypes:QuestTypes,Window_OmoriQuestList:QuestList,Window_MenuCommand:MenuCommand,Graphics:{width:640},LanguageManager:{getPluginText(){return 'LỜI KHUYÊN CỦA MARI';},getMessageData(key){if(key==='XX_BLUE.Chapter_Names')return {P:'PROLOGUE'};return {refresh_contents_fontsize:40,refresh_drawText_position:[0,-13]};}}};
 ui.install(env,{direction});return env;
}
for(const direction of ['ltr','rtl']){
 setup(direction);
 const control=setup(direction);
 const header=new control.Window_OmoriQuestHeader();header.refresh();
 assert(header.contents.calls[0].size<24);assert.equal(header.contents.fontSize,24);
 const menu=new control.Window_MenuCommand();
 // Native final column has a nominal96px field, but only82 drawable pixels.
 menu.drawText('SEÇENEKLER',500,-3,96,'left');
 const caption=menu.contents.calls[0];assert.equal(caption.text,'SEÇENEKLER');
 assert(caption.size<24);assert.equal(menu.contents.fontSize,24);
 assert(caption.x+caption.w+(direction==='rtl'?25:0)<=582);
 menu.drawText('OPTIONS',500,-3,96,'left');assert.equal(menu.contents.calls[1].size,24);
 // Ukrainian still exceeds82px at the18px minimum. Preserve height and let
 // native Bitmap.drawText condense this one caption into the actual field.
 menu.drawText('НАЛАШТУВАННЯ',500,-3,96,'left');
 const longCaption=menu.contents.calls[2];assert.equal(longCaption.size,18);
 assert('НАЛАШТУВАННЯ'.length*18/2.6>82);
 assert.equal(longCaption.text,'НАЛАШТУВАННЯ');assert.equal(menu.contents.fontSize,24);
 assert(longCaption.x+longCaption.w+(direction==='rtl'?25:0)<=582);
 for(const Type of [control.Window_OmoriQuestTypes,control.Window_OmoriQuestList]){
  const q=new Type();q.drawText('CHƯA HOÀN THÀNH',41,0,156,'left');
  const d=q.contents.calls[0];assert(d.size<24);assert.equal(q.contents.fontSize,24);
  if(direction==='ltr')assert(d.x+d.w<=160);
  else assert(d.x+d.w+25<=160);
  q.drawText('BASIL',41,28,156,'left');assert.equal(q.contents.calls[1].size,24);
  assert.throws(()=>q.drawText('X'.repeat(100),41,0,156,'left'),/exceeds its measured bounds/);
  assert.equal(q.contents.fontSize,24);
 }
 if(direction==='rtl') {
  const command=new control.Window_OmoriFileCommand();
  command.contents=bitmap(111);command.itemRectForText=()=>({x:46,y:24,width:59});
  command.resetTextColor=()=>{};command.changePaintOpacity=()=>{};
  command.isCommandEnabled=()=>true;command.commandName=()=> 'LONG RTL COMMAND';
  command.lineHeight=()=>24;command.drawItem(1);
  const draw=command.contents.calls[0];
  const inkRight=draw.x+draw.w+25,inkLeft=inkRight-(draw.w-1)+1;
  assert.equal(inkRight,104);assert(inkLeft>=46);
 } else assert.equal(control.Window_OmoriFileCommand.prototype.drawItem,undefined);
 let win={contents:bitmap()};
 ui.drawFileHeader(win,'ARCHIVE 1:',{chapter:'P'},40,-6,28);
 assert.equal(win.contents.calls.length,2);
 const [prefix,chapter]=win.contents.calls;
 assert.equal(prefix.text,'ARCHIVE 1:');assert.equal(chapter.text,'PROLOGUE');
 assert(prefix.x>=40&&chapter.x>=40);
 if(direction==='ltr')assert(prefix.x+prefix.w<chapter.x);
 else {assert(chapter.x+chapter.w<prefix.x+25);assert.equal(prefix.x+prefix.w+25,win.contents.width-9);}
 win={contents:bitmap()};ui.drawFileHeader(win,'ARCHIVE 6:',null,40,-6,28);
 assert.equal(win.contents.calls.length,1); // Empty slots still retain their heading.
 win={contents:bitmap()};ui.drawFilePair(win,'LONG LOCATION:','RETAINED MAP NAME',80,24);
 const [label,value]=win.contents.calls;
 assert.equal(label.text,'LONG LOCATION:');assert.equal(value.text,'RETAINED MAP NAME');
 if(direction==='ltr')assert(label.x+label.w<value.x);
 else {assert(value.x+value.w<label.x+25);assert.equal(label.x+label.w+25,win.contents.width-9);}
 assert(win.contents.calls.every(c=>c.x>=118&&c.x+c.w+(direction==='rtl'&&c.align==='right'?25:0)<=win.contents.width-7));
 assert.equal(win.contents.fontSize,24); // Local fitting must not leak to subsequent rows.
 win={contents:bitmap()};ui.drawFileLevel(win,'LEVEL:',28,30,24);
 assert.equal(win.contents.calls[1].text,direction==='ltr'?'28':'LEVEL:');
 const before=win.contents.fontSize;
 assert.throws(()=>ui.drawFilePair(win,'X'.repeat(100),'Y'.repeat(100),80,24),/exceeds its measured bounds/);
 assert.equal(win.contents.fontSize,before);
}
let env=setup('ltr'),scene=new env.Scene_OmoriTitleScreen();scene.createTitleCommands();
const boxes=scene._titleCommands;
assert(boxes[0].x>=40);assert(boxes.at(-1).x+boxes.at(-1).width<=630);
for(let i=1;i<boxes.length;i++)assert(boxes[i].x-(boxes[i-1].x+boxes[i-1].width)>=35);
assert(boxes.every(w=>w._localeTitleSize>=28&&w.contents.fontSize===w._localeTitleSize));
env=setup('ltr',['X'.repeat(100),'CONTINUE','OPTIONS']);scene=new env.Scene_OmoriTitleScreen();
assert.throws(()=>scene.createTitleCommands(),/exceed measured bounds/);
// Russian needs only the shared field geometry, with no title-window changes.
ui.configure({}, {direction:'ltr'});
let ru={contents:bitmap()};ui.drawFileLevel(ru,'CYRILLIC LEVEL LABEL',1,30,24);
const [label,number]=ru.contents.calls;
assert.equal(number.x-(label.x+label.w-1),8);assert.equal(number.text,'1');
console.log('PASS: title spacing, save headings, LTR/RTL pairs, narrow RTL commands, configure-only RU label/number gap, fitting isolation and overflow rejection. Native font/Canvas rendering is replaced in this geometry test.');
