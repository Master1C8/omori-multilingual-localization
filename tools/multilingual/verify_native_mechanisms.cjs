// Actual original consumer methods with explicit service doubles; no game boot/save I/O.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),vm=require('node:vm'),assert=require('node:assert');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const root=path.resolve(process.argv[2]),ui=JSON.parse(fs.readFileSync(0,'utf8'));
const raw=asset=>zlib.gunzipSync(fs.readFileSync(path.join(root,'source/inventory-8879120-01/original',asset+'.gz'))).toString();
function method(source,name){let found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===name&&n.right.type==='FunctionExpression')found.push(source.slice(n.start,n.end)+';');for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:'latest'}));assert.equal(found.length,1,name);return found[0];}
const bootstrap=require(path.join(root,'runtime/multilingual/native-bootstrap.js'));
const expected='function() {\nreturn 1;\n}',legacy='function () {\r\nreturn 1;\r\n}';
bootstrap.assertFunction({toString(){return legacy;}},expected);
assert.throws(()=>bootstrap.assertFunction({toString(){return legacy.replace('return 1','return 2');}},expected),/Native function input mismatch/);
const config=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(root,'source/text-corpus-8879120-02/original-plugins.js.gz'))).toString().split('var $plugins =')[1].trim().replace(/;$/,''));
const plugin=config.find(p=>p.status&&Object.keys(p.parameters).length);const key=Object.keys(plugin.parameters)[0],before=plugin.parameters[key];
bootstrap.prepareParameters(config,[{plugin:plugin.name.toLowerCase(),key,source:before,target:'SYNTHETIC PARAMETER'}]);
// Simulate native registration after the first bootstrap plugin, using its real setter.
const c=vm.createContext({});vm.runInContext('var PluginManager={_parameters:{}};',c);
vm.runInContext(method(raw('js/rpg_managers.js'),'PluginManager.setParameters'),c);
c.params=plugin.parameters;c.name=plugin.name;vm.runInContext('PluginManager.setParameters(name,params)',c);
assert.equal(c.PluginManager._parameters[plugin.name.toLowerCase()][key],'SYNTHETIC PARAMETER');
assert.throws(()=>bootstrap.prepareParameters(config,[{plugin:plugin.name.toLowerCase(),key,source:before,target:'X'}]),/Native plugin parameter input mismatch/);
const windowSource=raw('js/rpg_windows.js');
let drawCalls=[];const renderer=vm.createContext({drawCalls});vm.runInContext('function Window_Base(){};Window_Base.prototype.textWidth=function(c){return 10;};',renderer);
vm.runInContext(method(windowSource,'Window_Base.prototype.processNormalCharacter'),renderer);
vm.runInContext('var w=new Window_Base();w.contents={drawText:function(c){drawCalls.push(c);}};',renderer);
const segmented=[];
for(const sample of ['AB','سلام','שלום 12','क्षि','กิ','a\u0301','😀']){
 drawCalls.length=0;renderer.sample=sample;vm.runInContext('var state={text:sample,index:0,x:0,y:0,height:32};while(state.index<state.text.length)w.processNormalCharacter(state);',renderer);
 assert.equal(drawCalls.join(''),sample);assert.equal(drawCalls.length,sample.length);
 segmented.push({sample,codeUnitCalls:drawCalls.length,wholeRunDelivered:drawCalls.length===1});
}
function titleRun(source,widths){
 const labels={confirm:'SYNTHETIC CONFIRM',cancel:'SYNTHETIC CANCEL'};
 const native=JSON.parse(fs.readFileSync(path.join(root,'source/native-yaml-8879120-01/native-source.json'))).find(r=>r.asset==='languages/en/XX_BLUE.HERO').native.Scene_OmoriTitleScreen;
 const ctx=vm.createContext({Graphics:{boxWidth:640,boxHeight:480},widths,LanguageManager:{languageData(){return {text:{System:{plugins:{optionsMenu:{buttonHints:labels}}}}};},getMessageData(){return native;}}});
 vm.runInContext('function Scene_OmoriTitleScreen(){};function Bitmap(w,h){this.width=w;this.height=h;this.calls=[];}Bitmap.prototype.clear=function(){this.calls=[];};Bitmap.prototype.resize=function(w,h){this.width=w;this.height=h;};Bitmap.prototype.measureTextWidth=function(t){return widths[t];};Bitmap.prototype.drawInputIcon=function(input,x,y){this.calls.push({kind:"icon",input,x,y,width:24});};Bitmap.prototype.drawText=function(text,x,y){this.calls.push({kind:"text",text,x,y,width:widths[text]});};function Sprite(bitmap){this.bitmap=bitmap;this._frame={width:bitmap.width,height:bitmap.height};this.position={set:function(x,y){this.x=x;this.y=y;}};}Sprite.prototype._refresh=function(){};Scene_OmoriTitleScreen.prototype.addChild=function(){};',ctx);
 vm.runInContext(method(raw('js/rpg_core.js'),'Sprite.prototype.setFrame'),ctx);
 for(const name of ['createCommandHints','refreshCommandHints'])vm.runInContext(method(source,'Scene_OmoriTitleScreen.prototype.'+name),ctx);
 vm.runInContext('var scene=new Scene_OmoriTitleScreen();scene.createCommandHints();',ctx);
 return ctx.scene._commandHints;
}
const titleControls=[];
for(const [confirm,cancel] of [[150,90],[90,70],[187.5,112.5]]){
 const widths={'SYNTHETIC CONFIRM':confirm,'SYNTHETIC CANCEL':cancel},old=titleRun(ui.title.original,widths),fixed=titleRun(ui.title.fixed,widths);
 assert.equal(old.bitmap.width,229);assert.equal(fixed.bitmap.fontSize,28);assert.equal(fixed._frame.width,fixed.bitmap.width);assert.equal(fixed.position.x+fixed.bitmap.width,640);
 for(const call of fixed.bitmap.calls)assert.ok(call.x+call.width<=fixed.bitmap.width-4);
 titleControls.push({confirm,cancel,width:fixed.bitmap.width});
}
const bitmapOnly=titleRun(ui.title.fixed.replace('this._commandHints.setFrame(0, 0, hintWidth, this._commandHints.bitmap.height);',''),{'SYNTHETIC CONFIRM':150,'SYNTHETIC CANCEL':90});
assert.ok(bitmapOnly.bitmap.width>bitmapOnly._frame.width,'Bitmap-only resize must still clip');
// Source-bound width correction; actual item rectangle methods include the native pointer shift.
function saveRun(source,patched,flags){
 const ctx=vm.createContext({Rectangle:function(){},LanguageManager:{getMessageData(){return {save_command:'SYNTHETIC SAVE',load_command:'SYNTHETIC LOAD'};}}});
 vm.runInContext('function Window_Base(){};function Window_Selectable(){};Window_Selectable.prototype=Object.create(Window_Base.prototype);function Window_Command(){};Window_Command.prototype=Object.create(Window_Selectable.prototype);function Window_OmoriFileCommand(){};Window_OmoriFileCommand.prototype=Object.create(Window_Command.prototype);',ctx);
 for(const n of ['Window_Selectable.prototype.itemRectForText','Window_Selectable.prototype.itemRect','Window_Selectable.prototype.itemWidth','Window_Selectable.prototype.itemHeight','Window_Selectable.prototype.spacing'])vm.runInContext(method(windowSource,n),ctx);
 vm.runInContext('var _TDS_={OmoriBASE:{Window_Selectable_itemRectForText:Window_Selectable.prototype.itemRectForText}};Window_Selectable.prototype.customCursorRectTextYOffset=function(){return 0;};Window_Selectable.prototype.customCursorRectTextWidthOffset=function(){return 0;};Window_Base.prototype.textPadding=function(){return 6;};Window_Selectable.prototype.topIndex=function(){return 0;};Window_Command.prototype.addCommand=function(name,symbol,enabled){this.commands.push({name,symbol,enabled});};',ctx);
 vm.runInContext(method(raw('js/plugins/Omori BASE.OMORI'),'Window_Selectable.prototype.itemRectForText'),ctx);
 for(const n of ['windowWidth','windowHeight','standardPadding','lineHeight','maxCols','customCursorRectTextXOffset','makeCommandList'])vm.runInContext(method(source,'Window_OmoriFileCommand.prototype.'+n),ctx);
 if(patched)vm.runInContext(method(source,'Window_OmoriFileCommand.prototype.customCursorRectTextWidthOffset'),ctx);
 ctx.flags=flags;vm.runInContext('var w=new Window_OmoriFileCommand();w.width=w.windowWidth();w.height=w.windowHeight();w.padding=w.standardPadding();w._scrollX=w._scrollY=0;w._canSave=flags[0];w._canLoad=flags[1];w.commands=[];w.makeCommandList();var rect=w.itemRectForText(0);',ctx);
 assert.equal(ctx.w.width,119);assert.equal(ctx.w.height,64);assert.deepStrictEqual(Array.from(ctx.w.commands,x=>x.symbol),['save','load']);assert.deepStrictEqual(Array.from(ctx.w.commands,x=>x.enabled),flags);
 return {x:ctx.rect.x,width:ctx.rect.width,contentsWidth:ctx.w.width-2*ctx.w.padding};
}
for(const flags of [[true,true],[true,false],[false,true],[false,false]]){
 const old=saveRun(ui.save.original,false,flags),fixed=saveRun(ui.save.fixed,true,flags);
 assert.equal(old.x+old.width-old.contentsWidth,34);assert.equal(fixed.x,46);assert.equal(fixed.width,59);assert.equal(fixed.x+fixed.width,fixed.contentsWidth-6);
}
process.stdout.write(JSON.stringify({status:'passed-static',bootstrap:'pre-registration and legacy serialization controls',titleControls,bitmapOnlyNegative:'passed',saveEnabledStates:4,rendererSegmentation:segmented,boundary:'Actual native source methods; font widths, construction and drawing are doubles. No game launch, Canvas pixels, save I/O, native boot or visual acceptance.'}));
