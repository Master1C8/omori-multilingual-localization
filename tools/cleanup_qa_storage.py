#!/usr/bin/env python3
"""Plan/apply exact, hash-verified QA backup deduplication and movie-frame eviction.

Archived backups remain immutable and retain every path. Decoded PNGs are a cache;
their original movies, decoder, recipe, indexes and receipts must remain available.
No deletion of unknown files, source text, saves, releases or screenshot evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import uuid

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'diagnostics/cleanup-20261018-01'
FRAMES = ROOT / 'source/movie-frames-8879120-01'

def read(p):
    return json.loads(p.read_text())

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def sig(p):
    s = p.lstat()
    assert p.resolve() == p and stat.S_ISREG(s.st_mode), str(p)
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode, s.st_uid, s.st_gid]

def save(p, d):
    with p.open('x') as f:
        json.dump(d, f, indent=2)
        f.write('\n')

def row(p, h):
    s = sig(p)
    assert sha(p) == h and sig(p) == s, str(p)
    return {'path': str(p.relative_to(ROOT)), 'sha256': h, 'signature': s}

def plan():
    d = {'root': str(ROOT), 'links': [], 'deleteFrames': [], 'protected': [],
         'freeBefore': shutil.disk_usage(ROOT).free,
         'policy': 'Immutable archived backup duplicates retain all paths and bytes. Only indexed, unchanged decoded movie PNG cache is deleted. Original movies and all manifests retained.'}
    keepers = {}
    for r in read(EVIDENCE / 'backup-roots.json'):
        base = ROOT / r['path']
        restoration = base.parent.parent / 'restoration.json'
        assert read(restoration)['status'] == 'verified'
        d['protected'].append(row(restoration, sha(restoration)))
        for p in sorted(base.iterdir()):
            assert len(p.name) == 64 and all(c in '0123456789abcdef' for c in p.name)
            item = row(p, p.name)
            key = (p.name, *item['signature'][4:])
            if key not in keepers:
                keepers[key] = item
            elif item['signature'][:2] != keepers[key]['signature'][:2]:
                d['links'].append(dict(item, keeper=keepers[key]))
    print('Verified archived backup objects', flush=True)
    m = read(FRAMES / 'manifest.json')
    assert m['status'] == 'all-pinned-movies-decoded'
    originals = {}
    for movie in m['movies']:
        source = Path(movie['command'][movie['command'].index('-i') + 1])
        originals[str(source)] = movie['sourceSha256']
        decoder = Path(movie['command'][0])
        originals[str(decoder)] = m['ffmpegSha256']
        index = FRAMES / movie['frameIndex']['path']
        assert sha(index) == movie['frameIndex']['sha256']
        d['protected'].append(row(index, sha(index)))
        entries = read(index)
        assert len(entries) == movie['frames']
        expected = {FRAMES / e['path'] for e in entries}
        assert expected == set((index.parent / 'frames').iterdir())
        for e in entries:
            p = FRAMES / e['path']
            assert p.parent == index.parent / 'frames' and p.suffix == '.png'
            d['deleteFrames'].append(row(p, e['sha256']))
        print('Verified movie cache', index.parent.name, len(entries), flush=True)
    for name, h in originals.items():
        p = Path(name)
        s = sig(p)
        assert sha(p) == h and sig(p) == s
        d['protected'].append({'absolutePath': name, 'sha256': h, 'signature': s})
    for p in [FRAMES / 'manifest.json', ROOT / 'tools/source_movie_frames.py']:
        d['protected'].append(row(p, sha(p)))
    assert sha(ROOT / 'tools/source_movie_frames.py') == m['recipeSha256']
    selected = {}
    for x in d['links'] + d['deleteFrames']:
        p = ROOT / x['path']; s = p.stat()
        key = (s.st_dev, s.st_ino)
        z = selected.setdefault(key, [s.st_blocks * 512, s.st_nlink, 0]); z[2] += 1
    d['allocatedBytesEligible'] = sum(b for b, n, count in selected.values() if n == count)
    return d

def verify(x):
    p = Path(x['absolutePath']) if 'absolutePath' in x else ROOT / x['path']
    assert sig(p) == x['signature'] and sha(p) == x['sha256'] and sig(p) == x['signature'], str(p)
    return p

def apply(path):
    path = path.resolve()
    d = read(path)
    assert d['root'] == str(ROOT)
    opened = {l[1:] for l in (EVIDENCE / 'open-files.txt').read_text().splitlines() if l.startswith('n/')}
    for x in d['links'] + d['deleteFrames'] + d['protected']:
        p = verify(x)
        assert str(p) not in opened, 'Open file: ' + str(p)
    print('Whole selection and original regeneration dependencies verified', flush=True)
    changed = []
    with path.with_suffix('.journal.jsonl').open('x') as journal:
        for x in d['links']:
            p = verify(x); keeper = verify(x['keeper'])
            assert 'installer-metadata-final/backups' in str(p) and '/20261017-' in str(p)
            temp = p.with_name('.cleanup-' + uuid.uuid4().hex)
            try:
                os.link(keeper, temp)
                assert sig(p) == x['signature']
                os.replace(temp, p)
            finally:
                if temp.exists(): temp.unlink()
            assert p.stat().st_ino == keeper.stat().st_ino and sha(p) == x['sha256']
            journal.write(json.dumps({'linked': x['path']}) + '\n'); journal.flush()
            changed.append(x)
        for x in d['deleteFrames']:
            p = verify(x)
            assert p.is_relative_to(FRAMES) and p.parent.name == 'frames' and p.name.startswith('frame-') and p.suffix == '.png'
            p.unlink()
            journal.write(json.dumps({'deleted': x['path']}) + '\n'); journal.flush()
        for x in d['protected']: verify(x)
        for x in changed:
            assert sha(ROOT / x['path']) == x['sha256']
        assert all(not (ROOT / x['path']).exists() for x in d['deleteFrames'])
    result = {'status': 'verified', 'linkedBackupDuplicates': len(changed),
              'deletedReproducibleFrames': len(d['deleteFrames']),
              'allocatedBytesEligible': d['allocatedBytesEligible'],
              'freeBefore': d['freeBefore'], 'freeAfter': shutil.disk_usage(ROOT).free,
              'boundary': 'Per-file publication/deletion with journal; not a multi-file transaction.'}
    save(path.with_suffix('.result.json'), result)
    save(FRAMES / 'STORAGE_EVICTED.json', {'status': 'decoded-png-cache-evicted',
         'receipt': str(path.with_suffix('.result.json').relative_to(ROOT)),
         'historicalManifest': 'manifest.json', 'framesAvailable': False,
         'regeneration': 'Use retained tools/source_movie_frames.py with a new --output directory. Original movie hashes, recipe, decoder, per-frame hashes and receipts retained; eviction is not a visual-review result.'})
    return result

if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--plan', type=Path); a.add_argument('--apply', type=Path)
    args = a.parse_args()
    if args.plan:
        d = plan(); save(args.plan, d)
        print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in d.items()}, indent=2))
    elif args.apply:
        print(json.dumps(apply(args.apply), indent=2))
    else: a.error('Choose --plan or --apply')
