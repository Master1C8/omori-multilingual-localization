#!/usr/bin/env python3
"""Refresh payload resources around a pinned, unchanged tested universal app core.

This is the same packaging boundary used by finalize_after_hebrew.py. It does
not compile, install, or launch a game. Existing outputs are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from write_site_locale_manifest import write_manifest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    args = parser.parse_args()
    seed, payload, release = args.seed.resolve(), args.payload.resolve(), args.release.resolve()
    manifest = json.loads((seed / 'manifest.json').read_text())
    executable = 'mac/Contents/MacOS/OMORI Translation Installer'
    for name in ['mac/Contents/Info.plist', executable]:
        if sha(seed / name) != manifest['files'][name]:
            raise ValueError('Frozen tested app core changed: ' + name)
    architectures = subprocess.check_output(['lipo', '-archs', str(seed / executable)], text=True).split()
    if set(architectures) != {'arm64', 'x86_64'}:
        raise ValueError('Expected the tested universal Mac executable')
    receipt = json.loads((payload / 'payload-receipt.json').read_text())
    catalog = json.loads((payload / 'catalog.json').read_text())
    if sha(payload / 'catalog.json') != receipt['catalogSha256'] or len(catalog['locales']) != 27 or receipt['pendingLocales']:
        raise ValueError('Incomplete or changed release payload')
    for key, row in catalog['objects'].items():
        if sha(payload / 'objects' / key) != row['sha256']:
            raise ValueError('Compressed release object changed')
    app = release / 'OMORI Translation Installer.app'
    archive = release / 'OMORI-Installer-macOS-1.0.0.zip'
    if app.exists() or archive.exists():
        raise ValueError('Preserve existing release output')
    release.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seed / 'mac', app)
    resources = app / 'Contents/Resources'
    resources.mkdir(parents=True)
    shutil.copytree(payload, resources / 'Payload')
    (resources / 'PackageConfig.json').write_text(json.dumps({'catalogSha256': receipt['catalogSha256']}) + '\n')
    write_manifest(resources, 'macos')
    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    subprocess.run(['ditto', '-c', '-k', '--keepParent', str(app), str(archive)], check=True)
    if archive.stat().st_size > 100_000_000:
        raise ValueError('Installer exceeds the 100 MB target')
    files = 0
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.namelist()) != len(set(zipped.namelist())) or zipped.testzip() is not None:
            raise ValueError('Damaged installer archive')
        for path in app.rglob('*'):
            if path.is_file():
                if zipped.read(str(path.relative_to(release))) != path.read_bytes():
                    raise ValueError('Delivered archive differs: ' + str(path))
                files += 1
    output = {'platform': 'macos', 'path': str(archive), 'sha256': sha(archive),
              'bytes': archive.stat().st_size, 'filesReadback': files,
              'catalogSha256': receipt['catalogSha256'], 'locales': receipt['locales'],
              'coreSeedSha256': manifest['files'][executable], 'seedManifestSha256': sha(seed / 'manifest.json'),
              'core': 'Existing tested universal executable; resources refreshed and app re-signed ad hoc',
              'packagingScriptSha256': sha(Path(__file__)),
              'runtime': 'New real-game install not-run; exact locale resources retain their pinned native QA evidence'}
    (release / 'MACOS-RECEIPT.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
