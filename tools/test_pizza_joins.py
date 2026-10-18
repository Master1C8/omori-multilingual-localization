#!/usr/bin/env python3
"""Run the pinned pizza assembly function with delivered data and mocked choices.

No game, renderer, installer or saves are exercised. All reachable ordered pairs
of distinct hint indices and all introduction indices are enumerated, without a cap.
"""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from source_prepare import strict_yaml
from research_source import decrypt

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve previous evidence')
    asset = 'js/plugins/YIN - Minigame - PizzaDelivery.OMORI'
    snapshot = ROOT / 'source/inventory-8879120-01/original' / (asset + '.gz')
    raw = gzip.decompress(snapshot.read_bytes())
    graph = json.loads((ROOT / 'source/inventory-8879120-01/resource-graph.json').read_text())
    record = next(x for x in graph if x['asset'] == asset)
    original = Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw') / asset
    plaintext, encrypted_digest = decrypt(original)
    assert encrypted_digest == record['rawSha256']
    assert plaintext.encode('utf-8') == raw
    # Snapshots hold decrypted UTF-8 program text in this accepted inventory.
    source = raw.decode('utf-8')
    start = source.index('Game_Interpreter.prototype.generateHouse =')
    end = source.index('\n}', start) + 2
    function = source[start:end]
    resource = ROOT / 'build/ru/batches/ru-0192-ui-and-pizza/resources/languages/en/XX_BLUE.HERO.yaml'
    data = strict_yaml(resource.read_text())['Yin_Pizza_Delivery']
    script = r'''
const assert = require('node:assert/strict');
const p = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
global.Game_Interpreter = function() {};
Array.prototype.contains = Array.prototype.includes;
String.prototype.contains = String.prototype.includes;
global.LanguageManager = {getMessageData: key => {
  assert.equal(key, 'XX_BLUE.Yin_Pizza_Delivery'); return p.data;
}};
Game_Interpreter.prototype.houseHints = () => structuredClone(p.data.houseHints);
eval(p.function);
let cases = 0;
const examples = [];
assert.equal(p.data.partPool.length, 12);
assert.deepEqual(Object.keys(p.data.houseHints).map(Number), Array.from({length:36}, (_,i) => i+1));
assert.deepEqual(p.data.theNo, ['The No', 'No']);
for (let h = 1; h <= 36; h++) {
  const hints = p.data.houseHints[h];
  for (let i = 0; i < hints.length; i++) for (let j = 0; j < hints.length; j++) {
    if (i === j) continue;
    for (let k = 0; k < p.data.partPool.length; k++) {
      const selections = [h, hints[i], hints[j], p.data.partPool[k]];
      global.$gameSystem = {_chosenHouses: [], randomizeArray: a => {
        const choice = selections.shift(); const at = a.indexOf(choice);
        assert.ok(at >= 0, 'Selected choice must occur in the actual pool');
        a.unshift(...a.splice(at, 1)); return a;
      }};
      const output = new Game_Interpreter().generateHouse(Math.ceil(h / 12));
      const expected = p.data.partPool[k] + hints[i] + p.data.descriptionLink + hints[j];
      assert.equal(output, expected);
      assert.deepEqual($gameSystem.pizza, [hints[i], hints[j]]);
      assert.deepEqual($gameSystem._chosenHouses, [h]);
      assert.equal(selections.length, 0);
      assert.ok(p.data.partPool[k].endsWith(': '));
      assert.equal(p.data.descriptionLink, ' и ');
      assert.ok(!/[A-Za-z]/.test(output), 'No English prose in assembled directions');
      if (examples.length < 2 || (h === 36 && i === 1 && j === 0 && k === 11)) examples.push(output);
      cases++;
    }
  }
}
console.log(JSON.stringify({cases, examples, houses:36, introductions:12}));
'''
    result = subprocess.run(['node', '-e', script], input=json.dumps({'function': function, 'data': data}),
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    report = {'status': 'passed', **json.loads(result.stdout),
              'resourceSha256': hashlib.sha256(resource.read_bytes()).hexdigest(),
              'consumerSha256': hashlib.sha256(raw).hexdigest(),
              'recipeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'boundary': 'Actual original generateHouse function plus reparsed delivered YAML; random choice and message retrieval mocked',
              'limits': ['No engine loading, rendering, input, routing or game runtime acceptance',
                         'Assertions establish complete assembly/selection preservation, not semantic review of every combination']}
    args.evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
