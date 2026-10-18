// Isolated typed adapter tests; engine services are mocked. No game boot.
const assert=require('assert'),fs=require('fs');
const {create}=require('../runtime/ru-engine-display.js');
const combined=process.argv[2],compiled=process.argv[3];
const mappings=JSON.parse(fs.readFileSync(combined+'/display-mappings.json')).entries;
const receipt=JSON.parse(fs.readFileSync(compiled+'/receipt.json'));
const forms=JSON.parse(fs.readFileSync('runtime/ru-password-forms.json'));
const template='\\n<ВПЕЧАТЛЯЮЩАЯ СТАТУЯ>Твой ответ: \\"\\v[101] \\v[102] \\v[103] \\v[104]\\"\\c[0].';
const env={};
for(const kind of ['Actors','Enemies','Items','Skills','Weapons','Armors','Classes','States']) {
 env['$data'+kind]=JSON.parse(fs.readFileSync(combined+'/resources/data/'+kind+'.KEL.json'));
}
class Variables {constructor(){this._data={};}value(i){return this._data[i]||0;}setValue(i,v){this._data[i]=v;return 'native-set';}}
class Interpreter {constructor(command){this.command=command;}currentCommand(){return this.command;}}
Interpreter.prototype.command122=function(){const p=this.command.parameters;const raw=JSON.parse(p[4]);env.$gameVariables.setValue(p[0],raw);return 'native-result';};
Interpreter.prototype.command355=function(){const code=this.command.parameters[0];const match=code.match(/setValue\((\d+),\s*("[^\"]*")/);env.$gameVariables.setValue(+match[1],JSON.parse(match[2]));return 'script-result';};
env.Game_Variables=Variables;env.Game_Interpreter=Interpreter;env.$gameVariables=new Variables();
env.DataManager={loadMapData(){return 9;},onLoad(){return 8;},makeSavefileInfo(){return {actorData:{name:'OMORI'},location:'WHITE SPACE'};}};
const actor=(id,raw)=>({isActor:()=>true,actorId:()=>id,name:()=>raw});
env.$gameParty={leader:()=>actor(1,'OMORI'),battleMembers:()=>[actor(1,'OMORI')],name:()=> 'OMORI'};
env.$gameMap={mapId:()=>1,displayName:()=> 'WHITE SPACE'};
const entry=JSON.parse(fs.readFileSync('translation/ru/batches/ru-0002-neighbors-cutscenes.json')).entries.find(e=>e.id==='languages/en/01_cutscenes_neighbors.HERO#["message_15","text"]');
const sourceMessage={text:entry.target,nativeField:7};let nativeActorName='KEL';
env.$gameActors={actor:()=>({name:()=>nativeActorName})};
env.LanguageManager={getTextData:()=>sourceMessage};
const contextualForms=[{file:'01_cutscenes_neighbors',key:'message_15',target:entry.target,
 actorId:3,nativeName:'KEL',placeholder:'\\n[3]',form:entry.placeholderForms['\\n[3]'].targetForm}];
const api=create(mappings,receipt.variableBindings,env,forms,template,contextualForms);api.install();
let cases=0;
for(const row of mappings.filter(r=>r.path)) {
 assert.equal(api.lookup(row.asset,row.path,row.source),row.target);
 assert.equal(api.lookup(row.asset,row.path,row.source+' custom'),row.source+' custom');cases+=2;
}
assert.equal(api.name(actor(1,'OMORI')),'ОМОРИ');
assert.equal(api.name(actor(8,'CustomName')),'CustomName');
assert.equal(api.name(actor(8,'МоёИмя')),'МоёИмя');
assert.equal(api.name(actor(8,'OMORI')),'OMORI');cases+=4;
for(const row of mappings.filter(r=>r.asset==='data/Enemies.KEL')) {
 const id=row.path[0];const e={isActor:()=>false,isEnemy:()=>true,enemyId:()=>id,originalName:()=>row.source,name:()=>row.source+' A',_plural:true,_letter:' A'};
 assert.equal(api.name(e),row.target+' A');assert.equal(e.name(),row.source+' A');cases+=2;
}
for(const kind of ['Items','Skills','Weapons','Armors','Classes','States']) {
 for(const row of mappings.filter(r=>r.asset==='data/'+kind+'.KEL')) {
  const record=env['$data'+kind][row.path[0]],before=JSON.stringify(record);
  assert.equal(api.recordName(record),row.target);assert.equal(JSON.stringify(record),before);
  assert.equal(api.recordName(Object.assign({},record)),record.name);cases+=3;
 }
}
for(const binding of receipt.variableBindings.filter(b=>b.labels && !b.passwordCatalog)) {
 const data={};let cursor=data;
 for(const key of binding.commandPath.slice(0,-1)){cursor[key]={};cursor=cursor[key];}
 const command={code:binding.code,parameters:JSON.parse(binding.parameters)};
 cursor[binding.commandPath[binding.commandPath.length-1]]=command;
 api.bindAsset(binding.asset,data);const interpreter=new Interpreter(command),label=binding.labels[0],row=mappings.find(r=>r.id===label.unitId);
 assert.equal(interpreter['command'+binding.code](),binding.code===122?'native-result':'script-result');
 assert.equal(env.$gameVariables.value(label.variableId),row.source);
 assert.equal(api.variable(label.variableId),row.target);
 // Same bytes, unowned write: clear display provenance rather than translating.
 assert.equal(env.$gameVariables.setValue(label.variableId,row.source),'native-set');
 assert.equal(api.variable(label.variableId),row.source);
 interpreter['command'+binding.code]();const restored=JSON.parse(JSON.stringify(env.$gameVariables));
 Object.setPrototypeOf(restored,Variables.prototype);env.$gameVariables=restored;
 assert.equal(api.variable(label.variableId),row.target);cases+=6;
}
for(const row of mappings.filter(r=>r.asset==='js/plugins/GTP_OmoriFixes.OMORI')) {
 const error=new Error(row.source);assert.equal(api.error(row.id,error),error);
 assert.equal(error.message,row.source);assert.equal(api.errorMessage(error),row.target);
 assert.equal(api.errorMessage(new Error(row.source)),row.source);cases+=4;
}
const info=env.DataManager.makeSavefileInfo();assert.equal(info.actorData.name,'OMORI');assert.equal(api.savedActor(info),'ОМОРИ');
assert.equal(api.savedActor({actorData:{name:'CustomName'}}),'CustomName');cases+=3;
let combinations=0;
for(const a of Object.keys(forms.adjectives))for(const b of Object.keys(forms.objects))
 for(const c of Object.keys(forms.relations))for(const d of Object.keys(forms.heads)) {
  const words=[a,b,c,d],before=JSON.stringify(words),phrase=api.passwordPhrase(words);
  assert.equal(JSON.stringify(words),before);assert.equal(typeof phrase,'string');
  assert.ok(phrase.includes(forms.heads[d].text));
  assert.ok(phrase.includes(forms.relations[c][forms.heads[d].gender]));combinations++;
 }
assert.equal(combinations,625);
assert.equal(api.passwordPhrase(['SWEET','JELLY','FILLED','DONUT']),'СЛАДКИЙ ПОНЧИК, НАЧИНЁННЫЙ ДЖЕМОМ');
assert.equal(api.passwordPhrase(['MAGICAL','PLANET','SIZED','STATUE']),'ВОЛШЕБНАЯ СТАТУЯ РАЗМЕРОМ С ПЛАНЕТУ');
for(const [i,value] of ['SWEET','JELLY','FILLED','DONUT'].entries()) {
 const binding=receipt.variableBindings.find(b=>b.asset==='data/Map169.KEL' && b.labels[0].variableId===101+i && mappings.find(r=>r.id===b.labels[0].unitId).source===value);
 const data={};let cursor=data;for(const key of binding.commandPath.slice(0,-1)){cursor[key]={};cursor=cursor[key];}
 const command={code:122,parameters:JSON.parse(binding.parameters)};cursor[binding.commandPath.slice(-1)[0]]=command;api.bindAsset(binding.asset,data);new Interpreter(command).command122();
}
assert.equal(api.passwordText(template),template.replace('\\v[101] \\v[102] \\v[103] \\v[104]','СЛАДКИЙ ПОНЧИК, НАЧИНЁННЫЙ ДЖЕМОМ'));
// Preserve correct/incorrect password comparisons in the native keyword space.
assert.deepEqual([101,102,103,104].map(i=>env.$gameVariables.value(i)),['SWEET','JELLY','FILLED','DONUT']);
env.$gameVariables.setValue(101,'SWEET');assert.equal(api.passwordText(template),template);
cases+=combinations+6;
const view=env.LanguageManager.getTextData('01_cutscenes_neighbors','message_15');
assert.equal(view.text,'Из КАРМАНА КЕЛА на тебя смотрит крошечный камень-питомец.');
assert.equal(view.nativeField,7);assert.equal(sourceMessage.text,entry.target);
assert.equal(env.LanguageManager.getTextData('other-file','message_15'),sourceMessage);
nativeActorName='CustomName';assert.equal(env.LanguageManager.getTextData('01_cutscenes_neighbors','message_15'),sourceMessage);
cases+=5;
process.stdout.write(JSON.stringify({status:'passed',cases,boundary:'Real typed adapter, source mapping table and all 54 command bindings; mock engine services replace file loading, game interpreter and save I/O. JSON continuation checked. No game boot or rendering.'}));
