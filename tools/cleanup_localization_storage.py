#!/usr/bin/env python3
"""Reclaim immutable intermediate duplicates and dispensable closed stderr logs.

Never mutate translation/, source/, ZIPs, active locale outputs, or current native
checkpoints. Required evidence paths survive with identical bytes. Hardlinks are
restricted to sealed generated payloads, whose existing workflow forbids edits.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import uuid

ROOT = Path('/Users/antonkrutov/Desktop/omori full translation mod')
DONE = {'packaged-awaiting-review', 'local-scope-complete'}


def read(p):
    return json.loads(p.read_text())


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def signature(p):
    s = p.lstat()
    if p != p.resolve() or not stat.S_ISREG(s.st_mode) or any(x.is_symlink() for x in p.parents):
        raise ValueError('Not an ordinary non-symlink file: ' + str(p))
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, s.st_uid, s.st_gid]


def save_new(p, d):
    with p.open('x') as f:
        json.dump(d, f, indent=2)
        f.write('\n')


def context():
    run = Path(read(ROOT / 'runtime/cli-localization/current.json')['run'])
    state = read(run / 'state.json')
    closed = {l for l, row in state['locales'].items() if row['status'] in DONE}
    protected = []
    for row in state['locales'].values():
        cp = row.get('workflow', {}).get('machinePackageCheckpoint')
        if cp:
            manifest = ROOT / cp['manifest']['path']
            protected += [manifest.parent, ROOT / read(manifest)['inputs']['plaintext']]
    protected += [ROOT / ('build/ru/' + n) for n in
                  ['batches', 'combined-2026-10-14-10', 'display-2026-10-14-24', 'fonts-2026-10-14-14']]
    return run, state, closed, protected


def payloads(closed, protected):
    found = {}

    def add(p, expected=None):
        if any(p.is_relative_to(x) for x in protected) or p.suffix.lower() == '.zip':
            return
        if not (p.is_relative_to(ROOT / 'build') or
                p.is_relative_to(ROOT / 'runtime/multilingual/locales')):
            raise ValueError('Payload outside cleanup scope')
        sig = signature(p)
        if sig[2] >= 4096:
            found[str(p.relative_to(ROOT))] = {'signature': sig, 'expected': expected}

    for locale in sorted(closed):
        base = ROOT / 'runtime/multilingual/locales' / locale
        for receipt in base.rglob('receipt.json'):
            if 'resources' in receipt.relative_to(base).parts:
                continue
            d = read(receipt)
            if d.get('status') != 'passed-plaintext':
                continue
            for row in d.get('files', []):
                p = receipt.parent / row['path']
                if not p.is_relative_to(receipt.parent / 'resources'):
                    continue
                add(p, row['sha256'])
        for accepted in (ROOT / 'build/multilingual-delivery' / locale).glob('*/ACCEPTANCE.json'):
            d = read(accepted)
            manifest = accepted.with_name('manifest.json')
            if d.get('status') != 'passed-technical-candidate' or digest(manifest) != d['manifestSha256']:
                continue
            for row in read(manifest)['files']:
                add(accepted.parent / 'files' / row['path'], row['sha256'])

    # Russian revisions have explicit success receipts; current outputs are excluded.
    for receipt in (ROOT / 'build/ru').glob('*/receipt.json'):
        d = read(receipt)
        if d.get('status') == 'passed' and isinstance(d.get('resources'), list):
            for row in d['resources']:
                add(receipt.parent / row['output'], row['rawSha256'])
        elif d.get('status') == 'passed-static-assembly' and receipt.parent.name.startswith('display-'):
            for part in ['data', 'plugins']:
                for p in (receipt.parent / part).rglob('*'):
                    if p.is_file():
                        add(p)
    return found


def log_references():
    refs = set()
    pattern = re.compile(rb'"([^"\\\r\n]*\.log)"')
    for base in ['translation', 'runtime', 'history', 'publication', 'build']:
        for p in (ROOT / base).rglob('*.json'):
            if (p.is_relative_to(ROOT / 'runtime/storage-cleanup')
                    or 'resources' in p.parts or 'files' in p.parts or p.is_symlink()):
                continue
            raw = p.read_bytes()
            if b'.log' not in raw:
                continue
            for match in pattern.finditer(raw):
                name = match.group(1).decode('utf-8', errors='replace')
                if name.startswith(str(ROOT) + '/'):
                    name = name[len(str(ROOT)) + 1:]
                refs.add(name)
    return refs


def benign_stderr(p):
    marker = ' WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt[0]: prompt must be at most 128 characters path=file://'
    lines = p.read_text(errors='strict').splitlines()
    return all(not line.strip() or (re.match(r'^\d{4}-\d\d-\d\dT', line)
                                   and marker in line and len(line) < 2000) for line in lines)


def protected_hashes(closed):
    files = {p for p in ROOT.rglob('*.zip') if p.is_file()}
    for locale in closed:
        files.update((ROOT / 'translation' / locale / 'batches').glob('*.json'))
    files.update((ROOT / 'translation/ru/batches').glob('*.json'))
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(files)}


def plan():
    run, state, closed, protected = context()
    candidates = payloads(closed, protected)
    by_size = defaultdict(list)
    for name, row in candidates.items():
        by_size[(row['signature'][2], *row['signature'][4:])].append(name)
    groups = defaultdict(list)
    for names in by_size.values():
        if len(names) < 2:
            continue
        for name in names:
            row = candidates[name]
            h = digest(ROOT / name)
            if signature(ROOT / name) != row['signature']:
                raise ValueError('Payload changed during inventory: ' + name)
            if row['expected'] is not None and h != row['expected']:
                continue  # Altered or unverified output is not eligible.
            groups[(row['signature'][2], *row['signature'][4:], h)].append(name)
    links = []
    for group in groups.values():
        keeper = min(group)
        for name in sorted(group):
            if candidates[name]['signature'][:2] == candidates[keeper]['signature'][:2]:
                continue
            links.append({'path': name, 'keeper': keeper, 'sha256': digest(ROOT / keeper),
                          'signature': candidates[name]['signature'],
                          'keeperSignature': candidates[keeper]['signature']})
    refs = log_references()
    logs = []
    for row in state['locales'].values():
        for a in row.get('attempts', []):
            if not a.get('finished') or a['status'] not in {'continue', 'stage-complete'}:
                continue
            p = Path(a['eventsPath']).with_name('stderr.log')
            name = str(p.relative_to(ROOT))
            if p.exists() and name not in refs and p.name not in refs and benign_stderr(p):
                logs.append({'path': name, 'signature': signature(p), 'sha256': digest(p)})
    inodes = {}
    for row in links:
        p = ROOT / row['path'];s = p.stat();key = (s.st_dev, s.st_ino)
        entry = inodes.setdefault(key, [s.st_blocks * 512, s.st_nlink, 0]);entry[2] += 1
    return {'schemaVersion': 1, 'root': str(ROOT), 'run': str(run), 'closedLocales': sorted(closed),
            'policy': 'No translation/source/ZIP edits. Only sealed generated payload hardlinks and unreferenced benign stderr from completed accepted tasks. All bytes/evidence paths retained for payloads. No queue lifecycle changes.',
            'links': links, 'deleteLogs': logs, 'protectedHashes': protected_hashes(closed),
            'estimatedPayloadBytesReclaimed': sum(b for b, n, selected in inodes.values() if n == selected),
            'logBytesReclaimed': sum((ROOT / x['path']).stat().st_blocks * 512 for x in logs),
            'freeBytesBefore': shutil.disk_usage(ROOT).free}


def link_identical(target, keeper, target_sig, keeper_sig, expected):
    if signature(target) != target_sig or signature(keeper) != keeper_sig:
        raise ValueError('File identity changed before mutation')
    if digest(target) != expected or digest(keeper) != expected:
        raise ValueError('File bytes changed before mutation')
    temp = target.with_name('.' + target.name + '.cleanup-' + uuid.uuid4().hex)
    os.link(keeper, temp)
    try:
        if signature(target) != target_sig or signature(keeper) != keeper_sig:
            raise ValueError('File identity changed during linking')
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    if target.stat().st_ino != keeper.stat().st_ino or digest(target) != expected:
        raise ValueError('Hardlink postcondition failed')


def apply(plan_path):
    d = read(plan_path)
    if d['root'] != str(ROOT):
        raise ValueError('Wrong project')
    _, state, closed, protected = context()
    if not set(d['closedLocales']) <= closed:
        raise ValueError('A selected locale resumed writing; make a new plan')
    eligible = payloads(closed, protected)
    refs = log_references()
    # Validate the whole selection before the first mutation, then each file again.
    for row in d['links']:
        for key in ['path', 'keeper']:
            name = row[key]
            if name not in eligible or signature(ROOT / name) != row['signature' if key == 'path' else 'keeperSignature']:
                raise ValueError('Payload no longer eligible: ' + name)
    for row in d['deleteLogs']:
        p = ROOT / row['path']
        if (not p.is_relative_to(Path(d['run']) / 'jobs') or p.name != 'stderr.log'
                or row['path'] in refs or p.name in refs or signature(p) != row['signature']
                or digest(p) != row['sha256'] or not benign_stderr(p)):
            raise ValueError('Log no longer eligible: ' + str(p))
    for name, h in d['protectedHashes'].items():
        if digest(ROOT / name) != h:
            raise ValueError('Protected ZIP/completed translation changed: ' + name)
    changed = 0
    for row in d['links']:
        link_identical(ROOT / row['path'], ROOT / row['keeper'], row['signature'], row['keeperSignature'], row['sha256'])
        changed += 1
    deleted = 0
    for row in d['deleteLogs']:
        p = ROOT / row['path']
        if signature(p) != row['signature'] or digest(p) != row['sha256']:
            raise ValueError('Log changed immediately before deletion')
        p.unlink();deleted += 1
    for name, h in d['protectedHashes'].items():
        if digest(ROOT / name) != h:
            raise ValueError('Protected ZIP/completed translation verification failed: ' + name)
    result = {'status': 'completed', 'linkedDuplicatePayloadFiles': changed, 'removedBenignLogs': deleted,
              'estimatedPayloadBytesReclaimed': d['estimatedPayloadBytesReclaimed'],
              'logBytesReclaimed': d['logBytesReclaimed'], 'verifiedProtectedFiles': len(d['protectedHashes']),
              'freeBytesAfter': shutil.disk_usage(ROOT).free, 'queueObserverPid': read(Path(d['run']) / 'state.json')['supervisorPid'],
              'boundary': 'Per-file atomic hardlink replacement, not a transaction across files. Source/translation/ZIP files never selected. Immutable duplicate bytes retain all evidence paths.'}
    save_new(plan_path.with_suffix('.result.json'), result)
    return result


def self_test():
    with tempfile.TemporaryDirectory(prefix='omori-cleanup-') as name:
        base = Path(name).resolve();a = base / 'a';b = base / 'b';a.write_bytes(b'payload');b.write_bytes(b'payload')
        sa, sb = signature(a), signature(b);h = digest(a)
        link_identical(b, a, sb, sa, h)
        assert a.stat().st_ino == b.stat().st_ino and a.read_bytes() == b'payload'
        c = base / 'c';c.write_bytes(b'payload');sc = signature(c);c.write_bytes(b'changed')
        try:
            link_identical(c, a, sc, signature(a), h)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed target accepted')
        assert c.read_bytes() == b'changed' and a.read_bytes() == b'payload'
        assert not list(base.glob('.*cleanup-*'))
    return {'status': 'passed', 'checks': ['equal-content hardlink postcondition', 'changed-target rejection', 'other bytes preserved', 'temporary link cleanup']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--apply', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    elif args.plan:
        d = plan();save_new(args.plan, d)
        result = {k: v for k, v in d.items() if k not in {'links', 'deleteLogs', 'protectedHashes'}}
        result.update(duplicateFiles=len(d['links']), deletableLogs=len(d['deleteLogs']), protectedFiles=len(d['protectedHashes']))
    elif args.apply:
        result = apply(args.apply)
    else:
        parser.error('Choose --plan, --apply or --self-test')
    print(json.dumps(result, indent=2))
