// Actual native fallback consumer and packaged YAML; message/window services mocked.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert');
const {execFileSync}=require('child_process');
const dir=process.argv[2]+'/omori-ru-text-8879120';
const quests=JSON.parse(execFileSync('python3',['-c','import yaml,json,sys;print(json.dumps(yaml.safe_load(open(sys.argv[1]))))',dir+'/data/Quests.yml']));
const source=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/plugins/Omori Quest Menu.OMORI.gz')).toString();
const name='Window_OmoriQuestList.prototype.makeCommandList',start=source.indexOf(name+' = function()'),end=source.indexOf('\n};',start)+3;
assert.ok(start>=0&&end>start);
const context=vm.createContext({Window_OmoriQuestList:function(){},LanguageManager:{_language:'en',getMessageData:()=>({})},$dataQuests:quests});
vm.runInContext(source.slice(start,end),context);
const expected=new Map();
for(const p of fs.readdirSync('translation/ru/batches')) {
 const batch=JSON.parse(fs.readFileSync('translation/ru/batches/'+p));
 for(const row of batch.entries)if(row.id.startsWith('data/Quests.PLUTO#')) {
  const path=JSON.parse(row.id.split('#')[1]);expected.set(path[1],row.target);
 }
}
assert.equal(expected.size,35);
const window=new context.Window_OmoriQuestList();window._questList=[...expected.keys()].map(id=>({id}));const commands=[];
window.addCommand=(text,kind,enabled,quest)=>commands.push({text,kind,enabled,id:quest.id});window.makeCommandList();
assert.equal(commands.length,35);
for(const command of commands) {assert.equal(command.text,expected.get(command.id));assert.equal(command.kind,'quest');assert.equal(command.enabled,true);}
context.LanguageManager.getMessageData=()=>({BED:'PRIMARY-CONTROL'});commands.length=0;window.makeCommandList();assert.equal(commands.find(c=>c.id==='BED').text,'PRIMARY-CONTROL');
process.stdout.write(JSON.stringify({status:'passed',fallbackTitles:35,boundary:'Actual original makeCommandList and packaged PLUTO YAML; LanguageManager/window services mocked. Positive primary control preserved. No loader VFS, encryption, game boot or drawing.'}));
