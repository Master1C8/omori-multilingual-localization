// Native asset/request APIs are replaced; this does not establish real loading.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(__dirname+'/equipment-assets.js','utf8');
function fixture(){
 const timers=new Map(),calls=[],bitmaps=[];let serial=0;
 class XHR{
  constructor(){this.listeners={};this.readyState=0;this.status=0;this.onload=null;this.response=null;}
  open(){this.readyState=1;return 'opened';}
  addEventListener(n,f){(this.listeners[n]||=[]).push(f);}
  fire(n){for(const f of this.listeners[n]||[])f.call(this);if(n==='load'&&this.onload)this.onload();}
  complete(){this.readyState=4;this.status=200;this.response={byteLength:7};this.fire('readystatechange');this.fire('load');this.fire('loadend');}
  send(){if(this.sync)this.complete();return 'sent';}
 }
 class Scene_Map{}
 const player={x:11,y:15,canMove:()=>true};
 const context={XMLHttpRequest:XHR,WeakMap,document:{baseURI:'chrome-extension://fixture/index.html'},
  SceneManager:{_scene:new Scene_Map(),_sceneStarted:false},$gameMap:{mapId:()=>92},$gamePlayer:player,
  ImageManager:{reserveNormalBitmap(...args){calls.push(args);const b={_loadingState:'decrypting',_image:{complete:true,naturalWidth:0,naturalHeight:0}};bitmaps.push(b);return b;}},
  setInterval:f=>{timers.set(++serial,f);return serial;},clearInterval:id=>timers.delete(id)};
 context.window=context;vm.createContext(context);vm.runInContext(source,context);
 return{context,calls,bitmaps,player,tick:()=>{for(const f of [...timers.values()])f();}};
}
{
 const f=fixture();f.tick();assert.equal(f.calls.length,0);
 f.context.SceneManager._sceneStarted=true;f.tick();assert.equal(f.calls.length,2);
 assert.deepEqual(f.calls.map(a=>a[0]),['img/atlases/itemCharms.png','img/atlases/itemWeapon.png']);
 assert(f.calls.every(a=>a[1]===0&&a[2]==='omori-equipment-qa'));
 assert.equal(f.context.__qaEquipmentAssets.phase,'loading');
 for(const b of f.bitmaps){b._loadingState='loaded';Object.assign(b._image,{naturalWidth:64,naturalHeight:32});}
 f.tick();assert.equal(f.context.__qaEquipmentAssets.phase,'ready');f.tick();assert.equal(f.calls.length,2);
 assert.equal(f.player.x,11);assert.equal(f.player.y,15);
}
{
 const f=fixture(),x=new f.context.XMLHttpRequest();x.sync=true;
 assert.equal(x.open('GET','img/atlases/itemWeapon.rpgmvp'),'opened');assert.equal(x.send(),'sent');
 let callbacks=0;x.onload=()=>callbacks++;assert.equal(callbacks,0);
 const row=f.context.__qaAtlasRequests[0];assert(row.events.some(e=>e.event==='load'&&e.onloadPresent===false));
 assert.equal(row.events.find(e=>e.event==='load').responseBytes,7);
 const y=new f.context.XMLHttpRequest();y.open('GET','img/atlases/itemCharms.rpgmvp');y.send();y.onload=()=>callbacks++;y.complete();
 assert.equal(callbacks,1);assert(f.context.__qaAtlasRequests[1].events.some(e=>e.event==='load'&&e.onloadPresent===true));
 const z=new f.context.XMLHttpRequest();z.open('GET','other.png');z.send();assert.equal(f.context.__qaAtlasRequests.length,2);
}
{
 const f=fixture();f.context.SceneManager._sceneStarted=true;delete f.context.ImageManager.reserveNormalBitmap;f.tick();
 assert.equal(f.context.__qaEquipmentAssets.phase,'error');assert.match(f.context.__qaEquipmentAssets.error,/reservation API unavailable/);
}
console.log('PASS guarded two-asset cache fixture, no replay, request return/callback preservation, synchronous lost-handler observation, unrelated requests and missing-API rejection; native proof required.');
