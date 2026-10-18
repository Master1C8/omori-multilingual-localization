// Isolated source-function checks with mocked battlers. No game boot or save access.
const fs = require('node:fs');
const zlib = require('node:zlib');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const originalPath = process.argv[2], deliveredPath = process.argv[3];
const original = zlib.gunzipSync(fs.readFileSync(originalPath)).toString('utf8');
const delivered = fs.readFileSync(deliveredPath, 'utf8');
function extract(source) {
  const ast = acorn.parse(source, {ecmaVersion:'latest'});
  let found;
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'AssignmentExpression' &&
        source.slice(node.left.start,node.left.end) === 'Window_BattleLog.prototype.makeCustomActionText') {
      assert.equal(found,undefined); found = source.slice(node.right.start,node.right.end);
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(walk);
      else if (value && typeof value === 'object') walk(value);
    }
  }
  walk(ast); assert.ok(found); return found;
}
function render(source, type, {name='CustomName', noEffect=false, switch6=false, hp=0, mp=0}={}) {
  const result = {isHit:()=>true,success:true,critical:false,missed:false,evaded:false,
    hpDamage:hp,mpDamage:mp,tpDamage:0,addedStates:[],removedStates:[],elementStrong:false,elementWeak:false};
  const battler = label => ({name:()=>label,result:()=>result,_result:result,_noEffectMessage:noEffect,
    friendsUnit:()=>({getLowestIndexMember:()=>0}),index:()=>0,isStateAffected:()=>false});
  const context = vm.createContext({OmoriRu:{name:b=>b.name()},$gameActors:{actor:id=>battler(id===1?'OMORI':'AUBREY')},
    $gameSwitches:{value:()=>switch6}});
  vm.runInContext('String.prototype.contains = function(s) {return this.indexOf(s) >= 0;};',context);
  const fn = vm.runInContext('(' + extract(source) + ')',context);
  return fn.call({},battler(name),battler(name),{meta:{BattleLogType:type}});
}
let cases = 0;
for (const name of ['OMORI','CustomName']) {
  const en = render(original,'AFRAID',{name,noEffect:true});
  const ru = render(delivered,'AFRAID',{name,noEffect:true});
  assert.match(en,/cannot be AFRAID/);
  assert.match(ru,/нельзя напугать/);
  assert.doesNotMatch(ru,/ЭМОЦИЮ изменить нельзя/);
  const positive = render(delivered,'AFRAID',{name,noEffect:false});
  assert.match(positive,/ЭМОЦИЯ — НАПУГАН/);
  assert.doesNotMatch(positive,/нельзя напугать/);
  cases += 2;
}
for (const switch6 of [false,true]) {
  const en = render(original,'DANDELION',{switch6});
  const ru = render(delivered,'DANDELION',{switch6});
  assert.match(en,switch6 ? /herself again/ : /hisself again/);
  assert.match(ru,/CustomName снова чувствует себя собой\./);
  assert.doesNotMatch(ru,/себя себя|self|her|his/);
  cases++;
}
for (const hp of [1,71]) {
  const en = render(original,'ATTACK',{hp,name:'Group'});
  const ru = render(delivered,'ATTACK',{hp,name:'ГРУППА'});
  assert.match(en,new RegExp(`takes ${hp} damage!`));
  assert.match(ru,new RegExp(`ГРУППА: урон — ${hp}!`));
  cases++;
}
assert.match(render(delivered,'B OMORI SOMETHING CONSUME EMOTION'),/поглощает ЭМОЦИИ/);
cases++;
for(const type of ['CALM DOWN','SPROUT BUNNY FEED','BD COOK','H FACE HEAL']) {
 for(const hp of [-1,-11,-20]) {
  const ru=render(delivered,type,{hp});
  assert.match(ru,new RegExp('восстановление СЕРДЕЦ — '+Math.abs(hp)));
  assert.doesNotMatch(ru,/\d+ СЕРДЕЦ/);cases++;
 }
}
process.stdout.write(JSON.stringify({status:'passed',cases,originalPlaintextSha256:crypto.createHash('sha256').update(original).digest('hex'),
  deliveredRawSha256:crypto.createHash('sha256').update(delivered).digest('hex'),
  boundary:'Actual makeCustomActionText function; battler/actor/switch engine services mocked; no game boot, renderer or save access.'}));
