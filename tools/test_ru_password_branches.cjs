// Actual native commands/page selection, current compiled bindings and catalog.
// Variables/party/database/message services mocked; no game or save I/O.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const {create}=require('../runtime/ru-engine-display.js');
const combined=process.argv[2],compiled=process.argv[3];
const receipt=JSON.parse(fs.readFileSync(compiled+'/receipt.json'));
const mapping=JSON.parse(fs.readFileSync(combined+'/display-mappings.json')).entries;
const raw=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/rpg_objects.js.gz')).toString();
const methods={};function walk(n){if(!n||!n.type)return;if(n.type==='AssignmentExpression')methods[raw.slice(n.left.start,n.left.end)]=raw.slice(n.right.start,n.right.end);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}
walk(acorn.parse(raw,{ecmaVersion:'latest'}));
const {execFileSync}=require('child_process');
const catalog=JSON.parse(execFileSync('python3',['-c',"import yaml,json,sys;print(json.dumps(yaml.safe_load(open(sys.argv[1]))))",combined+'/resources/languages/en/XX_MELON.HERO.yaml']));
const forms=JSON.parse(fs.readFileSync('runtime/ru-password-forms.json'));
const nativeMaps={},deliveredMaps={};for(const id of ['006','169']) {
 nativeMaps[id]=JSON.parse(zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/data/Map'+id+'.KEL.gz')));
 deliveredMaps[id]=JSON.parse(fs.readFileSync(combined+'/resources/data/Map'+id+'.KEL.json'));
}
const plans=[['006',42,0],['169',6,0],['169',6,2]];let cases=0,combinations=0;
for(const [map,event,page] of plans) {
 class Variables{constructor(){this._data=[];this.writes=[];}value(id){return this._data[id]||0;}setValue(id,value){this.writes.push([id,value]);this._data[id]=value;}}
 class Interpreter{currentCommand(){return this._list[this._index];}nextEventCode(){return this._list[this._index+1]?.code||0;}skipBranch(){this.skipped=true;}}
 const actor27={};let actorPresent=false;
 const env={Game_Variables:Variables,Game_Interpreter:Interpreter,$gameVariables:new Variables(),
  $gameSwitches:{value:()=>false},$gameSelfSwitches:{value:()=>false},$gameParty:{members:()=>({contains:a=>a===actor27&&actorPresent})},$gameActors:{actor:()=>actor27},
  DataManager:{loadMapData(){},onLoad(){},makeSavefileInfo(){return {};}},
  LanguageManager:{getMessageData:key=>catalog[key.split('.')[1]]}};
 const context=vm.createContext(env);vm.runInContext('Array.prototype.contains=Array.prototype.includes;',context);
 for(const code of [111,122,355])Interpreter.prototype['command'+code]=vm.runInContext('('+methods['Game_Interpreter.prototype.command'+code]+')',context);
 Interpreter.prototype.operateVariable=vm.runInContext('('+methods['Game_Interpreter.prototype.operateVariable']+')',context);
 const meets=vm.runInContext('('+methods['Game_Event.prototype.meetsConditions']+')',context);
 if(map==='169') {const select=()=>{for(let i=2;i>=0;i--)if(meets.call({},nativeMaps[map].events[event].pages[i]))return i;};assert.equal(select(),0);actorPresent=true;assert.equal(select(),2);actorPresent=false;}
 const api=create(mapping,receipt.variableBindings,env,forms,catalog.message_49.text);api.install();
 api.bindAsset('data/Map'+map+'.KEL',deliveredMaps[map]);
 const bindings=receipt.variableBindings.filter(b=>b.asset==='data/Map'+map+'.KEL'&&b.commandPath[1]===event&&b.commandPath[3]===page&&b.labels);
 const interpreter=new Interpreter();interpreter._list=deliveredMaps[map].events[event].pages[page].list;
 const run=b=>{interpreter._index=b.commandPath.at(-1);interpreter._params=interpreter._list[interpreter._index].parameters;assert.equal(interpreter['command'+b.code](),true);};
 for(const b of bindings.filter(b=>b.labels.some(l=>l.variableId>=105)))run(b);
 assert.deepEqual([105,106,107,108].map(id=>env.$gameVariables.value(id)),['SWEET','JELLY','FILLED','DONUT']);
 const choose=(id,word)=>{const b=bindings.find(b=>b.labels.some(l=>l.variableId===id&&mapping.find(r=>r.id===l.unitId).source===word));assert.ok(b);run(b);};
 for(const a of Object.keys(forms.adjectives))for(const b of Object.keys(forms.objects))for(const c of Object.keys(forms.relations))for(const d of Object.keys(forms.heads)) {
  const words=[a,b,c,d];words.forEach((w,i)=>choose(101+i,w));
  assert.deepEqual([101,102,103,104].map(id=>env.$gameVariables.value(id)),words);
  assert.equal(env.LanguageManager.getMessageData('XX_MELON.message_49').text,catalog.message_49.text.replace('\\v[101] \\v[102] \\v[103] \\v[104]',api.passwordPhrase(words)));
  const correct=[101,102,103,104].every((id,i)=>env.$gameVariables.value(id)===env.$gameVariables.value(105+i));
  assert.equal(correct,words.join(' ')==='SWEET JELLY FILLED DONUT');combinations++;
  for(let i=0;i<4;i++) {interpreter._params=[1,101+i,1,105+i,0];interpreter._branch={};interpreter._indent=0;interpreter.command111();assert.equal(interpreter._branch[0],words[i]===['SWEET','JELLY','FILLED','DONUT'][i]);}
 }
 ['SWEET','JELLY','FILLED','DONUT'].forEach((w,i)=>choose(101+i,w));
 assert.ok(env.LanguageManager.getMessageData('XX_MELON.message_49').text.includes('СЛАДКИЙ ПОНЧИК, НАЧИНЁННЫЙ ДЖЕМОМ'));
 const restored=JSON.parse(JSON.stringify(env.$gameVariables));Object.setPrototypeOf(restored,Variables.prototype);env.$gameVariables=restored;
 assert.ok(api.passwordText(catalog.message_49.text).includes('СЛАДКИЙ ПОНЧИК, НАЧИНЁННЫЙ ДЖЕМОМ'));
 env.$gameVariables.setValue(101,'SWEET');assert.equal(api.passwordText(catalog.message_49.text),catalog.message_49.text);
 choose(101,'SWEET');env.$gameVariables.setValue(102,'CUSTOM');assert.equal(api.passwordText(catalog.message_49.text),catalog.message_49.text);
 if(page===0) {
  assert.ok(restored.writes.every(([,value])=>typeof value!=='string'||/^[A-Z]+$/.test(value)),'Native setter must receive original tokens');
  const first=bindings.find(b=>b.labels.length===4),broken=JSON.parse(JSON.stringify(deliveredMaps[map]));
  broken.events[event].pages[page].list[first.commandPath.at(-1)+1].parameters[0]+=' // altered';
  api.bindAsset('data/Map'+map+'.KEL',broken);interpreter._list=broken.events[event].pages[page].list;run(first);
  assert.equal(env.$gameVariables.value(105),catalog.message_43.text,'Wrong sibling source must not gain a binding');
  interpreter._list=deliveredMaps[map].events[event].pages[page].list;
  const sibling=interpreter._list[first.commandPath.at(-1)+1],original=sibling.parameters[0];
  sibling.parameters[0]+=' // changed in place after binding';run(first);
  assert.equal(env.$gameVariables.value(105),catalog.message_43.text,'An in-place command change must invalidate active provenance');
  sibling.parameters[0]=original;run(first);assert.equal(env.$gameVariables.value(105),'SWEET');
 }
 cases+=8;
}
assert.equal(combinations,1875);
process.stdout.write(JSON.stringify({status:'passed',branches:3,combinations,cases,sourceCatalogCommands:42,sourceCatalogAssignments:48,
 boundary:'Actual original command122/355 and Map169 page selection; delivered source command arrays, current catalog and typed runtime. Variables, party/message/database services and save I/O mocked. JSON continuation only; no game/loader/Canvas.'}));
