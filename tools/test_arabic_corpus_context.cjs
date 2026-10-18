/* Mechanical joining-boundary coverage on saved Arabic inputs, not semantic review. */
'use strict';
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const api=require('./multilingual/delivery/arabic_runs.js');
const joining=require('./multilingual/delivery/arabic_joining.js');
const corpus=process.argv[2],results=[];let records=0,boundaries=0,connected=0;
function edge(s,reverse){let chars=Array.from(s);if(reverse)chars.reverse();return chars.find(c=>joining.type(c)!=='T')||'';}
for(const file of fs.readdirSync(corpus).filter(n=>n.endsWith('.json')).sort()){
 for(const entry of JSON.parse(fs.readFileSync(path.join(corpus,file),'utf8')).entries){
  records++;const text=entry.target.replace(/\\/g,'\x1b').replace(/\x1b\x1b/g,'\\');
  const re=new RegExp('(?:'+api.transparentControlPattern+')+','gi');let m;
  while((m=re.exec(text))){
   boundaries++;const prior=text.slice(0,m.index),following=text.slice(m.index+m[0].length);
   const left=edge(prior.replace(new RegExp(api.transparentControlPattern,'gi'),''),true);
   const right=edge(following.replace(new RegExp(api.transparentControlPattern,'gi'),''),false);
   const expected='DLC'.includes(joining.type(left))&&'DRC'.includes(joining.type(right));
   // Actual controls end after a base/mark cluster and before a base in this corpus.
   const cluster=Array.from(prior).reverse();let take=0;
   for(const c of cluster){take+=c.length;if(joining.type(c)!=='T')break;}
   const leftText=prior.slice(prior.length-take),leftStart=m.index-leftText.length;
   const rendered=api.contextualText({text,index:leftStart},leftText,joining);
   if(leftText && joining.type(leftText.slice(-1))!=='U')assert.equal(rendered.endsWith('\u200d'),expected,entry.id);
   if(expected){
    const first=Array.from(following)[0];assert.equal(first,right,entry.id+' has an unexpected mark/control before the joining base');
    assert(api.contextualText({text,index:m.index+m[0].length},first,joining).startsWith('\u200d'),entry.id);
    connected++;results.push({id:entry.id,controls:m[0].replace(/\x1b/g,'\\'),left,right});
   }
  }
 }
}
console.log(JSON.stringify({status:'passed-current-corpus-joining-context',authoredRecords:records,inlineBoundaries:boundaries,joiningBoundaries:connected,affectedIds:new Set(results.map(r=>r.id)).size,results,boundary:'Unicode joining-type/command-boundary assertions on current authored records; no semantic read, dynamic-name substitution, Canvas pixels or gameplay.',runtime:'not-run'}));
