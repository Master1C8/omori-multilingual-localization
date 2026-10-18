#!/usr/bin/env python3
"""Freeze the verified native helper's complete later-loaded dependency closure."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(root, output, closure_path=None):
    root, output = root.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(root / 'runtime/cli-localization/runs'):
        raise ValueError('Use a new immutable tooling revision inside the existing run')
    packet = Path(closure_path).resolve() if closure_path else root / 'runtime/multilingual/shared-delivery/DEPENDENCY_CLOSURE.json'
    if not packet.is_relative_to(root):
        raise ValueError('Dependency closure must belong to the canonical project')
    closure = json.loads(packet.read_text())
    paths = closure['helperDependencies']
    # Check all inputs before creating a partially copied output revision.
    for name, expected in paths.items():
        source = root / name
        if source.is_symlink() or not source.resolve().is_relative_to(root) or digest(source) != expected:
            raise ValueError('Shared helper identity changed: ' + name)
    font_root = Path(closure['externalFontToolsRoot']).resolve()
    if not font_root.is_relative_to(root / '.venv-fonts') or not font_root.is_dir():
        raise ValueError('Expected retained local fontTools dependency')
    output.mkdir(parents=True)
    copied = {}
    for name, expected in paths.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
        if digest(target) != expected or digest(root / name) != expected:
            raise ValueError('Changed dependency during freeze: ' + name)
        copied[name] = expected
    target_font = output / '.venv-fonts/lib/python3.9/site-packages/fontTools'
    shutil.copytree(font_root, target_font, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    font_hashes = {}
    for path in sorted(target_font.rglob('*')):
        if path.is_symlink():
            raise ValueError('Font dependency contains an unpinned symlink')
        if path.is_file():
            name = path.relative_to(target_font)
            expected = digest(font_root / name)
            if digest(path) != expected:
                raise ValueError('Font dependency changed during copy: ' + str(name))
            font_hashes[str(path.relative_to(output))] = expected
    receipt = {'schemaVersion': 1, 'status': 'frozen', 'projectRoot': str(root),
               'sourceClosureSha256': digest(packet), 'helpers': copied,
               'fontTools': font_hashes,
               'entryPoint': 'tools/multilingual/delivery/native_delivery.py',
               'data': 'Canonical source, authored inputs, installed original fonts and YAML parser stay separately verified read-only inputs.'}
    (output / 'freeze.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {'directory': str(output), 'helpers': len(copied), 'fontToolsFiles': len(font_hashes),
            'entryPoint': str(output / receipt['entryPoint'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--closure', type=Path)
    args = parser.parse_args()
    print(json.dumps(freeze(args.root, args.output, args.closure), indent=2))
