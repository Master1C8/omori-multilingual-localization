// Exercise the actual compiled save/load geometry and native Canvas call bounds.
// Window construction, cursor artwork and Canvas pixels are mocked; visual review is separate.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const before=process.argv[2],after=process.argv[3],output=process.argv[4];
const plugin='plugins/Omori Save & Load.js';
const old=fs.readFileSync(before+'/'+plugin,'utf8'),current=fs.readFileSync(after+'/'+plugin,'utf8');
const addition='Window_OmoriFileCommand.prototype.customCursorRectTextWidthOffset = function() { return -this.customCursorRectTextXOffset(); };\r\n';
assert.equal(current.split(addition).length,2);assert.equal(current.replace(addition,''),old);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const ar=JSON.parse(fs.readFileSync(after+'/receipt.json')),br=JSON.parse(fs.readFileSync(before+'/receipt.json'));
assert.deepStrictEqual(Object.keys(ar.compiledOutputs),Object.keys(br.compiledOutputs));assert.deepStrictEqual(Object.keys(ar.compiledOutputs).filter(k=>ar.compiledOutputs[k]!==br.compiledOutputs[k]),[plugin,'plugins/Omori Title Screen.js']);
const original=p=>zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/'+p+'.gz')).toString();
function method(src,name){let found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type==='AssignmentExpression'&&src.slice(n.left.start,n.left.end)===name&&n.right.type==='FunctionExpression')found.push(src.slice(n.start,n.end)+';');for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(src,{ecmaVersion:'latest'}));assert.equal(found.length,1,name);return found[0];}
const core=original('js/rpg_windows.js'),base=original('js/plugins/Omori BASE.OMORI'),bitmap=original('js/rpg_core.js');
const catalog=JSON.parse(fs.readFileSync('source/native-yaml-8879120-01/native-source.json')).find(r=>r.asset==='languages/en/XX_BLUE.HERO');
const yaml=require('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw/js/libs/js-yaml-master');
const loc=yaml.safeLoad(fs.readFileSync('build/ru/combined-2026-10-14-10/resources/languages/en/XX_BLUE.HERO.yaml','utf8')).Omori_Save_Load;
assert.equal(loc.save_command,'СОХРАНИТЬ');assert.equal(loc.load_command,'ЗАГРУЗИТЬ');
function run(src){
 const c=vm.createContext({LanguageManager:{getMessageData(){return loc;}},Rectangle:function(){},records:[]});
 vm.runInContext('function Window_Base(){} function Window_Selectable(){} Window_Selectable.prototype=Object.create(Window_Base.prototype);function Window_Command(){} Window_Command.prototype=Object.create(Window_Selectable.prototype);function Window_OmoriFileCommand(){} Window_OmoriFileCommand.prototype=Object.create(Window_Command.prototype);function Bitmap(){}',c);
 for(const n of ['Window_Base.prototype.drawText','Window_Selectable.prototype.itemRectForText','Window_Selectable.prototype.itemRect','Window_Selectable.prototype.itemWidth','Window_Selectable.prototype.itemHeight','Window_Selectable.prototype.spacing','Window_Command.prototype.drawItem','Window_Command.prototype.itemTextAlign'])vm.runInContext(method(core,n),c);
 vm.runInContext('var _TDS_={OmoriBASE:{Window_Selectable_itemRectForText:Window_Selectable.prototype.itemRectForText}};Window_Selectable.prototype.customCursorRectTextYOffset=function(){return 0;};Window_Selectable.prototype.customCursorRectTextWidthOffset=function(){return 0;};',c);
 vm.runInContext(method(base,'Window_Selectable.prototype.itemRectForText'),c);
 for(const n of ['windowWidth','windowHeight','standardPadding','lineHeight','maxCols','customCursorRectTextXOffset','makeCommandList'])vm.runInContext(method(src,'Window_OmoriFileCommand.prototype.'+n),c);
 if(src===current)vm.runInContext(method(src,'Window_OmoriFileCommand.prototype.customCursorRectTextWidthOffset'),c);
 vm.runInContext(method(bitmap,'Bitmap.prototype.drawText'),c);
 vm.runInContext('Window_Base.prototype.textPadding=function(){return 6;};Window_Selectable.prototype.topIndex=function(){return 0;};Window_Command.prototype.resetTextColor=function(){};Window_Command.prototype.changePaintOpacity=function(enabled){this.contents.opacity=enabled;};Window_Command.prototype.commandName=function(i){return this.commands[i].name;};Window_Command.prototype.isCommandEnabled=function(i){return this.commands[i].enabled;};Window_Command.prototype.addCommand=function(name,symbol,enabled){this.commands.push({name:name,symbol:symbol,enabled:enabled});};',c);
 vm.runInContext('Bitmap.prototype._makeFontNameText=function(){return "28px OMORI_GAME";};Bitmap.prototype._drawTextOutline=function(text,x,y,width){records.push({kind:"outline",text:text,x:x,y:y,width:width,opacity:this.opacity});};Bitmap.prototype._drawTextBody=function(text,x,y,width){records.push({kind:"body",text:text,x:x,y:y,width:width,opacity:this.opacity});};Bitmap.prototype._setDirty=function(){};',c);
 const controls=[];
 for(const flags of [[true,true],[true,false],[false,true],[false,false]]){
  c.flags=flags;vm.runInContext('var win=new Window_OmoriFileCommand();win.width=win.windowWidth();win.height=win.windowHeight();win.padding=win.standardPadding();win._scrollX=0;win._scrollY=0;win.commands=[];win._canSave=flags[0];win._canLoad=flags[1];win.makeCommandList();win.contents=new Bitmap();win.contents.width=win.width-win.padding*2;win.contents.fontSize=28;win.contents._context={globalAlpha:1,save:function(){},restore:function(){}};records.length=0;win.drawItem(0);win.drawItem(1);',c);
  assert.deepStrictEqual(Array.from(c.win.commands,x=>x.symbol),['save','load']);assert.deepStrictEqual(Array.from(c.win.commands,x=>x.enabled),flags);
  assert.equal(c.win.width,119);assert.equal(c.win.height,64);assert.equal(c.win.contents.fontSize,28);
  const calls=Array.from(c.records,r=>({...r}));assert.equal(calls.length,4);
  for(const r of calls){assert.equal(r.x,46);assert.equal(r.opacity,flags[r.text===loc.save_command?0:1]);}
  controls.push({flags,calls,contentsWidth:c.win.contents.width});
 }
 return controls;
}
const broken=run(old),fixed=run(current);
for(const ctrl of broken)for(const r of ctrl.calls)assert.equal(r.x+r.width-ctrl.contentsWidth,34);
for(const ctrl of fixed)for(const r of ctrl.calls){assert.equal(r.width,59);assert.equal(r.x+r.width,ctrl.contentsWidth-6);}
const result={status:'passed',labels:[loc.save_command,loc.load_command],enabledStateControls:4,previousOverflowPixels:34,fixedTextStart:46,fixedMaxWidth:59,rightPadding:6,windowSize:[119,64],fontSize:28,changedCompiledOutputs:[plugin,"plugins/Omori Title Screen.js"],sourceSha256:hash(Buffer.from(current)),boundary:'Actual compiled command geometry/list, native item rect and drawItem/drawText/Bitmap.drawText. Canvas pixels and window construction mocked; branch symbols/enabled states preserved. No save I/O.',controls:fixed};fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');process.stdout.write(JSON.stringify({status:'passed',labels:result.labels,states:4,oldOverflow:34,newRightPadding:6}));
