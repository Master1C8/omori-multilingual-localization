"""Statically parse all enabled original plugins without executing their code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from research_source import decrypt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve prior evidence; choose a new output path')
    raw = (args.game_root / 'js/plugins.js').read_bytes()
    text = raw.decode('utf-8')
    plugins = json.JSONDecoder().raw_decode(text[text.index('['):])[0]
    inputs = []
    for plugin in plugins:
        if not plugin['status']:
            continue
        files = [args.game_root / 'js/plugins' / (plugin['name'] + suffix)
                 for suffix in ('.OMORI', '.js')]
        path = next((p for p in files if p.is_file()), None)
        if path is None:
            raise ValueError('Enabled plugin is missing: ' + plugin['name'])
        source, digest = decrypt(path) if path.suffix == '.OMORI' else (
            path.read_text(), hashlib.sha256(path.read_bytes()).hexdigest())
        inputs.append({'asset': str(path.relative_to(args.game_root)),
                       'rawSha256': digest, 'source': source})
    helper = Path(__file__).with_name('inspect_plugin_text_ast.cjs')
    result = subprocess.run(['node', '--expose-internals', str(helper)],
                            input=json.dumps(inputs), text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    report['pluginConfigurationSha256'] = hashlib.sha256(raw).hexdigest()
    report['parserHelperRawSha256'] = hashlib.sha256(helper.read_bytes()).hexdigest()
    report['limits'].append('Template segments are inspected separately; interpolation and computed names remain unresolved.')
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'parsed': len(report['parsed']), 'errors': report['errors'],
                      'stringLiteralCount': report['stringLiteralCount'],
                      'templateSegmentCount': report['templateSegmentCount'],
                      'labelLiterals': report['labelLiterals'],
                      'templateLabelSegments': report['templateLabelSegments']}))


if __name__ == '__main__':
    main()
