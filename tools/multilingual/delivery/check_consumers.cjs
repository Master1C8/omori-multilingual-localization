/* Isolated consumer tests on decrypted delivered records. This is not the game runtime. */
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const data=JSON.parse(fs.readFileSync(0,'utf8'));
const {create}=require('./engine_display.js');
const values={}, env={$gameVariables:{value:id=>values[id],setValue:(id,value)=>values[id]=value}};
const records=data.resources;
for(const kind of ['Actors','Enemies','Items','Skills','Weapons','Armors','Classes','States'])env['$data'+kind]=records['data/'+kind+'.KEL'];
const api=create(data.mapping,data.proof.variables,env,[]);
for(const [asset,tree] of Object.entries(records))api.bindAsset(asset,tree);
let counts={recordName:0,mapName:0,variable:0,errorMessage:0,'emotion-display-operand':0};
const byid=Object.fromEntries(data.mapping.map(row=>[row.id,row]));
function at(tree,path){return path.reduce((v,k)=>v[k],tree);}
for(const binding of data.proof.bindings){
 const row=byid[binding.id];assert(row,'Unknown binding');
 let actual;
 if(binding.kind==='recordName'){
  const record=records[row.asset][row.path[0]];
  assert.strictEqual(record.name,row.source,'Delivered logical database name changed');
  actual=api.recordName(record);
  // Native battler identities stay raw; the display view is separately mapped.
  if(row.asset==='data/Actors.KEL')assert.strictEqual(api.name({name:()=>row.source,isActor:()=>true,actorId:()=>row.path[0]}),row.target);
  if(row.asset==='data/Enemies.KEL')assert.strictEqual(api.name({name:()=>row.source+' A',originalName:()=>row.source,isEnemy:()=>true,enemyId:()=>row.path[0],_plural:true,_letter:' A'}),row.target+' A');
 }else if(binding.kind==='mapName'){
  assert.strictEqual(records[row.asset].displayName,row.source);
  const id=Number(/Map(\d+)/.exec(row.asset)[1]);actual=api.mapName({displayName:()=>row.source,mapId:()=>id});
  assert.strictEqual(api.mapName({displayName:()=>row.source,mapId:()=>id,_overrideDisplayName:true}),row.source);
 }else if(binding.kind==='variable'){
  const nativeBinding=data.proof.variables.find(b=>b.labels&&b.labels.some(l=>l.unitId===row.id));
  const command=at(records[nativeBinding.asset],nativeBinding.commandPath);
  const label=nativeBinding.labels.find(l=>l.unitId===row.id);
  values[label.variableId]=row.source;api.commitCommand(command,{_list:at(records[nativeBinding.asset],nativeBinding.commandPath.slice(0,-1)),_index:nativeBinding.commandPath.at(-1)});
  assert.strictEqual(values[label.variableId],row.source,'Native variable changed');actual=api.variable(label.variableId);
  values[label.variableId]=row.source+' custom';assert.strictEqual(api.variable(label.variableId),values[label.variableId]);
 }else if(binding.kind==='errorMessage'){
  const error=api.error(row.id,new Error(row.source));assert.strictEqual(error.message,row.source);actual=api.errorMessage(error);
 }else if(binding.kind==='emotion-display-operand')actual=api.label(row.id,row.source);
 else throw new Error('Unwired consumer kind');
 assert.strictEqual(actual,row.target,'Unwired mapped target '+row.id);counts[binding.kind]++;
}
assert.strictEqual(Object.keys(byid).length,data.proof.bindings.length);
process.stdout.write(JSON.stringify({status:'passed-isolated-consumers',counts,boundary:'Actual decrypted delivered records plus isolated JS display functions. Native loader, boot order, rendering, gameplay and UI are not exercised.'}));
