// Official loader configuration/path/order functions with fake file providers.
// Does not initialize the loader, game, native plugins, VFS, Steam or encryption.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),path=require('path'),assert=require('assert');
const dir=process.argv[2],manifest=JSON.parse(fs.readFileSync(dir+'/omori-ru-text-8879120/mod.json'));
const inputs=JSON.parse(fs.readFileSync(dir+'/omori-ru-text-8879120/evidence/package-inputs.json'));
const nativeSources=new Map(inputs.resourceSources.map(r=>[r.file,r.asset.toLowerCase()]));
const raw=zlib.gunzipSync(fs.readFileSync('source/text-corpus-8879120-02/original-plugins.js.gz')).toString('utf8');
const context=vm.createContext({window:{nw:{App:{argv:[]}}},console:{log(){}},
 require:name=>name==='fs'?{readFileSync:()=>raw}:require(name)});
context.window._logLine=()=>{};
vm.runInContext(fs.readFileSync('source/loader-reference/_oneloader_configuration.js','utf8'),context);
const rules=context.window.$ONELOADER_CONFIG.DATA_RULES;
vm.runInContext(raw,context);const native=JSON.parse(JSON.stringify(context.$plugins));
const early=fs.readFileSync('source/loader-reference/early_loader.js','utf8');
// Exact class definition, extracted by its pinned next sibling boundary.
const start=early.indexOf('class ModFile {'),end=early.indexOf('class RawAsset extends ModFile',start);
assert.ok(start>=0&&end>start);vm.runInContext(early.slice(start,end)+';this.TestModFile=ModFile;',context);
const injected=new Set();let files=0;
for(const [category,entries] of Object.entries(manifest.files)) {
 if(category==='assets')continue;
 const rule=rules.find(r=>r.jsonKeys.includes(category));assert.ok(rule);
 for(const entry of entries) {
  assert.ok(fs.existsSync(dir+'/omori-ru-text-8879120/'+entry));
  const value=new context.TestModFile({json:{_flags:[]}}, {file:path.basename(entry),base:path.dirname(entry)},rule);
  const destination=value.injectionPoint.toLowerCase();assert.ok(!injected.has(destination));injected.add(destination);
  if(nativeSources.has(entry))assert.equal(destination,nativeSources.get(entry),'Wrong native resource identity: '+entry);
  assert.equal(destination,inputs.injections[entry],'Recorded injection differs from official rule');
  assert.ok(!destination.includes('/data/data/')&&!destination.includes('/plugins/plugins/'));files++;
 }
}
assert.ok(injected.has('data/quests.pluto'));
assert.ok(!injected.has('data/quests.kel'));
const {verify}=require('./loader_resource_paths.cjs');
assert.equal(verify([{category:'data',file:'data/Quests.yml',originalAsset:'data/Quests.PLUTO'}])[0].destination,'data/quests.pluto');
assert.throws(()=>verify([{category:'data',file:'data/Quests.json',originalAsset:'data/Quests.PLUTO'}]),/Native injection mismatch/);
const pluginRules=new Map(),locks=new Set();
for(const entry of manifest.files.plugins) {
 const name=path.basename(entry,'.js').toLowerCase();locks.add(name);pluginRules.set(name,{rule:manifest.plugins_ordered[name]||{at:-1}});
 if(!name.startsWith('omoriru_'))assert.ok(native.some(p=>p.name.toLowerCase()===name),'Unexpected newly enabled native plugin: '+name);
}
context.PluginManager={_parameters:{}};context.$modLoader={success:true,pluginOrderingRules:pluginRules,pluginLocks:locks,
 knownMods:new Map([[manifest.id,{json:manifest}]]),$runScripts(){}};
context.window.$modLoader=context.$modLoader;
vm.runInContext(fs.readFileSync('source/loader-reference/patchplugins.js','utf8'),context);
assert.equal(context.$plugins[0].name,'omoriru_bootstrap');assert.equal(context.$plugins[context.$plugins.length-1].name,'omoriru_install');
const remaining=Array.from(context.$plugins).filter(p=>!p.name.startsWith('omoriru_'));
assert.deepEqual(JSON.parse(JSON.stringify(remaining)),native);
process.stdout.write(JSON.stringify({status:'passed',resourceFiles:files,nativePlugins:native.length,
 boundary:'Actual official ModFile injection-point class, configuration and plugin ordering source. Fake fs supplies only original config; encryption, VFS, native plugin execution and game boot are not exercised.'}));
