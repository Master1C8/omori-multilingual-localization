// Execute only the original message-macro plugins in a restricted VM. Rendering,
// game state, database loading and storage are absent: this checks text dispatch.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';

const root = process.argv[2];
if (!root) throw new Error('Expected original asset root');
const source = fs.readFileSync(path.join(root, 'js/plugins.js'), 'utf8');
const plugins = JSON.parse(source.slice(source.indexOf('[')).trim().replace(/;$/, ''));
const selected = plugins.filter(p => p.status && p.name.startsWith('YEP_X_MessageMacros'));
const params = Object.fromEntries(selected.map(p => [p.name, p.parameters]));
const context = vm.createContext({ PluginManager: { parameters: name => params[name] } });
vm.runInContext('var Imported = {YEP_MessageCore:true}; var Yanfly = {}; function Window_Base() {};' +
  'Window_Base.prototype.convertEscapeCharacters = function(text) {return text;};', context);
const hashes = [];
for (const plugin of selected) {
  const bytes = fs.readFileSync(path.join(root, 'js/plugins', `${plugin.name}.OMORI`));
  const decoder = crypto.createDecipheriv('aes-256-ctr', Buffer.from('6bdb2e585882fbd48826ef9cffd4c511'), bytes.subarray(0,16));
  const decoded = Buffer.concat([decoder.update(bytes.subarray(16)), decoder.final()]).toString('utf8');
  vm.runInContext(decoded, context, {filename: plugin.name, timeout: 1000});
  hashes.push({plugin: plugin.name, encryptedSha256: crypto.createHash('sha256').update(bytes).digest('hex')});
}
context.inputs = JSON.parse(fs.readFileSync(0, 'utf8'));
const expanded = vm.runInContext('inputs.map(text => Window_Base.prototype.convertMacroText.call({}, text))', context, {timeout: 30000});
process.stdout.write(JSON.stringify({expanded, pluginHashes: hashes}));
