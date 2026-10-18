// Trace all original enabled normal-character overrides; Canvas/letter sprites doubled.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),vm=require('node:vm'),assert=require('node:assert'),crypto=require('node:crypto');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const root=path.resolve(process.argv[2]),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const pins={};function raw(asset){const f=path.join(root,'source/inventory-8879120-01/original',asset+'.gz'),b=fs.readFileSync(f);pins['source/inventory-8879120-01/original/'+asset+'.gz']=hash(b);return zlib.gunzipSync(b).toString();}
function method(source,name){let found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===name&&n.right.type==='FunctionExpression')found.push(source.slice(n.start,n.end)+';');for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:'latest'}));assert.equal(found.length,1,name);return found[0];}
const configRaw=zlib.gunzipSync(fs.readFileSync(path.join(root,'source/text-corpus-8879120-02/original-plugins.js.gz'))).toString();
const config=JSON.parse(configRaw.slice(configRaw.indexOf('[')).trim().replace(/;$/,''));
const names=['YEP_MessageCore','TDS Text Effects','GTP_OmoriFixes'];const order=names.map(name=>{const i=config.findIndex(p=>p.name===name);assert.ok(i>=0&&config[i].status);return i;});assert.ok(order[0]<order[1]&&order[1]<order[2]);
const base=raw('js/rpg_windows.js'),yep=raw('js/plugins/YEP_MessageCore.OMORI'),tds=raw('js/plugins/TDS Text Effects.OMORI'),gtp=raw('js/plugins/GTP_OmoriFixes.OMORI');
const c=vm.createContext({});vm.runInContext('function Window_Base(){};Window_Base.prototype.textWidth=function(){return 10;};Window_Base.prototype.checkWordWrap=function(){return false;};var Yanfly={Message:{}};var _TDS_={TextEffects:{}};',c);
vm.runInContext(method(base,'Window_Base.prototype.processNormalCharacter'),c);
vm.runInContext('Yanfly.Message.Window_Base_processNormalCharacter=Window_Base.prototype.processNormalCharacter;',c);
vm.runInContext(method(yep,'Window_Base.prototype.processNormalCharacter'),c);
vm.runInContext('_TDS_.TextEffects.Window_Base_processNormalCharacter=Window_Base.prototype.processNormalCharacter;',c);
vm.runInContext(method(tds,'Window_Base.prototype.processNormalCharacter'),c);
const spriteSource=method(tds,'Window_Base.prototype.createLetterEffectSprite');assert.ok(spriteSource.includes('textState.text[textState.index]'));
const controls=[];
for(const easternWrap of [false,true]){
 if(easternWrap)vm.runInContext(method(gtp,'_TDS_.TextEffects.Window_Base_processNormalCharacter'),c);
 for(const effects of [false,true])for(const text of ['AB','سلام','שלום 12','क्षि','กิ','a\u0301','😀']){
  c.effects=effects;c.text=text;c.drawCalls=[];c.sprites=[];
  vm.runInContext('var w=new Window_Base();w._letterEffectsActive=effects;w.canCreateLetterEffectSprite=function(){return effects;};w.createLetterEffectSprite=function(s){sprites.push(s.text[s.index]);};w.contents={drawText:function(c){drawCalls.push(c);},blockTextDrawing:function(){}};var state={text:text,index:0,x:0,y:0,height:32};while(state.index<state.text.length)w.processNormalCharacter(state);',c);
  assert.equal(c.drawCalls.join(''),text);assert.equal(c.drawCalls.length,text.length);
  if(effects){assert.equal(c.sprites.join(''),text);assert.equal(c.sprites.length,text.length);}
  controls.push({easternWrap,effects,text,codeUnitDrawCalls:c.drawCalls.length,letterSpriteCalls:c.sprites.length});
 }
}
process.stdout.write(JSON.stringify({schemaVersion:1,status:'passed-static-trace',pluginOrder:names.map((name,i)=>({name,index:order[i]})),sourcePins:pins,controls,baselineMechanism:'Every enabled normal-character path reaches one-code-unit drawing; letter effects also select one code unit. No run shaping, grapheme grouping or bidi ordering exists at this boundary.',blockedLocales:['ar','fa','he','hi','th'],runtime:'not-run',visual:'not-run',recipeSha256:hash(fs.readFileSync(__filename)),limitations:'Actual original methods and enabled config/order. Wrap decision, font advance/Canvas drawing and letter-sprite construction are doubles; no glyph pixels or native scene acceptance.'}));
