// Parse-only validation: exact literal offsets/values, no repeated enclosing code.
const fs = require('node:fs');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const crypto = require('node:crypto');
const files = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = {strings: [], errors: []};
for (const file of files) {
  let ast;
  try { ast = acorn.parse(file.source, {ecmaVersion: 'latest', sourceType: 'script'}); }
  catch (error) { result.errors.push({asset: file.asset, error: error.message}); continue; }
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    const literal = node.type === 'Literal' && typeof node.value === 'string';
    const template = node.type === 'TemplateElement';
    if (literal || template) {
      const source = literal ? node.value : (node.value.cooked ?? node.value.raw);
      result.strings.push({id: `${file.asset}@js:${node.start}:${node.end}`, asset: file.asset,
        spanUtf16: [node.start, node.end], nodeType: node.type, source,
        rawSource: file.source.slice(node.start, node.end),
        sourceValueSha256: crypto.createHash('sha256').update(source).digest('hex')});
    }
    for (const [key, value] of Object.entries(node)) {
      if (key === 'loc') continue;
      if (Array.isArray(value)) for (const child of value) walk(child);
      else if (value && typeof value === 'object') walk(value);
    }
  }
  walk(ast);
}
process.stdout.write(JSON.stringify(result));
