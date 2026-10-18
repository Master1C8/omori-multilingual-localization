// Fake NW.js policy boundary; actual hidden native capture is a separate proof.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const calls=[],handlers={},phases=[];
const native={focus:()=>calls.push('focus'),show:v=>calls.push(['show',v]),on:(n,f)=>handlers[n]=f};
const context={require:n=>{if(n==='fs')return{writeFileSync:(p,s)=>phases.push(JSON.parse(s).phase),renameSync:()=>{}};assert.equal(n,'nw.gui');return{Window:{get:()=>native}}}};
context.window=context;vm.createContext(context);
const source=fs.readFileSync(__dirname+'/background-window-adapter.js','utf8').replace('__STATE_PATH__',JSON.stringify('/fake/state'));vm.runInContext(source,context);
assert.deepEqual(phases,['before-native-window-get','installed']);
native.focus();native.show();native.show(true);assert.deepEqual(calls,[]);
assert.equal(context.__qaWindowPolicy.suppressedNativeFocus,1);
assert.equal(context.__qaWindowPolicy.suppressedShow,2);
native.show(false);assert.deepEqual(calls,[['show',false]]);
handlers.focus();assert.equal(context.__qaWindowPolicy.events[0].event,'focus');
assert.throws(()=>vm.runInContext(source,context),/Duplicate QA window policy/);
console.log('PASS native focus/show suppression, explicit hide delegation, lifecycle evidence and duplicate guard; native capture unproven.');
