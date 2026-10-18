// Isolated actual note refresh/assembly; fake canvas/images, static font advances.
const fs=require('fs'),zlib=require('zlib'),vm=require('vm'),assert=require('assert');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const dir=process.argv[2],evidence=process.argv[3];
const metrics=JSON.parse(fs.readFileSync('source/ru-pizza-font-metrics-2026-10-14-01.json'));
const old=zlib.gunzipSync(fs.readFileSync('source/inventory-8879120-01/original/js/plugins/YIN - Minigame - PizzaDelivery.OMORI.gz')).toString();
const source=fs.readFileSync(dir+'/plugins/YIN - Minigame - PizzaDelivery.js','utf8');
function assignments(code){const out={};function walk(n){if(!n||!n.type)return;if(n.type==='AssignmentExpression'&&n.right.type==='FunctionExpression')out[code.slice(n.left.start,n.left.end)]=code.slice(n.right.start,n.right.end);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(code,{ecmaVersion:'latest'}));return out;}
const before=assignments(old),after=assignments(source),changed=['Window_PizzaDeliveryNote.prototype.refresh','Game_Interpreter.prototype.checkImages'];
assert.deepEqual(Object.keys(after),Object.keys(before));
for(const owner of Object.keys(before))if(!changed.includes(owner))assert.equal(after[owner],before[owner]);
let requests=[],draws=[],blits=0;
const ctx=vm.createContext({ImageManager:{loadPicture(name){requests.push(name);if(name!=='PIZZA-Background')throw new Error('Missing English word sprite: '+name);return {width:620,height:440};}}});
vm.runInContext(fs.readFileSync('runtime/ru-pizza-note.js','utf8'),ctx);
ctx.OmoriRu={renderPizzaNote:ctx.OmoriRuPizzaNote.render};
const actual=vm.runInContext('('+after[changed[0]]+')',ctx);
const native=vm.runInContext('('+before[changed[0]]+')',ctx);
function window(){return {visible:false,contents:{width:620,height:440,fontSize:32,textColor:'white',outlineWidth:4,
 clear(){draws=[];},blt(){blits++;},drawText(text,x,y,width,height){assert.ok(x>=24&&x+width<=580);assert.ok(y>=32&&y+height<=440);draws.push(text);}},
 resetFontSettings(){this.contents.fontSize=32;},textWidth(text){return Array.from(text).reduce((sum,c)=>{const a=metrics.advances[c.codePointAt(0)];if(a===undefined)throw new Error('Missing static glyph advance');return sum+a*this.contents.fontSize;},0);}};}
// Native negative: valid note area/background, fail precisely at RU word sprite.
assert.throws(()=>native.call(window(),'Русская записка'),/Missing English word sprite: PIZZA-Русская/);
// Matching native positive: only the word-resource availability changes.
ctx.ImageManager.loadPicture=name=>({width:name==='PIZZA-Background'?620:60,height:name==='PIZZA-Background'?440:64});
native.call(window(),'This house');
ctx.ImageManager.loadPicture=name=>{requests.push(name);assert.equal(name,'PIZZA-Background');return {width:620,height:440};};
ctx.LanguageManager={getMessageData:key=>{assert.equal(key,'XX_BLUE.Yin_Pizza_Delivery');return metrics.data;}};
vm.runInContext('Array.prototype.contains=Array.prototype.includes;String.prototype.contains=String.prototype.includes;',ctx);
let cases=0,maxLines=0,minFont=32;
for(let h=1;h<=36;h++) {
 const hints=metrics.data.houseHints[h];
 for(let i=0;i<hints.length;i++)for(let j=0;j<hints.length;j++)if(i!==j)for(const part of metrics.data.partPool) {
  const chosen=[h,hints[i],hints[j],part];
  ctx.$gameSystem={_chosenHouses:[],randomizeArray(a){const value=chosen.shift(),at=a.indexOf(value);assert.ok(at>=0);a.unshift(...a.splice(at,1));return a;}};
  ctx.$gameSystem._chosenHouses.contains=function(value){return this.includes(value);};
  const assembly=vm.runInContext('('+after['Game_Interpreter.prototype.generateHouse']+')',ctx);
  const text=assembly.call({houseHints:()=>structuredClone(metrics.data.houseHints)},Math.ceil(h/12));
  assert.equal(text,part+hints[i]+metrics.data.descriptionLink+hints[j]);assert.equal(chosen.length,0);
  const w=window(),result=actual.call(w,text);assert.equal(draws.join(' '),text);
  assert.ok(w.visible);assert.equal(w.contents.textColor,'white');assert.equal(w.contents.outlineWidth,4);
  assert.equal(w.contents.fontSize,result.fontSize);maxLines=Math.max(maxLines,result.lines.length);minFont=Math.min(minFont,result.fontSize);cases++;
 }
}
assert.equal(cases,19944);
vm.runInContext('('+after[changed[1]]+')',ctx).call({});
const narrow=window();narrow.contents.width=10;assert.throws(()=>actual.call(narrow,'Дом'),/no usable content area/);
assert.throws(()=>actual.call(window(),Array(2000).fill('Дом').join(' ')),/does not fit the original note window/);
const split=Array.from(ctx.OmoriRuPizzaNote.linesFor('ДЛИННОЕСЛОВО',s=>s.length*10,30));assert.equal(split.join(''),'ДЛИННОЕСЛОВО');
assert.ok(requests.slice(2).every(name=>name==='PIZZA-Background'));
const report={status:'passed',cases,maxLines,minFont,unchangedFunctionAssignments:Object.keys(before).length-2,
 boundary:'Actual compiled note refresh delegates to the shipped text helper; actual unchanged generateHouse enumerates all ordered distinct hint pairs and 12 introductions. Original RU sprite failure plus matching English positive, viewport/overflow controls and background-only preloader tested.',
 limits:['Canvas, image loading, window services and random choice are mocked. Widths are static unshaped advances from pinned original Latin and final Cyrillic fonts; kerning/hinting/rendered appearance are not established.','No game, full plugin/loader boot, images edited, installation, saves or visual QA.']};
if(evidence){if(fs.existsSync(evidence))throw new Error('Preserve prior evidence');fs.writeFileSync(evidence,JSON.stringify(report,null,2)+'\n');}
process.stdout.write(JSON.stringify(report));
