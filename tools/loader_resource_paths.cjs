// Exact official OneLoader path rules only; no loader/VFS/game initialization.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),path=require('path');
function verify(rows) {
 const raw=zlib.gunzipSync(fs.readFileSync('source/text-corpus-8879120-02/original-plugins.js.gz')).toString();
 const context=vm.createContext({window:{nw:{App:{argv:[]}}},console:{log(){}},
   require:name=>name==='fs'?{readFileSync:()=>raw}:require(name)});
 context.window._logLine=()=>{};
 vm.runInContext(fs.readFileSync('source/loader-reference/_oneloader_configuration.js','utf8'),context);
 const rules=context.window.$ONELOADER_CONFIG.DATA_RULES;
 const early=fs.readFileSync('source/loader-reference/early_loader.js','utf8');
 const start=early.indexOf('class ModFile {'),end=early.indexOf('class RawAsset extends ModFile',start);
 if(start<0||end<start)throw new Error('Official loader class boundary changed');
 vm.runInContext(early.slice(start,end)+';this.TestModFile=ModFile;',context);
 return rows.map(row=>{
   const rule=rules.find(r=>r.jsonKeys.includes(row.category));
   if(!rule)throw new Error('Unsupported loader category');
   const value=new context.TestModFile({json:{_flags:[]}}, {file:path.basename(row.file),base:path.dirname(row.file)},rule);
   const destination=value.injectionPoint.toLowerCase();
   if(destination!==row.originalAsset.toLowerCase())
     throw new Error('Native injection mismatch: '+row.file+' -> '+destination+' expected '+row.originalAsset);
   return {file:row.file,destination};
 });
}
module.exports={verify};
if(require.main===module) {
 try {process.stdout.write(JSON.stringify(verify(JSON.parse(fs.readFileSync(0,'utf8')))));}
 catch(error) {process.stderr.write(error.message);process.exitCode=1;}
}
