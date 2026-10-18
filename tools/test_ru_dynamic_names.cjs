// Actual original interpreter command functions and prepared name-binding table.
// Native variables/database/troop/file services are mocked; no game boot or saves.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const {create}=require('../runtime/ru-engine-display.js');
const combined=process.argv[2],display=process.argv[3];
const mappings=JSON.parse(fs.readFileSync(combined+'/display-mappings.json')).entries;
const receipt=JSON.parse(fs.readFileSync(display+'/receipt.json'));
const source=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/rpg_objects.js.gz')).toString('utf8');
function method(owner) {
 let result;function walk(n){if(!n||!n.type)return;if(n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===owner)result=source.slice(n.right.start,n.right.end);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:'latest'}));assert.ok(result);return result;
}
const env={};
for(const kind of ['Actors','Enemies','Items','Skills','Weapons','Armors','Classes','States'])env['$data'+kind]=JSON.parse(fs.readFileSync(combined+'/resources/data/'+kind+'.KEL.json'));
class Variables {constructor(){this._data={};}setValue(id,v){this._data[id]=v;return 'native';}value(id){return this._data[id]||0;}}
class Interpreter {currentCommand(){return this._list[this._index];}nextEventCode(){return this._list[this._index+1]?this._list[this._index+1].code:0;}operateVariable(id,op,value){assert.equal(op,0);env.$gameVariables.setValue(id,value);}}
env.Game_Variables=Variables;env.Game_Interpreter=Interpreter;env.$gameVariables=new Variables();
env.DataManager={loadMapData(){},onLoad(){},makeSavefileInfo(){return {};}};
env.$gameTroop={members:()=>env.members};
const context=vm.createContext(env);
Interpreter.prototype.command122=vm.runInContext('('+method('Game_Interpreter.prototype.command122')+')',context);
Interpreter.prototype.command355=vm.runInContext('('+method('Game_Interpreter.prototype.command355')+')',context);
const api=create(mappings,receipt.variableBindings,env);api.install();let cases=0;
function at(data,path){for(const key of path)data=data[key];return data;}
for(const binding of receipt.variableBindings.filter(b=>b.dynamicName)) {
 const data=JSON.parse(zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/'+binding.asset+'.gz')));
 api.bindAsset(binding.asset,data);const path=binding.commandPath,list=at(data,path.slice(0,-1)),index=path[path.length-1];
 const interpreter=new Interpreter();interpreter._list=list;interpreter._index=index;interpreter._params=list[index].parameters;
 const descriptor=binding.dynamicName;let raw,target;
 if(descriptor.kind==='database') {
  const record=env['$data'+descriptor.database][descriptor.recordId];raw=record.name;target=api.recordName(record);
 } else if(descriptor.kind==='gacha-item') {
  interpreter._gachaItem=env.$dataItems.find(r=>r&&r.name==='LIFE JAM');assert.ok(interpreter._gachaItem);
  raw=interpreter._gachaItem.name.toUpperCase();target=api.recordName(interpreter._gachaItem).toUpperCase();
 } else {
  const row=mappings.find(r=>r.asset==='data/Enemies.KEL'&&r.source==='HAROLD');assert.ok(row);
  const enemy={name:()=>row.source+' A',originalName:()=>row.source,isActor:()=>false,isEnemy:()=>true,enemyId:()=>row.path[0],_plural:true,_letter:' A'};
  env.members=[enemy,enemy];raw=enemy.name();target=api.name(enemy);
 }
 assert.equal(interpreter['command'+binding.code](),true);
 assert.equal(env.$gameVariables.value(descriptor.variableId),raw);
 assert.equal(api.variable(descriptor.variableId),target);
 env.$gameVariables=Object.assign(new Variables(),JSON.parse(JSON.stringify(env.$gameVariables)));
 assert.equal(env.$gameVariables.value(descriptor.variableId),raw);
 assert.equal(api.variable(descriptor.variableId),target);
 env.$gameVariables.setValue(descriptor.variableId,raw);assert.equal(api.variable(descriptor.variableId),raw);cases+=6;
}
const item=env.$dataItems.find(r=>r&&r.name==='LIFE JAM');assert.equal(api.setRecordVariable(829,item),'native');
assert.equal(env.$gameVariables.value(829),'LIFE JAM');assert.equal(api.variable(829),api.recordName(item));
const clone=Object.assign({},item);api.setRecordVariable(829,clone);assert.equal(api.variable(829),'LIFE JAM');cases+=4;
process.stdout.write(JSON.stringify({status:'passed',cases,dynamicCommands:receipt.variableBindings.filter(b=>b.dynamicName).length,
 boundary:'Actual original command122/355 functions plus exact original command lists and real display adapter. All dynamic metadata survives JSON restore before an unowned same-value write invalidates it. Database/troop/variable services and save serialization mocked; no game boot, renderer, installed-game or save access.'}));
