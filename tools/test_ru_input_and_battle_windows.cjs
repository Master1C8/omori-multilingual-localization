// Actual source methods only; no game/plugin initialization or rendered window.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert');
const acorn=require('internal/deps/acorn/acorn/dist/acorn'),dir=process.argv[2];
function find(source,predicate) {let found;function walk(n){if(!n||!n.type)return;if(predicate(n)){assert.equal(found,undefined);found=n;}for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:'latest'}));assert.ok(found);return found;}
const nameSource=fs.readFileSync(dir+'/plugins/Omori Name Input.js','utf8');
const original=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/plugins/Omori Name Input.OMORI.gz')).toString('utf8');
const cls=find(nameSource,n=>n.type==='ClassDeclaration'&&n.id.name==='VirtualKeyboard');
class Base {refresh(){}}
let language='en',typed=[],sounds=0;
const context=vm.createContext({Window_Selectable:Base,LanguageManager:{get _language(){return language;}},
 SoundManager:{playOk(){sounds++;},playBuzzer(){},playCancel(){},playCursor(){}},Math});
vm.runInContext(nameSource.slice(cls.start,cls.end)+';this.Keyboard=VirtualKeyboard;',context);
for(const table of ['EN','JP','KR','CH','OMORI_RU']) {
 const n=find(nameSource,n=>n.type==='AssignmentExpression'&&nameSource.slice(n.left.start,n.left.end)==='VirtualKeyboard.'+table);
 vm.runInContext('VirtualKeyboard.'+table+'='+nameSource.slice(n.right.start,n.right.end),context);
 if(table!=='OMORI_RU') {
  const old=find(original,n=>n.type==='AssignmentExpression'&&original.slice(n.left.start,n.left.end)==='VirtualKeyboard.'+table);
  assert.equal(nameSource.slice(n.right.start,n.right.end),original.slice(old.right.start,old.right.end));
 }
}
for(const key of ['{lock}','{confirm}','{space}','{bksp}','{rarrow}','{larrow}','{ruLang}'])context.Keyboard[key]=key;
const keyboard=Object.create(context.Keyboard.prototype);keyboard._layoutType='default';keyboard._isCaps=false;
keyboard._nameWindow={add(c){typed.push(c);return true;},back(){return true;}};
keyboard.determineLayoutData();assert.equal(keyboard.maxCols(),14);assert.equal(keyboard.maxItems(),56);
const lower=keyboard._currentLayout.flat().filter(s=>/^[а-яё]$/.test(s));assert.equal(new Set(lower).size,33);
for(const char of ['с','а','н','н','и']) {
 const index=keyboard._currentLayout.flat().indexOf(char);keyboard.index=()=>index;keyboard.processOk();
}
assert.equal(typed.join(''),'санни');
const lockIndex=keyboard._currentLayout.flat().indexOf('{lock}');keyboard.index=()=>lockIndex;keyboard.processOk();
assert.equal(keyboard._layoutType,'shift');assert.equal(new Set(keyboard._currentLayout.flat().filter(s=>/^[А-ЯЁ]$/.test(s))).size,33);
assert.ok(keyboard._currentLayout.flat().includes('№'));
const languageIndex=keyboard._currentLayout.flat().indexOf('{ruLang}');keyboard.index=()=>languageIndex;keyboard.processOk();
assert.equal(keyboard._ruLatin,true);assert.ok(keyboard._currentLayout.flat().includes('O'));
typed=[];
for(const char of 'OMOCAT') {
 const index=keyboard._currentLayout.flat().indexOf(char);keyboard.index=()=>index;keyboard.processOk();
}
assert.equal(typed.join(''),'OMOCAT');
keyboard.index=()=>languageIndex;keyboard.processOk();assert.equal(keyboard._ruLatin,false);
assert.ok(keyboard._currentLayout.flat().includes('Ё'));
language='jp';keyboard.determineLayoutData();assert.deepEqual(JSON.parse(JSON.stringify(keyboard._currentLayout[0])),JSON.parse(JSON.stringify(context.Keyboard.JP.shift[0].split(' '))));
const fixes=fs.readFileSync(dir+'/plugins/GTP_OmoriFixes.js','utf8');
const validator=find(fixes,n=>n.type==='FunctionDeclaration'&&n.id.name==='isTextInCurrentLanguage');
const validation=vm.createContext({LanguageManager:{defaultLanguage:()=> 'en'}});
const check=vm.runInContext('('+fixes.slice(validator.start,validator.end)+')',validation);
for(const value of ['САННИ','МоёИмя','Имя№1','CustomName'])assert.equal(check(value),true);
assert.equal(check('漢字'),false); // Matching baseline English-channel rejection.
const battle=fs.readFileSync(dir+'/plugins/Omori Battle System.js','utf8');
let windows=0;
for(const owner of ['Window_BattleItem.prototype.drawItem','Window_BattleSkill.prototype.drawItem']) {
 const n=find(battle,n=>n.type==='AssignmentExpression'&&battle.slice(n.left.start,n.left.end)===owner);
 const item={id:1,name:'NATIVE NAME',meta:{}};let displayed;
 const ctx=vm.createContext({DataManager:{itemShortName:i=>i.name},OmoriRu:{displayField:(i,v)=>{assert.equal(i,item);assert.equal(v,item.name);return 'РУССКОЕ ИМЯ';}}});
 const fn=vm.runInContext('('+battle.slice(n.right.start,n.right.end)+')',ctx);
 fn.call({_data:[item],contents:{drawText:s=>displayed=s},itemRect:()=>({x:0,y:0,width:100,height:24}),textPadding:()=>0,
  changePaintOpacity(){},isEnabled:()=>true},0);
 assert.equal(displayed,'РУССКОЕ ИМЯ');assert.equal(item.name,'NATIVE NAME');windows++;
}
process.stdout.write(JSON.stringify({status:'passed',russianLetters:66,windowConsumers:windows,
 boundary:'Actual VirtualKeyboard selector/input/lock methods, native GTP name validator and two actual battle window draw methods. Window, sound, data lookup and rendering services mocked; no game or plugin boot.'}));
