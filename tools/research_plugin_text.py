#!/usr/bin/env python3
"""Read enabled scripts and preserve bounded text-call candidates for review.

Line-pattern candidates are not a JavaScript parser or an accepted text inventory.
They do not execute game code or choose speaker identity, gender or wording.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from research_source import decrypt

CALL = re.compile(r'\.(?:drawText(?:Ex)?|addText|addCommand|setHelpText|setText)\s*\(|\.push\s*\(\s*[\"\']addText[\"\']')
NAMEBOX = re.compile(r'\\{1,2}n<[^>]+>|\\{1,2}who\b|[\"\'][A-Z][A-Z .!?\'_-]+:\s')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    registry = args.game_root / 'js/plugins.js'
    raw = registry.read_bytes()
    source = raw.decode('utf-8')
    plugins = json.loads(source[source.index('['):].rstrip().removesuffix(';'))
    enabled = [p for p in plugins if p['status']]
    files, candidates, errors = [], [], []
    for plugin in enabled:
        choices = [args.game_root / 'js/plugins' / (plugin['name'] + suffix)
                   for suffix in ['.OMORI', '.js']]
        path = next((p for p in choices if p.is_file()), None)
        if path is None:
            errors.append({'plugin': plugin['name'], 'error': 'Script file missing'})
            continue
        text, digest = decrypt(path) if path.suffix == '.OMORI' else (
            path.read_text(), hashlib.sha256(path.read_bytes()).hexdigest())
        asset = str(path.relative_to(args.game_root))
        files.append({'asset': asset, 'rawSha256': digest})
        for line_number, line in enumerate(text.splitlines(), 1):
            kinds = []
            if CALL.search(line):
                kinds.append('text-call-candidate')
            if NAMEBOX.search(line):
                kinds.append('namebox-or-labeled-prefix-candidate')
            if kinds:
                candidates.append({'asset': asset, 'line': line_number,
                                   'kinds': kinds, 'sourceLine': line})
    report = {
        'schemaVersion': 1, 'steamBuild': '8879120',
        'pluginConfigurationSha256': hashlib.sha256(raw).hexdigest(),
        'enabledPlugins': len(enabled), 'scriptsRead': len(files),
        'candidateCount': len(candidates),
        'candidateKindCounts': dict(Counter(k for c in candidates for k in c['kinds'])),
        'scripts': files, 'candidates': candidates, 'errors': errors,
        'limits': ['Line-pattern search includes dynamic expressions and false positives.',
                   'It can miss multiline calls, computed dispatch, other APIs and image text.',
                   'Script comments/headers are not automatically excluded or classified as visible.',
                   'No runtime reachability, accepted inventory or new character identity is asserted.'],
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['enabledPlugins', 'scriptsRead', 'candidateCount',
                                           'candidateKindCounts', 'errors']}, indent=2))


if __name__ == '__main__':
    main()
