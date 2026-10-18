// Parse supplied original scripts; never execute them or generate localization text.
const fs = require('node:fs');
const acorn = require('internal/deps/acorn/acorn/dist/acorn');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const methods = new Set(['drawText', 'drawTextEx', 'addText', 'addCommand', 'setHelpText', 'setText']);
const report = {schemaVersion: 1, node: process.version, acorn: acorn.version,
  scriptCount: input.length, parsed: [], errors: [], textCalls: [], labelLiterals: [], stringLiteralCount: 0,
  templateSegmentCount: 0, templateLabelSegments: [],
  limits: ['AST parsing is static; it does not establish reachability or resolve computed code.',
    'The text-call selection is an authored API set, not an exhaustive visible-field inventory.',
    'String labels can be technical protocols rather than speaking characters.']};
for (const file of input) {
  let ast;
  try { ast = acorn.parse(file.source, {ecmaVersion: 'latest', locations: true, sourceType: 'script'}); }
  catch (e) { report.errors.push({asset: file.asset, error: e.message}); continue; }
  report.parsed.push({asset: file.asset, rawSha256: file.rawSha256});
  const walk = (node) => {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'Literal' && typeof node.value === 'string') {
      report.stringLiteralCount++;
      if (/\\n<[^>]+>|\\who\b|^\s*>?(?:[A-Z][A-Z .!?'_-]+|\?\?\?)\s*:/.test(node.value)) {
        report.labelLiterals.push({asset: file.asset, line: node.loc.start.line, value: node.value});
      }
    }
    if (node.type === 'TemplateElement') {
      report.templateSegmentCount++;
      const value = node.value.cooked ?? node.value.raw;
      if (/\\n<[^>]+>|\\who\b|^\s*>?(?:[A-Z][A-Z .!?'_-]+|\?\?\?)\s*:/.test(value)) {
        report.templateLabelSegments.push({asset: file.asset, line: node.loc.start.line, value});
      }
    }
    if (node.type === 'CallExpression' && node.callee.type === 'MemberExpression') {
      const property = node.callee.property;
      const method = node.callee.computed ? property.value : property.name;
      let argument;
      if (methods.has(method)) argument = node.arguments[0];
      if (method === 'push' && node.arguments[0]?.type === 'Literal' && node.arguments[0].value === 'addText') {
        argument = node.arguments[1];
      }
      if (argument) report.textCalls.push({asset: file.asset, line: node.loc.start.line, method,
        argumentSource: file.source.slice(argument.start, argument.end),
        literalValue: argument.type === 'Literal' && typeof argument.value === 'string' ? argument.value : null});
    }
    for (const [key, child] of Object.entries(node)) {
      if (key === 'loc') continue;
      if (Array.isArray(child)) child.forEach(walk);
      else if (child && typeof child === 'object') walk(child);
    }
  };
  walk(ast);
}
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
