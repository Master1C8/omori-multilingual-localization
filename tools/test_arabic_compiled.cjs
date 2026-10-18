/* Execute selected functions from the actual delivered native scripts.
 * Graphics/game objects are fixtures; real Canvas/gameplay remain untested.
 */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
function nodes(source){const found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type)found.push(n);for(const [k,v]of Object.entries(n)){if(k==='type')continue;if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:'latest'}));return found;}
function assignment(source,left){const hits=nodes(source).filter(n=>n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===left);assert.equal(hits.length,1,left);return source.slice(hits[0].right.start,hits[0].right.end);}
const bootstrap=data.OmoriLocale_Bootstrap,install=data.OmoriLocale_Install;
assert(bootstrap.includes(fs.readFileSync(process.argv[3],'utf8')),'Exact frozen run adapter missing from delivered bootstrap');
const joiningFile=require('path').join(require('path').dirname(process.argv[3]),'arabic_joining.js');
if(fs.existsSync(joiningFile))assert(bootstrap.includes(fs.readFileSync(joiningFile,'utf8')),'Exact Unicode joining data/license missing from delivered bootstrap');
assert(install.includes('root.OmoriLocaleArabic.install(root);'));
const keyboard=vm.runInNewContext('('+assignment(bootstrap,'root.OmoriLocale.keyboardLayouts')+')');
const name=data['Omori Name Input'];
const english=vm.runInNewContext('('+assignment(name,'VirtualKeyboard.EN')+')');
const klass=nodes(name).find(n=>n.type==='ClassDeclaration'&&n.id.name==='VirtualKeyboard');
const method=klass.body.body.find(n=>n.key.name==='determineLayoutData');assert(method);
const determine=vm.runInNewContext('(function'+name.slice(method.value.start,method.value.end)+')',{VirtualKeyboard:{EN:english},OmoriLocale:{keyboardLayouts:keyboard}});
const keyWindow={getLanguage:()=> 'EN',_layoutType:'default'};determine.call(keyWindow);
assert.equal(keyWindow._currentLayout.length,5);assert.equal(keyWindow._layoutCols,14);
const flat=Array.from(keyWindow._currentLayout).flat();
for(const key of ['ا','أ','إ','آ','ش','١','{confirm}','{bksp}','{lock}','{space}'])assert(flat.includes(key),key);
keyWindow._layoutType='shift';determine.call(keyWindow);
assert(Array.from(keyWindow._currentLayout).flat().includes('Q'));
const allowedNode=nodes(bootstrap).find(n=>n.type==='VariableDeclarator'&&n.id.name==='allowed');
const allowed=vm.runInNewContext('('+bootstrap.slice(allowedNode.init.start,allowedNode.init.end)+')');
const validName=vm.runInNewContext('('+assignment(bootstrap,'root.OmoriLocale.validName')+')',{allowed});
assert.equal(validName('سامي'),true);assert.equal(validName('أحمد'),true);assert.equal(validName('OMORI'),true);assert.equal(validName('س\u202eامي'),false);
const drawings=[],sprites=[];
function Bitmap(width,height){this.width=width;this.height=height;}
Bitmap.prototype.drawText=function(text){drawings.push(text);};
function Sprite(bitmap){this.bitmap=bitmap;}
function Point(x,y){this.x=x;this.y=y;}
const effect=vm.runInNewContext('('+assignment(data['TDS Text Effects'],'Window_Base.prototype.createLetterEffectSprite')+')',{Bitmap,Sprite,Point});
const window={textWidth:t=>t.length*12,contents:{fontFace:'OMORI_GAME',fontSize:28,textColor:'#fff'},standardPadding:()=>8,_letterEffectSprites:[],_letterEffectSynchIndex:null,_letterEffects:[],_letterEffectContainerSprite:{addChild:s=>sprites.push(s)}};
effect.call(window,{text:'سلام',index:0,x:10,y:0,height:47,_omoriRunText:'سلام'});
assert.deepEqual(drawings,['سلام']);assert.equal(sprites.length,1);assert.equal(sprites[0].bitmap._omoriRtlRun,true);
const api=require(process.argv[3]);
const refresh=vm.runInNewContext('('+assignment(name,'Window_OmoriNameInputName.prototype.refreshText')+')',{OmoriLocaleArabic:api});
const names=[];const input={_text:['س','ا','م','ي'],_textIndex:3,contents:{width:200,height:72,clearRect(){},fillRect(){},drawText:t=>names.push(t)}};
refresh.call(input);assert.deepEqual(names,['سامي']);assert.equal(input._text.join(''),'سامي');
console.log(JSON.stringify({status:'passed-actual-delivered-function-wiring',groups:4,keyboardRows:5,keyboardColumns:14,logicalNames:true,wholeEffectRun:true,boundary:'Selected real delivered methods with graphics/game fixtures; no real Canvas, boot, input interaction or gameplay.'}));
