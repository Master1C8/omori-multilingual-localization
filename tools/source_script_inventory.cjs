// Parse original game scripts without executing them. Output source literals,
// consumer context and exact source spans, never translated wording.
const fs = require('node:fs');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const crypto = require('node:crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const report = {schemaVersion: 1, node: process.version, acorn: acorn.version,
  scripts: [], strings: [], errors: [], displayCalls: [], catalogConsumers: []};
const sinks = new Set(['drawText', 'drawTextEx', 'addText', 'addCommand', 'setHelpText', 'setText']);
const references = new Set(['getMessageData', 'getTextData', 'getSystemText', 'getPluginText', 'getDatabaseText']);
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
for (const file of input) {
  let ast;
  try { ast = acorn.parse(file.source, {ecmaVersion: 'latest', locations: true, sourceType: 'script'}); }
  catch (error) { report.errors.push({asset: file.asset, error: error.message}); continue; }
  const src = node => file.source.slice(node.start, node.end);
  const boundedCallee = node => ['FunctionExpression', 'ArrowFunctionExpression'].includes(node.type)
    ? '<inline-function>' : src(node);
  const property = node => node?.type === 'MemberExpression'
    ? (node.computed ? node.property.value : node.property.name) : node?.name;
  report.scripts.push({asset: file.asset, rawSha256: file.rawSha256, plaintextSha256: hash(file.source)});
  function walk(node, parents = []) {
    if (!node || typeof node !== 'object' || !node.type) return;
    const functionIndex = parents.findLastIndex(p => ['FunctionExpression', 'FunctionDeclaration', 'ArrowFunctionExpression'].includes(p.type));
    const scopeParents = functionIndex < 0 ? parents : parents.slice(functionIndex + 1);
    if (node.type === 'CallExpression') {
      const method = property(node.callee);
      if (sinks.has(method)) report.displayCalls.push({asset: file.asset, line: node.loc.start.line,
        start: node.start, end: node.end, method, source: src(node)});
      if (method === 'push' && node.arguments[0]?.value === 'addText') report.displayCalls.push({
        asset: file.asset, line: node.loc.start.line, start: node.start, end: node.end,
        method: 'push/addText', source: src(node)});
      const enclosingStatement = [...scopeParents].reverse().find(p => /Statement$/.test(p.type) || p.type === 'VariableDeclarator');
      const assigning = [...scopeParents].reverse().find(p => p.type === 'AssignmentExpression' || p.type === 'VariableDeclarator' || p.type === 'Property');
      if (references.has(method)) report.catalogConsumers.push({asset: file.asset, line: node.loc.start.line,
        start: node.start, end: node.end, method, source: src(node),
        statement: enclosingStatement ? src(enclosingStatement) : null,
        assigning: assigning ? src(assigning) : null,
        ancestorCalls: [...scopeParents].reverse().filter(p => p.type === 'CallExpression').map(p => boundedCallee(p.callee)),
        reference: node.arguments[0]?.type === 'Literal' ? node.arguments[0].value : null});
    }
    const isString = node.type === 'Literal' && typeof node.value === 'string';
    const isTemplate = node.type === 'TemplateElement';
    if (isString || isTemplate) {
      const source = isString ? node.value : (node.value.cooked ?? node.value.raw);
      const parent = parents.at(-1);
      let role = 'needs-role-review';
      let reason = 'AST literal/template segment requires consumer tracing; assignment alone does not prove display.';
      if (parent?.type === 'Property' && parent.key === node && !parent.computed) {
        role = 'preserve-exactly'; reason = 'Object property key.';
      } else if (parent?.type === 'MemberExpression' && parent.property === node) {
        role = 'preserve-exactly'; reason = 'Computed property identifier.';
      } else if (parent?.type === 'BinaryExpression' && ['===', '!==', '==', '!='].includes(parent.operator)) {
        role = 'preserve-exactly'; reason = 'Exact comparison operand.';
      } else if (!source.trim()) {
        role = 'preserve-exactly'; reason = 'Empty/whitespace formatting literal.';
      }
      const enclosing = [...scopeParents].reverse().find(p => /Statement$/.test(p.type) || p.type === 'VariableDeclarator');
      const consumer = [...scopeParents].reverse().find(p => p.type === 'CallExpression');
      const func = [...parents].reverse().find(p => ['FunctionExpression', 'FunctionDeclaration', 'ArrowFunctionExpression'].includes(p.type));
      const owner = func ? parents[parents.indexOf(func) - 1] : null;
      const functionName = func?.id?.name ?? (owner?.type === 'AssignmentExpression' ? src(owner.left)
        : owner?.type === 'VariableDeclarator' ? src(owner.id) : null);
      const assignment = [...parents].reverse().find(p => p.type === 'AssignmentExpression' || p.type === 'VariableDeclarator');
      const field = [...parents].reverse().find(p => p.type === 'Property');
      const propertyKey = field ? (field.computed ? src(field.key) : (field.key.name ?? field.key.value)) : null;
      const argumentIndex = consumer ? consumer.arguments.findIndex(a => a.start <= node.start && node.end <= a.end) : -1;
      const commandObject = [...parents].reverse().find(p => p.type === 'ObjectExpression' &&
        p.properties.some(v => (v.key?.name ?? v.key?.value) === 'code' && typeof v.value?.value === 'number'));
      const commandCode = commandObject?.properties.find(v => (v.key?.name ?? v.key?.value) === 'code')?.value.value ?? null;
      const ancestorCalls = [...scopeParents].reverse().filter(p => p.type === 'CallExpression').map(p => ({
        method: property(p.callee), callee: boundedCallee(p.callee),
        argumentIndex: p.arguments.findIndex(a => a.start <= node.start && node.end <= a.end),
        arguments: p.arguments.map(a => src(a))}));
      report.strings.push({id: `${file.asset}@js:${node.start}:${node.end}`, asset: file.asset,
        source, rawSource: src(node), spanUtf16: [node.start, node.end], nodeType: node.type,
        sourceValueSha256: hash(source), role, reason,
        context: {line: node.loc.start.line, parentType: parent?.type,
          statement: enclosing ? src(enclosing) : null,
          call: consumer ? src(consumer) : null,
          callMethod: consumer ? property(consumer.callee) : null,
          callArgumentIndex: argumentIndex, callArguments: consumer ? consumer.arguments.map(a => src(a)) : [],
          assignmentTarget: assignment ? src(assignment.left ?? assignment.id) : null,
          propertyKey, ancestorCalls, functionName, commandCode,
          commandObject: commandObject ? src(commandObject) : null}, protectedSyntaxStatus: 'AST span classification incomplete'});
    }
    for (const [key, child] of Object.entries(node)) {
      if (key === 'loc') continue;
      if (Array.isArray(child)) child.forEach(v => walk(v, [...parents, node]));
      else if (child && typeof child === 'object') walk(child, [...parents, node]);
    }
  }
  walk(ast);
}
process.stdout.write(JSON.stringify(report));
