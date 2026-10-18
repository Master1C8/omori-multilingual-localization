// Read-only bundled-parser bridge. No game initialization or installed-file writes.
const fs = require('node:fs');
const yaml = require(require('node:path').resolve(process.argv[2]));
const requests = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(requests.map(r => ({asset: r.asset, value: yaml.safeLoad(r.text)}))));
