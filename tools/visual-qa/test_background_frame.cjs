// Fake browser scheduling tests delivery/cancellation, not native macOS occlusion.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(__dirname+'/background-frame-adapter.js','utf8');
function fixture(){
 let next=1,native=new Map(),timers=new Map(),cancelled=[],focusCalls=0;
 const context={performance:{now:()=>1500},setTimeout:f=>{const id=next++;timers.set(id,f);return id;},clearTimeout:id=>timers.delete(id),
  focus:()=>focusCalls++,requestAnimationFrame:f=>{const id=next++;native.set(id,f);return id;},cancelAnimationFrame:id=>{cancelled.push(id);native.delete(id);}};
 context.window=context;vm.createContext(context);vm.runInContext(source,context);
 return{context,native,timers,cancelled,focusCalls:()=>focusCalls};
}
{
 const f=fixture();f.context.focus();assert.equal(f.focusCalls(),0);
 assert.equal(f.context.__qaFrameScheduler.suppressedFocusCalls,1);
}
{
 const f=fixture(),calls=[];f.context.requestAnimationFrame(t=>calls.push(t));
 const callback=[...f.native.values()][0];callback(1200);
 assert.deepEqual(calls,[1200]);assert.equal(f.timers.size,0);assert.equal(f.context.__qaFrameScheduler.nativeDeliveries,1);
 callback(1201);assert.deepEqual(calls,[1200]); // late duplicate cannot advance the engine twice
}
{
 const f=fixture(),calls=[];f.context.requestAnimationFrame(t=>calls.push(t));
 const late=[...f.native.values()][0];[...f.timers.values()][0]();
 assert.deepEqual(calls,[1500]);assert.equal(f.cancelled.length,1);assert.equal(f.context.__qaFrameScheduler.fallbackDeliveries,1);
 late(1501);assert.deepEqual(calls,[1500]);
}
{
 const f=fixture(),calls=[];const id=f.context.requestAnimationFrame(t=>calls.push(t));
 const lateNative=[...f.native.values()][0],lateTimer=[...f.timers.values()][0];f.context.cancelAnimationFrame(id);
 assert.equal(f.native.size,0);assert.equal(f.timers.size,0);lateNative(1600);lateTimer();assert.deepEqual(calls,[]);
}
{
 const f=fixture(),calls=[];const a=f.context.requestAnimationFrame(()=>calls.push('a'));
 f.context.requestAnimationFrame(()=>calls.push('b'));f.context.cancelAnimationFrame(a);[...f.native.values()][0](1700);
 assert.deepEqual(calls,['b']);assert.equal(f.context.__qaFrameScheduler.cancelled,1);
 assert.throws(()=>f.context.requestAnimationFrame(null),/Animation callback must be a function/);
}
console.log('PASS native/fallback exactly-once delivery, late callbacks, cancellation and independent requests; native occlusion still requires game capture.');
