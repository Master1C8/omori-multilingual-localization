// DOM/input scheduling fixture; actual native OMORI behavior is verified separately.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(__dirname+'/input-bridge.js','utf8').replaceAll('__STATE_PATH__',JSON.stringify('/qa/state'));
function fixture(){
 const files=new Map(),timers=[],events=[];let updates=0,actions=0;
 const mockFs={existsSync:p=>files.has(p),readFileSync:p=>files.get(p),writeFileSync:(p,v)=>files.set(p,v),renameSync:(a,b)=>{files.set(b,files.get(a));files.delete(a);}};
 const names={90:'ok',88:'escape',37:'left',39:'right',38:'up',40:'down'};
 const Input={_currentState:{unrelated:true},_pressedTime:0,_latestButton:null,fail:false,
  update(){updates++;if(this.fail)throw Error('engine fixture error');let key=Object.keys(names).map(k=>names[k]).find(k=>this._currentState[k]);
   if(key===this._latestButton)this._pressedTime++;else{this._latestButton=key;this._pressedTime=0;}
  }};
 const caught=[];
 const ctx={require:n=>{assert.equal(n,'fs');return mockFs;},Input,Graphics:{frameCount:0},SceneManager:{_scene:{constructor:{name:'fixture'}},catchException(error){caught.push(error);return 'original-error-result';}},
  setInterval:f=>{timers.push(f);return timers.length;},clearInterval(){},console,
  KeyboardEvent:class{constructor(type,options){Object.assign(this,options,{type,isTrusted:false});}},
  document:{dispatchEvent:e=>{events.push(e);Input._currentState[names[e.keyCode]]=e.type==='keydown';}}};
 ctx.window=ctx;vm.createContext(ctx);vm.runInContext(source,ctx);timers[1]();
 return {ctx,files,events,Input,caught,updates:()=>updates,actions:()=>actions,
  command:(id,keyCode)=>{files.set('/qa/state.input-request.json',JSON.stringify({type:'keyPulse',id,keyCode}));timers[0]();},
  tick(){Input.update();if(Input._latestButton==='ok'&&Input._pressedTime===0)actions++;ctx.Graphics.frameCount++;},
  ack:()=>JSON.parse(files.get('/qa/state.input-ack.json'))};
}
{
 const f=fixture();f.command('one',90);for(let n=0;n<10;n++)f.tick();
 assert.equal(f.actions(),1);assert.equal(f.updates(),10);
 assert.deepEqual(f.events.map(e=>e.type),['keydown','keyup']);assert(f.events.every(e=>e.isTrusted===false));
 const ack=f.ack();assert.equal(ack.status,'released');assert.equal(ack.samples.length,3);assert(ack.samples.every(s=>s.current));
 assert.equal(f.Input._currentState.ok,false);assert.equal(f.Input._currentState.unrelated,true);
 f.command('one',90);f.tick();assert.equal(f.events.length,2); // no replay of an old request
}
{
 const f=fixture();f.command('unsupported',116);f.tick();assert.equal(f.events.length,0);
 f.command('cancel',88);for(let n=0;n<4;n++)f.tick();assert.equal(f.ack().status,'released');
 assert.equal(f.events[0].keyCode,88);assert.equal(f.Input._currentState.escape,false);
}
{
 const f=fixture();f.command('error',90);f.Input.fail=true;
 assert.throws(()=>f.tick(),/engine fixture error/);assert.equal(f.ack().status,'error');
 assert.deepEqual(f.events.map(e=>e.type),['keydown','keyup']);assert.equal(f.Input._currentState.ok,false);
}
{
 const f=fixture();f.command('scene-error',88);for(let n=0;n<3;n++)f.tick();
 assert.equal(f.ack().status,'sampled');const error=Error('scene update fixture error');
 assert.equal(f.ctx.SceneManager.catchException(error),'original-error-result');
 assert.deepEqual(f.caught,[error]);assert.equal(f.ack().status,'error');
 assert.match(f.ack().error,/scene update fixture error/);assert.equal(f.Input._currentState.escape,false);
 assert.deepEqual(f.events.map(e=>e.type),['keydown','keyup']);
 f.command('scene-error',88);f.tick();assert.equal(f.events.length,2);
}
console.log('PASS three natural samples, exactly one action, key release, no replay, unsupported-key rejection, unrelated-state preservation and engine-error release. Native game still required.');
