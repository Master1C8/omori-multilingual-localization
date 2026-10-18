const fs=require('fs'), acorn=require('internal/deps/acorn/acorn/dist/acorn');
const source=fs.readFileSync(0,'utf8'), ast=acorn.parse(source,{ecmaVersion:'latest',allowReturnOutsideFunction:true});
const rows=[];
function walk(n,parents) {
 if(!n||typeof n!=='object'||!n.type)return;
 if(n.type==='CallExpression'||n.type==='NewExpression')rows.push({type:n.type,span:[n.start,n.end],
  callee:source.slice(n.callee.start,n.callee.end),args:n.arguments.map(a=>({span:[a.start,a.end],source:source.slice(a.start,a.end)}))});
 if(n.type==='AssignmentExpression'&&n.right&&n.right.type==='FunctionExpression')rows.push({type:'FunctionAssignment',
  owner:source.slice(n.left.start,n.left.end),span:[n.right.start,n.right.end],source:source.slice(n.right.start,n.right.end)});
 for(const v of Object.values(n)) {if(Array.isArray(v))v.forEach(x=>walk(x,parents.concat(n)));else if(v&&typeof v==='object')walk(v,parents.concat(n));}
}
walk(ast,[]);process.stdout.write(JSON.stringify(rows));
