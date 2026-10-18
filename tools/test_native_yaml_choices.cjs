// Native parser + actual choice producer/setup and width/escape functions.
// Bitmap/font drawing is mocked; this is not in-game visual acceptance.
const fs=require('fs'),zlib=require('zlib'),assert=require('assert'),vm=require('vm'),crypto=require('crypto');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const game='/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw';
const yaml=require(game+'/js/libs/js-yaml-master');
const combined=process.argv[2],build=process.argv[3],out=process.argv[4];
const read=p=>JSON.parse(fs.readFileSync(p)),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const raw=asset=>zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/'+asset+'.gz')).toString();
function decrypt(b){return crypto.createDecipheriv('aes-256-ctr',Buffer.from('6bdb2e585882fbd48826ef9cffd4c511'),b.subarray(0,16)).update(b.subarray(16)).toString();}
function differences(a,b,path=[]){
 if(typeof a!==typeof b||a===null||b===null||typeof a!=='object')return a===b?[]:[{path,before:a,after:b}];
 assert.equal(Array.isArray(a),Array.isArray(b));assert.deepStrictEqual(Object.keys(a).sort(),Object.keys(b).sort());
 return Object.keys(a).flatMap(k=>differences(a[k],b[k],path.concat(Array.isArray(a)?Number(k):k)));
}
const units=read('source/native-yaml-8879120-01/units.json'),author=read('translation/ru/native-yaml-supplement.json').entries;
const expected=new Map(author.map(e=>[e.id,e]));assert.equal(expected.size,19);assert.equal(units.length,19);
const prepared=new Map(read(out+'/prepared-source.json').map(r=>[r.asset,r.prepared]));
const manifest=read(build+'/manifest.json'),files=new Map(manifest.files.map(r=>[r.path,r]));
const receipt=read(combined+'/receipt.json'),resources=new Map(receipt.resources.map(r=>[r.originalAsset,r]));
const sources=read('source/native-yaml-8879120-01/native-source.json');let residual=[],delta=[],targets={};
for(const row of sources){
 const original=yaml.safeLoad(raw(row.asset));assert.deepStrictEqual(original,row.native);
 residual.push(...differences(prepared.get(row.asset),original).map(d=>({asset:row.asset,...d})));
 const installed=files.has(row.asset)?fs.readFileSync(build+'/files/'+row.asset):fs.readFileSync(game+'/'+row.asset);
 if(files.has(row.asset))assert.equal(hash(installed),files.get(row.asset).sha256);
 const delivered=yaml.safeLoad(decrypt(installed));targets[row.asset]=delivered;
 if(resources.has(row.asset)){
  const p=resources.get(row.asset),text=fs.readFileSync(combined+'/'+p.output);assert.equal(hash(text),p.rawSha256);assert.deepStrictEqual(delivered,yaml.safeLoad(text.toString()));
  const previous=yaml.safeLoad(fs.readFileSync('build/ru/combined-2026-10-14-09/'+p.output,'utf8'));
  delta.push(...differences(previous,delivered).map(d=>({asset:row.asset,...d})));
 }else assert.deepStrictEqual(delivered,original);
}
assert.equal(sources.length,211);assert.equal(residual.length,1);assert.equal(residual[0].asset,'data/Notes.PLUTO');assert.equal(residual[0].before,'Oooooooh!');assert.equal(residual[0].after,'Oooooooh!\n');
assert.equal(fs.readFileSync(game+'/data/Notes.PLUTO').length>16,true);assert.equal(decrypt(fs.readFileSync(game+'/data/Notes.PLUTO')),raw('data/Notes.PLUTO'));
assert.equal(delta.length,19);
for(const d of delta){const id=d.asset+'#'+JSON.stringify(d.path),e=expected.get(id);assert.ok(e,id);assert.equal(typeof d.before,'boolean');assert.equal(d.before,e.source==='YES');assert.equal(d.after,e.target);assert.equal(d.after,e.source==='YES'?'ДА':'НЕТ');}
for(const u of units){let v=targets[u.asset];for(const k of u.path)v=v[k];assert.equal(v,expected.get(u.id).target);}
function method(source,name){const ast=acorn.parse(source,{ecmaVersion:'latest'});let found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===name&&n.right.type==='FunctionExpression')found.push(source.slice(n.start,n.end)+';');for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(ast);assert.equal(found.length,1,name);return found[0];}
const core=fs.readFileSync(game+'/js/rpg_windows.js','utf8'),objects=fs.readFileSync(game+'/js/rpg_objects.js','utf8');
const lang=raw('js/plugins/Text_Language_Processor.OMORI'),yep=raw('js/plugins/YEP_MessageCore.OMORI'),base=raw('js/plugins/Omori BASE.OMORI');
const c=vm.createContext({TextManager:{currencyUnit:'CLAMS'},LanguageManager:{_language:'en',_data:{}},assert});
vm.runInContext('function Game_Interpreter(){this._branch={};this._indent=0;} function Game_Message(){} function Window_Base(){} function Window_ChoiceList(){} Window_ChoiceList.prototype=Object.create(Window_Base.prototype);',c);
for(const [source,names] of [[lang,['LanguageManager.getTextData','LanguageManager.getMessageData','Game_Interpreter.prototype.addLanguageChoice','Game_Interpreter.prototype.setupLanguageChoices','Game_Message.prototype.setLanguageLabels']], [objects,['Game_Message.prototype.setChoices','Game_Message.prototype.setChoiceBackground','Game_Message.prototype.setChoicePositionType','Game_Message.prototype.setChoiceCallback','Game_Message.prototype.choices']], [core,['Window_Base.prototype.convertEscapeCharacters','Window_Base.prototype.drawTextEx']], [yep,['Window_Base.prototype.textWidthEx']], [base,['Window_ChoiceList.prototype.maxChoiceWidth']]])for(const name of names)vm.runInContext(method(source,name),c);
// Use the native Array clone implementation, not a different algorithm.
const nativeCore=fs.readFileSync(game+'/js/rpg_core.js','utf8');let cloneFn;function findClone(n){if(!n||typeof n!=='object')return;if(n.type==='Property'&&n.key.name==='clone'){const v=n.value.properties.find(p=>p.key.name==='value').value;cloneFn=nativeCore.slice(v.start,v.end);}for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(findClone);else if(v&&typeof v==='object')findClone(v);}}findClone(acorn.parse(nativeCore,{ecmaVersion:'latest'}));assert.ok(cloneFn);vm.runInContext('Array.prototype.clone='+cloneFn+';',c);
vm.runInContext('Window_Base.prototype.calcTextHeight=function(){return 32;};Window_Base.prototype.resetFontSettings=function(){};Window_Base.prototype.processCharacter=function(s){s.index++;s.x+=16;};Window_Base.prototype.lineHeight=function(){return 32;};Window_Base.prototype.textPadding=function(){return 6;};',c);
const event=JSON.parse(raw('data/Map088.KEL')).events[2].pages[0].list;
const choices=event.filter(e=>e.code===356&&e.parameters[0].startsWith('AddChoice XX_GENERAL.message_')).map(e=>e.parameters[0].split(' '));
assert.deepStrictEqual(choices.map(e=>e.slice(1)),[['XX_GENERAL.message_4','Label1'],['XX_GENERAL.message_5','Label2']]);assert.ok(event.some(e=>e.code===356&&e.parameters[0]==='ShowChoices 1'));
function run(data,broken){c.LanguageManager._data={en:{text:{XX_GENERAL:data}}};vm.runInContext('var $gameMessage=new Game_Message();var interpreter=new Game_Interpreter();var win=new Window_ChoiceList();win.contents={height:160};interpreter.commandLanguageJumpTo=function(label){this.selectedLabel=label;};',c);for(const e of choices)vm.runInContext('interpreter.addLanguageChoice('+JSON.stringify(e[1])+','+JSON.stringify(e[2])+');',c);vm.runInContext('interpreter.setupLanguageChoices(1);',c);assert.equal(c.$gameMessage._choiceCancelType,1);assert.deepStrictEqual(Array.from(c.$gameMessage._choiceLabels),['Label1','Label2']);if(broken){assert.throws(()=>vm.runInContext('win.maxChoiceWidth()',c),/text.replace is not a function/);return;}assert.ok(vm.runInContext('win.maxChoiceWidth()',c)>0);for(let n=0;n<2;n++){vm.runInContext('$gameMessage._choiceCallback('+n+')',c);assert.equal(c.interpreter.selectedLabel,'Label'+(n+1));}}
run(yaml.safeLoad(raw('languages/en/XX_GENERAL.HERO')),false);
run(yaml.safeLoad(fs.readFileSync('build/ru/combined-2026-10-14-09/resources/languages/en/XX_GENERAL.HERO.yaml','utf8')),true);
run(targets['languages/en/XX_GENERAL.HERO'],false);
const result={status:'passed',nativeYamlAssets:211,changedCaptions:19,changedCatalogs:5,sourceParserResidual:residual,delta,brokenPreviousControl:'exact text.replace TypeError reproduced',positiveControls:['original English choice width','new Russian choice width','both branch labels and cancel index preserved'],boundary:'Bundled js-yaml; actual choice producer/setup, native width and base escape conversion. Bitmap/font drawing mocked; no runtime scene or save acceptance.',buildManifestSha256:hash(fs.readFileSync(build+'/manifest.json')),recipeSha256:hash(fs.readFileSync(__filename))};fs.writeFileSync(out+'/native-yaml-regression.json',JSON.stringify(result,null,2)+'\n');process.stdout.write(JSON.stringify({status:result.status,assets:211,captions:19,catalogs:5,oldErrorReproduced:true}));
