// Generated bootstrap through the real native PluginManager.setup order.
// Native plugin bodies, renderer, filesystem and Steam are replaced by bounded mocks.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto'),zlib=require('zlib');
const dir=process.argv[2],receipt=JSON.parse(fs.readFileSync(dir+'/receipt.json'));
const source=fs.readFileSync(dir+'/plugins/OmoriRu_Bootstrap.js','utf8');
const original=fs.readFileSync('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw/js/rpg_managers.js','utf8');
const setup=original.slice(original.indexOf('PluginManager.setup ='),original.indexOf('PluginManager.checkErrors ='));
const parameterSetter=original.slice(original.indexOf('PluginManager.setParameters ='),original.indexOf('PluginManager.loadScript ='));
const config=zlib.gunzipSync(fs.readFileSync('source/text-corpus-8879120-02/original-plugins.js.gz')).toString();
function canonical(s){return s.replace(/\r\n?/g,"\n").replace(/^function[ \t]*\(/,"function(");}
function make(legacy) {
 const context=vm.createContext({WeakMap,console:{log(){}},PluginManager:{_parameters:{},_scripts:[]}});
 context.PluginManager._scripts.contains=function(x){return this.indexOf(x)!==-1;};
 const seen=new Set();
 for(const row of receipt.coreFunctions) {
  const pieces=row.owner.split('.');let prefix='';
  for(let i=0;i<pieces.length-1;i++) {
   prefix+=(i?'.':'')+pieces[i];if(seen.has(prefix))continue;seen.add(prefix);
   if(pieces[i]==='prototype')continue;
   if(vm.runInContext('typeof '+prefix+' !== "undefined"',context))continue;
   if(i===0)vm.runInContext('var '+prefix+'=function(){};',context);
   else vm.runInContext(prefix+'={};',context);
  }
  vm.runInContext(row.owner+' = '+row.source+';',context);
 }
 if(legacy)vm.runInContext('var originalFunctionString=Function.prototype.toString;Function.prototype.toString=function(){return originalFunctionString.call(this).replace(/^function\\(/,"function (").replace(/\\r?\\n/g,"\\r\\n");};',context);
 vm.runInContext(config,context);
 context.$plugins.unshift({name:'OmoriRu_Bootstrap',status:true,parameters:{}});
 vm.runInContext(setup+parameterSetter,context);
 let consumers=0;
 context.PluginManager.loadScript=function(name) {
  if(name==='OmoriRu_Bootstrap.js'){assert.equal(Object.keys(this._parameters).length,1);vm.runInContext(source,context);return;}
  for(const e of receipt.parameterEdits)if(e.plugin===name.slice(0,-3).toLowerCase()){
   assert.equal(this._parameters[e.plugin][e.key],e.target);consumers++;
  }
 };
 return {context,run:()=>context.PluginManager.setup(context.$plugins),count:()=>consumers};
}
const positive=make();positive.run();
for(const row of receipt.coreFunctions)assert.equal(canonical(vm.runInContext(row.owner+'.toString()',positive.context)),canonical(row.target));
for(const e of receipt.parameterEdits)assert.equal(positive.context.PluginManager._parameters[e.plugin][e.key],e.target);
assert.equal(positive.count(),receipt.parameterEdits.length);assert.ok(positive.context.OmoriRu);
const legacy=make(true);legacy.run();assert.equal(legacy.count(),receipt.parameterEdits.length);
const capture=JSON.parse(fs.readFileSync('diagnostics/ru-direct-launch-2026-10-14/function-serialization.json'));
assert.notEqual(capture.actual,capture.expected);assert.equal(canonical(capture.actual),canonical(capture.expected));
const parameterNegative=make(),e=receipt.parameterEdits[0];
parameterNegative.context.$plugins.find(p=>p.name.toLowerCase()===e.plugin).parameters[e.key]='other build';
assert.throws(parameterNegative.run,/RU plugin parameter input mismatch:/);
const coreNegative=make();
vm.runInContext(receipt.coreFunctions[0].owner+'=function(){return "other build";};',coreNegative.context);
assert.throws(coreNegative.run,/RU core function mismatch:/);
process.stdout.write(JSON.stringify({status:'passed',coreFunctions:receipt.coreFunctions.length,parameterFields:receipt.parameterEdits.length,
 nativeParameterConsumers:positive.count(),legacyParameterConsumers:legacy.count(),actualLegacyFunctionCapture:'verified-format-only',bootstrapSha256:crypto.createHash('sha256').update(source).digest('hex'),
 boundary:'Actual native PluginManager.setup/setParameters, original plugin configuration and compiled bootstrap. Native plugin bodies and global containers mocked; no game renderer or save I/O.'}));
