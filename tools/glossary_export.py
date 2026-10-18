#!/usr/bin/env python3
"""Copy an explicitly accepted locale into the canonical and project exports.

No wording generation or semantic acceptance. Two file replacements are not an
OS transaction: failures trigger guarded compensating rollback. Git delivery is
coordinator-owned and separate; this tool never publishes, commits or deploys.
"""
import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/omori')
SOURCE_SHA = '11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b'
CLI_SOURCE = '3f1a11ea9079027d4ac258f9851629e5cafd2eca8c34f34483688b4286df25db'
RU_SHA = '100e203e9ce6282bc2023e13f8b239dbcacdb552da24a05324d7789e952c8d15'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def replace_bytes(path, data):
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, name = tempfile.mkstemp(prefix='.omori-export-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def replace_pair(paths, before, after, after_first=None):
    if all(path.read_bytes() == after for path in paths):
        return 0
    changed = []
    try:
        for index, path in enumerate(paths):
            if path.read_bytes() != before:
                raise RuntimeError(f'Export drift at {path}; preserve concurrent changes.')
            replace_bytes(path, after)
            changed.append(path)
            if index == 0 and after_first is not None:
                after_first()
        if any(path.read_bytes() != after for path in paths):
            raise RuntimeError('Export parity changed during integration.')
    except BaseException as original:
        failures = []
        for path in reversed(changed):
            try:
                if path.read_bytes() != after:
                    raise RuntimeError('Concurrent content prevents safe rollback.')
                replace_bytes(path, before)
            except BaseException as rollback_error:
                failures.append(f'{path}: {rollback_error}')
        if failures:
            raise RuntimeError('Incomplete guarded rollback: ' + '; '.join(failures)) from original
        raise
    return len(changed)

def self_check():
    with tempfile.TemporaryDirectory(prefix='omori-export-check-') as name:
        paths = [Path(name) / 'project.json', Path(name) / 'master.json']
        old, new, owner = b'old\n', b'new\n', b'owner\n'
        for path in paths:
            path.write_bytes(old)
        def fail():
            raise RuntimeError('Injected failure between actual file replacements.')
        try:
            replace_pair(paths, old, new, fail)
        except RuntimeError as error:
            assert str(error).startswith('Injected failure')
        else:
            raise AssertionError('Failure injection did not run.')
        assert all(path.read_bytes() == old for path in paths)
        assert replace_pair(paths, old, new) == 2
        assert all(path.read_bytes() == new for path in paths)
        assert replace_pair(paths, old, new) == 0
        assert all(path.read_bytes() == new for path in paths)
        for path in paths:
            path.write_bytes(old)
        def drift():
            paths[1].write_bytes(owner)
        try:
            replace_pair(paths, old, new, drift)
        except RuntimeError as error:
            assert str(error).startswith('Export drift')
        else:
            raise AssertionError('Concurrent drift was not rejected.')
        assert paths[0].read_bytes() == old and paths[1].read_bytes() == owner
    print('Passed: real-file failure rollback; first application and unchanged repeat; concurrent-drift preservation. Synthetic fixtures do not establish editorial quality or canonical delivery.')

def integrate(locale):
    scope = json.loads((ROOT / 'glossary/multilingual-orchestration-usage.json').read_text())
    if locale not in scope['targetLocales']:
        raise RuntimeError('Locale is outside the owner-authorized target set.')
    folder = ROOT / 'glossary' / locale
    acceptance = json.loads((folder / 'acceptance.json').read_text())
    assert acceptance['accepted'] is True and acceptance['cleanFullAudits'] == 2
    assert acceptance['sourceRawSha256'] == SOURCE_SHA
    assert acceptance['sourceCliFingerprint'] == CLI_SOURCE
    source_raw = (MASTER / 'glossary.json').read_bytes()
    assert digest(source_raw) == SOURCE_SHA
    ids = [row['id'] for row in json.loads(source_raw)]
    target_raw = (folder / 'approved.json').read_bytes()
    assert digest(target_raw) == acceptance['targetLayerRawSha256']
    target = json.loads(target_raw)
    assert list(target) == ids and len(ids) == 699
    assert all(set(row) == {'term', 'meaning'} and all(isinstance(v, str) and v.strip()
               for v in row.values()) for row in target.values())
    ru_raw = (ROOT / 'glossary/ru/approved.json').read_bytes()
    assert digest(ru_raw) == RU_SHA
    paths = [ROOT / 'glossary/glossary-translations.json', MASTER / 'glossary-translations.json']
    before = paths[1].read_bytes()
    assert paths[0].read_bytes() == before, 'Project/master export drift; reconcile first.'
    export = json.loads(before)
    assert export['ru'] == json.loads(ru_raw)
    if locale in export and export[locale] != target:
        raise RuntimeError('A different active locale exists; reconcile before replacement.')
    export[locale] = target
    after = (json.dumps(export, ensure_ascii=False, indent=2) + '\n').encode()
    changed = replace_pair(paths, before, after)
    assert digest((MASTER / 'glossary.json').read_bytes()) == SOURCE_SHA
    assert digest((ROOT / 'glossary/ru/approved.json').read_bytes()) == RU_SHA
    print(json.dumps({'locale': locale, 'entries': len(target), 'filesChanged': changed,
                      'fullExportRawSha256': digest(after), 'snapshotByteParity': True,
                      'publication': 'not performed'}, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--apply')
    args = parser.parse_args()
    if args.self_check:
        self_check()
    elif args.apply:
        integrate(args.apply)
    else:
        parser.error('Choose --self-check or --apply <accepted-locale>.')
