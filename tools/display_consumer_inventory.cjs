// Read-only AST inventory of potential typed-name display consumers.
const fs = require('fs'), zlib = require('zlib');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const files = JSON.parse(fs.readFileSync(0,'utf8')), rows=[];
for (const file of files) {
 const source=file.source || zlib.gunzipSync(fs.readFileSync(file.path)).toString('utf8');
 let ast;
 try {ast=acorn.parse(source,{ecmaVersion:'latest',allowReturnOutsideFunction:true});}
 catch(e) {throw new Error(file.asset+': '+e.message);}
 function walk(n,parents) {
  if(!n || typeof n!=='object' || !n.type)return;
  if(n.type==='MemberExpression' && !n.computed && ['name','originalName','displayName'].includes(n.property.name)) {
   const p=parents[parents.length-1];
   const expression=p && p.type==='CallExpression' && p.callee===n ? p : n;
   const stmt=parents.slice().reverse().find(x=> /Statement$/.test(x.type) || x.type==='VariableDeclaration');
   const fun=parents.slice().reverse().find(x=>x.type==='AssignmentExpression' && x.right && /FunctionExpression/.test(x.right.type));
   rows.push({asset:file.asset,span:[expression.start,expression.end],expression:source.slice(expression.start,expression.end),
    statement:stmt?source.slice(stmt.start,stmt.end):'',owner:fun?source.slice(fun.left.start,fun.left.end):'',
    ancestors:parents.slice(-6).map(x=>x.type),
    comparisons:parents.filter(x=>x.type==='BinaryExpression' && ['===','!==','==','!=','<','>','<=','>='].includes(x.operator)).map(x=>source.slice(x.start,x.end)),
    calls:parents.filter(x=>x.type==='CallExpression').map(x=>source.slice(x.callee.start,x.callee.end))});
  }
  for(const [k,v] of Object.entries(n)) {
   if(k==='start'||k==='end')continue;
   if(Array.isArray(v))v.forEach(x=>walk(x,parents.concat(n)));
   else if(v&&typeof v==='object')walk(v,parents.concat(n));
  }
 }
 walk(ast,[]);
}
process.stdout.write(JSON.stringify(rows));
