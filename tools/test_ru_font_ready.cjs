// Actual packaged install; native boot methods, mocked DOM/font/database services.
// No browser, Canvas, loader boot, game or installer is launched.
const fs=require('fs'),vm=require('vm'),zlib=require('zlib'),assert=require('assert');
const dir=process.argv[2],receipt=JSON.parse(fs.readFileSync(dir+'/receipt.json'));
const source=fs.readFileSync(dir+'/plugins/OmoriRu_Install.js','utf8');
const native=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/rpg_scenes.js.gz')).toString();
function method(name) {const start=native.indexOf(name+' = function(');assert.ok(start>=0);const end=native.indexOf('\n};',start)+3;return native.slice(start,end);}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup() {
 let clock=0,link,nativeReady=true,installed=0;const pending=[];
 const context=vm.createContext({OmoriRu:{install(){installed++;}},Scene_Boot:function(){},Scene_Base:function(){},
  DataManager:{isDatabaseLoaded:()=>nativeReady},Graphics:{isFontLoaded:()=>true},Date:{now:()=>clock},
  document:{fonts:{load(font,text){return new Promise((resolve,reject)=>pending.push({font,text,resolve,reject}));}},
    createElement(){return {};},head:{appendChild(value){link=value;}}}});
 context.Scene_Base.prototype.isReady=()=>true;
 vm.runInContext(method('Scene_Boot.prototype.isReady'),context);
 vm.runInContext(method('Scene_Boot.prototype.isGameFontLoaded'),context);
 vm.runInContext(source,context);assert.equal(installed,1);
 const boot=new context.Scene_Boot();
 return {ready:()=>boot.isReady(),pending,get link(){return link;},clock:v=>clock=v,native:v=>nativeReady=v};
}
(async()=>{
 const s=setup();assert.equal(s.ready(),false);assert.equal(s.pending.length,0);
 s.link.onload();await tick();assert.equal(s.pending.length,receipt.fontInputs.probes.length);
 s.pending.forEach((p,i)=>{const probe=receipt.fontInputs.probes[i];assert.equal(p.font,'16px '+probe.family);assert.equal(p.text,probe.text);});
 for(let i=0;i<s.pending.length-1;i++)s.pending[i].resolve([{status:'loaded'}]);
 await tick();assert.equal(s.ready(),false);
 s.pending.at(-1).resolve([{status:'loaded'}]);await tick();assert.equal(s.ready(),true);
 s.native(false);assert.equal(s.ready(),false);s.native(true);assert.equal(s.ready(),true);
 const css=setup();css.link.onerror();assert.throws(()=>css.ready(),/fallback stylesheet failed/);
 const failed=setup();failed.link.onload();await tick();failed.pending[0].reject(new Error('test font fetch rejection'));await tick();assert.throws(()=>failed.ready(),/test font fetch rejection/);
 const empty=setup();empty.link.onload();await tick();empty.pending[0].resolve([]);await tick();assert.throws(()=>empty.ready(),/fallback font is unavailable/);
 const timeout=setup();timeout.clock(60000);assert.throws(()=>timeout.ready(),/fallback fonts timed out/);
 timeout.link.onload();await tick();timeout.pending.forEach(p=>p.resolve([{status:'loaded'}]));await tick();assert.throws(()=>timeout.ready(),/fallback fonts timed out/);
 assert.deepEqual([...new Set(receipt.fontInputs.probes.map(p=>p.family))].sort(),['GameFont','OMORI_GAME','OMORI_GAME2']);
 for(const file of ['OMORI-RU-Primary.ttf','OMORI-RU-Secondary.ttf','OMORI-RU-Chinese-Fallback.ttf','NotoSansSymbols2-Regular.ttf','mplus-1m-regular.ttf'])assert.ok(receipt.fontInputs.probes.some(p=>p.file===file));
 process.stdout.write(JSON.stringify({status:'passed',probes:s.pending.length,cases:8,boundary:'Actual compiled install and original Scene_Boot methods; DOM stylesheet/font I/O, Graphics and database readiness mocked. No real font load, Canvas rendering or game boot.'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
