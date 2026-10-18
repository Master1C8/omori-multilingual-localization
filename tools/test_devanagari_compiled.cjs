/* Execute selected actual delivered methods with graphics/game fixtures. */
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
function nodes(source){const found=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type)found.push(n);for(const [k,v]of Object.entries(n)){if(k==='type')continue;if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}}walk(acorn.parse(source,{ecmaVersion:2018}));return found;}
function assignment(source,left){const hits=nodes(source).filter(n=>n.type==='AssignmentExpression'&&source.slice(n.left.start,n.left.end)===left);assert.equal(hits.length,1,left);return source.slice(hits[0].right.start,hits[0].right.end);}
const bootstrap=data.OmoriLocale_Bootstrap,install=data.OmoriLocale_Install;
assert(bootstrap.includes(fs.readFileSync(process.argv[3],'utf8')),'Exact frozen Devanagari adapter missing');
assert(install.includes('root.OmoriLocaleDevanagari.install(root);'));
assert(install.includes('Locale-Devanagari.ttf'),'Delivered font-loading probe missing');
const layouts=vm.runInNewContext('('+assignment(bootstrap,'root.OmoriLocale.keyboardLayouts')+')');
const name=data['Omori Name Input'],english=vm.runInNewContext('('+assignment(name,'VirtualKeyboard.EN')+')');
const klass=nodes(name).find(n=>n.type==='ClassDeclaration'&&n.id.name==='VirtualKeyboard');
const method=klass.body.body.find(n=>n.key.name==='determineLayoutData');
const determine=vm.runInNewContext('(function'+name.slice(method.value.start,method.value.end)+')',{VirtualKeyboard:{EN:english},OmoriLocale:{keyboardLayouts:layouts}});
const keyboard={getLanguage:()=> 'EN',_layoutType:'default'};determine.call(keyboard);
assert.equal(keyboard._currentLayout.length,6);assert.equal(keyboard._layoutCols,14);
const flat=Array.from(keyboard._currentLayout).flat();
for(const key of ['अ','आ','क','ष','्','ि','़','०','९','{confirm}','{bksp}','{lock}','{space}'])assert(flat.includes(key),key);
const maxItems=vm.runInNewContext('(function'+name.slice(klass.body.body.find(n=>n.key.name==='maxItems').value.start,klass.body.body.find(n=>n.key.name==='maxItems').value.end)+')');
assert.equal(maxItems.call(keyboard),84);
keyboard._layoutType='shift';determine.call(keyboard);assert(Array.from(keyboard._currentLayout).flat().includes('Q'));
const allowedNode=nodes(bootstrap).find(n=>n.type==='VariableDeclarator'&&n.id.name==='allowed');
const allowed=vm.runInNewContext('('+bootstrap.slice(allowedNode.init.start,allowedNode.init.end)+')');
const valid=vm.runInNewContext('('+assignment(bootstrap,'root.OmoriLocale.validName')+')',{allowed});
for(const word of ['कृष्ण','क़','हिन्दी','OMORI'])assert.equal(valid(word),true,word);
assert.equal(valid('नाम\u202e'),false);assert.equal(valid('नाम\n'),false);
assert(data['GTP_OmoriFixes'].includes('!OmoriLocale.validName(text)'));
const draws=[],sprites=[];
function Bitmap(width,height){this.width=width;this.height=height;}Bitmap.prototype.drawText=t=>draws.push(t);
function Sprite(bitmap){this.bitmap=bitmap;}function Point(x,y){this.x=x;this.y=y;}
const effect=vm.runInNewContext('('+assignment(data['TDS Text Effects'],'Window_Base.prototype.createLetterEffectSprite')+')',{Bitmap,Sprite,Point});
const window={textWidth:t=>t.length*12,contents:{fontFace:'OMORI_GAME',fontSize:28,textColor:'#fff'},standardPadding:()=>8,_letterEffectSprites:[],_letterEffectSynchIndex:null,_letterEffects:[],_letterEffectContainerSprite:{addChild:s=>sprites.push(s)}};
effect.call(window,{text:'क्षेत्र',index:0,x:0,y:0,height:38,_omoriRunText:'क्षेत्र'});
assert.deepEqual(draws,['क्षेत्र']);assert.equal(sprites.length,1);assert(!sprites[0].bitmap._omoriRtlRun);
const api=require(process.argv[3]);
const refresh=vm.runInNewContext('('+assignment(name,'Window_OmoriNameInputName.prototype.refreshText')+')',{OmoriLocaleDevanagari:api});
const names=[],input={_text:Array.from('कृष्ण'),_textIndex:2,contents:{width:200,height:80,clearRect(){},fillRect(){},drawText:t=>names.push(t)}};
refresh.call(input);assert.deepEqual(names,['कृष्ण']);assert.equal(input._text.join(''),'कृष्ण');
console.log(JSON.stringify({status:'passed-actual-delivered-Hindi-wiring',groups:4,keyboardRows:6,keyboardColumns:14,nativeItems:84,LatinShiftRetained:true,logicalNames:true,wholeEffectRun:true,fontLoadingProbe:true,boundary:'Actual delivered selected methods with graphics/game fixtures; no real Canvas/font loading/scroll/input/gameplay.',runtime:'not-run',visual:'not-run'}));
