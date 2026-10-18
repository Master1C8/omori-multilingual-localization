// Extract source-only guard data from native05 technical evidence; never copy targets.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),assert=require('node:assert'),vm=require('node:vm'),crypto=require('node:crypto');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const root=path.resolve(process.argv[2]),build=path.resolve(process.argv[3]);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const receiptRaw=fs.readFileSync(path.join(build,'receipt.json')),receipt=JSON.parse(receiptRaw),asset='plugins/OmoriRu_Bootstrap.js';
const raw=fs.readFileSync(path.join(build,asset));assert.equal(hash(raw),receipt.compiledOutputs[asset]);const source=raw.toString();
const ast=acorn.parse(source,{ecmaVersion:'latest'}),core=[],parameters=[];
function walk(n){
 if(!n||typeof n!=='object')return;
 if(n.type==='IfStatement'&&n.test.type==='BinaryExpression'&&n.test.operator==='!=='){
  const t=n.test;
  if(t.left.type==='CallExpression'&&t.left.callee.name==='nativeFunctionSource'&&t.right.type==='CallExpression'&&t.right.callee.name==='nativeFunctionSource'){
   const argument=t.left.arguments[0],expected=t.right.arguments[0];
   assert.equal(expected.type,'Literal');assert.equal(argument.type,'CallExpression');
   core.push({owner:source.slice(argument.callee.object.start,argument.callee.object.end),source:expected.value});
  }
 }
 if(n.type==='VariableDeclarator'&&n.id.name==='edits'&&n.init.type==='ArrayExpression'){
  for(const row of n.init.elements){const props=Object.fromEntries(row.properties.map(p=>[p.key.name||p.key.value,p.value]));
   assert.ok(['plugin','key','source'].every(k=>props[k].type==='Literal'));
   parameters.push({plugin:props.plugin.value,key:props.key.value,source:props.source.value});
  }
 }
 for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}
}
walk(ast);assert.equal(core.length,46);assert.equal(parameters.length,157);
const bootstrap=require(path.join(root,'runtime/multilingual/native-bootstrap.js'));
for(const row of core){
 const fn=vm.runInNewContext('('+row.source+')');bootstrap.assertFunction(fn,row.source);
 const legacy=row.source.replace(/\r\n?/g,'\n').replace(/^function\(/,'function (').replace(/\n/g,'\r\n');
 bootstrap.assertFunction({toString(){return legacy;}},row.source);
 assert.throws(()=>bootstrap.assertFunction({toString(){return legacy.replace(/\}\s*$/,'return 42;}');}},row.source),/Native function input mismatch/);
}
const configRaw=zlib.gunzipSync(fs.readFileSync(path.join(root,'source/text-corpus-8879120-02/original-plugins.js.gz'))).toString();
const config=JSON.parse(configRaw.slice(configRaw.indexOf('[')).trim().replace(/;$/,''));
const edits=parameters.map((r,i)=>({...r,target:'SYNTHETIC PARAMETER '+i}));
for(const r of parameters){const rows=config.filter(p=>p.name.toLowerCase()===r.plugin);assert.equal(rows.length,1);assert.equal(rows[0].parameters[r.key],r.source);}
const originalConfig=JSON.stringify(config),withBoot=[{name:'OmoriLocale_Bootstrap',status:true,parameters:{}},...config];
const manager=zlib.gunzipSync(fs.readFileSync(path.join(root,'source/inventory-8879120-01/original/js/rpg_managers.js.gz'))).toString();
function method(name){let matches=[];function w(n){if(!n||typeof n!=='object')return;if(n.type==='AssignmentExpression'&&manager.slice(n.left.start,n.left.end)===name&&n.right.type==='FunctionExpression')matches.push(manager.slice(n.start,n.end)+';');for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(w);else if(v&&typeof v==='object')w(v);}}w(acorn.parse(manager,{ecmaVersion:'latest'}));assert.equal(matches.length,1);return matches[0];}
let observed=0;const c=vm.createContext({plugins:withBoot});vm.runInContext('var PluginManager={_scripts:[],_parameters:{}};',c);
const nativeCore=zlib.gunzipSync(fs.readFileSync(path.join(root,'source/inventory-8879120-01/original/js/rpg_core.js.gz'))).toString();
let containsSource;function contains(n){if(!n||typeof n!=='object')return;if(n.type==='Property'&&n.key.name==='contains'&&n.value.type==='ObjectExpression'){const value=n.value.properties.find(p=>p.key.name==='value').value;containsSource=nativeCore.slice(value.start,value.end);}for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(contains);else if(v&&typeof v==='object')contains(v);}}
contains(acorn.parse(nativeCore,{ecmaVersion:'latest'}));assert.ok(containsSource);vm.runInContext('Array.prototype.contains='+containsSource+';',c);
vm.runInContext(method('PluginManager.setup')+method('PluginManager.setParameters'),c);
c.PluginManager.loadScript=function(name){
 if(name==='OmoriLocale_Bootstrap.js'){bootstrap.prepareParameters(withBoot,edits);return;}
 const wanted=edits.filter(e=>e.plugin===name.replace(/\.js$/,'').toLowerCase());
 for(const e of wanted){assert.equal(c.PluginManager._parameters[e.plugin][e.key],e.target);observed++;}
};
vm.runInContext('PluginManager.setup(plugins)',c);assert.equal(observed,157);
const wrong=JSON.parse(originalConfig);const e=parameters[0];wrong.find(p=>p.name.toLowerCase()===e.plugin).parameters[e.key]='WRONG INPUT';
const wrongBefore=JSON.stringify(wrong);assert.throws(()=>bootstrap.prepareParameters(wrong,edits),/Native plugin parameter input mismatch/);assert.equal(JSON.stringify(wrong),wrongBefore,'preflight rejection must leave all parameters unchanged');
const result={schemaVersion:1,status:'passed-static',coreFunctions:46,parameterConsumers:157,modernAndLegacyGuards:'passed',wrongCoreControls:46,wrongParameterControl:'passed before writes',nativeSetup:'actual original PluginManager.setup/setParameters; loadScript doubled',sourceReceiptSha256:hash(receiptRaw),sourceBootstrapSha256:hash(raw),sharedBootstrapSha256:hash(fs.readFileSync(path.join(root,'runtime/multilingual/native-bootstrap.js'))),recipeSha256:hash(fs.readFileSync(__filename)),runtime:'not-run',nativeBoot:'not-run',visual:'not-run',limitation:'Shared primitives and source-only guard fixtures tested; this is not a compiled multilingual display overlay.'};
process.stdout.write(JSON.stringify({result,sourceFixture:{schemaVersion:1,sourceBuild:'8879120',sourceBootstrapSha256:hash(raw),policy:'Original source/parameter before-values only. No translated target code or wording copied.',core,parameters}}));
