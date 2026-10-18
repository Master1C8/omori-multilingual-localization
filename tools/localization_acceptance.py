"""Finite, evidence-bound OMORI acceptance gates; never authors text or launches a game.

See runtime/multilingual/shared-acceptance/CONTRACT.json. Public functions are
read-only. Evidence is replayed from existing per-task pipeline records, not a
second status store. A receipt proves recorded work, never that Python read it
semantically. The CLI supplies the independently observed thread identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

INVENTORY = 'source/multilingual/shared-8879120-03/units.json'
INVENTORY_SHA256 = '4faf2a7b0bc682febcbcb03fe67ea7c2cad1ead21723ba5ae47c6f33d265214d'
FROZEN = 'runtime/cli-localization/runs/20261014T124749Z-facf4e91/tooling-direct-v2'
TOTAL_VISIBLE, TOTAL_OCCURRENCES, RETENTIONS = 20717, 20794, 77
MASTER_SOURCE = Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/omori/glossary.json')
MEDIA_MANIFEST = 'source/media-8879120-02/manifest.json'
MEDIA_SHA256 = 'f41a3e16eee1dbf81ef697dbc8c3cacecb5f12e6d446f433d7be8ec507ddad91'
BINDINGS = ('inventorySha256', 'glossarySha256', 'corpusSha256')
ROLES = ('author', 'editor', 'reviewer', 'resources', 'package')
MANDATORY_SURFACES = ('gender-address', 'terminology', 'save-load', 'locale-input',
                      'hud-menus-titles', 'speakers-credits-location', 'image-text',
                      'controls-branches', 'script-layout')
COMPONENTS = ('context', 'repetitions', 'glossaryReferents', 'runtimeBindings', 'regressions')


class GateError(ValueError):
    pass


def _require(ok, message):
    if not ok:
        raise GateError(message)


def _json(path):
    def pairs(items):
        result = {}
        for k, v in items:
            _require(k not in result, 'Duplicate JSON key: ' + k)
            result[k] = v
        return result
    def bad(value):
        raise GateError('Nonfinite JSON number: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=bad)


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _digest(path):
    return _sha(Path(path).read_bytes())


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _safe(root, path, locale=None):
    root = Path(root).resolve()
    path = Path(path)
    _require(not path.is_absolute() and '..' not in path.parts, 'Evidence path must be root-relative: ' + str(path))
    candidate = root / path
    for part in [candidate, *candidate.parents]:
        if part == root:
            break
        _require(not part.is_symlink(), 'Symlink evidence/input rejected: ' + str(path))
    _require(candidate.resolve().is_relative_to(root), 'Evidence escapes root: ' + str(path))
    if locale:
        parts = path.parts
        for prefix in [('translation',), ('glossary',), ('runtime', 'multilingual', 'locales')]:
            if parts[:len(prefix)] == prefix and len(parts) > len(prefix):
                _require(parts[len(prefix)] == locale, 'Cross-locale evidence rejected: ' + str(path))
    return candidate


def _ref(root, path, locale=None):
    p = _safe(root, path, locale)
    _require(p.is_file(), 'Missing regular evidence file: ' + str(path))
    return {'path': str(Path(path)), 'sha256': _digest(p)}


class Evidence:
    def __init__(self, root, locale, declared, unused_operational=(), snapshots=None):
        self.root, self.locale = Path(root).resolve(), locale
        self.allowed = {}
        self.saved = {}
        self.snapshots = snapshots or {}
        _require(isinstance(declared, list), 'evidence must be an array')
        for ref in declared:
            _require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'Invalid evidence reference')
            _require(ref['path'] not in self.allowed, 'Duplicate evidence reference')
            self.allowed[ref['path']] = ref['sha256']
            if ref['path'] in unused_operational:
                _safe(self.root, ref['path'], self.locale)
            else:
                self.path(ref)

    def path(self, ref):
        _require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'Expected {path,sha256} reference')
        _require(self.allowed.get(ref['path']) == ref['sha256'], 'Undeclared work evidence: ' + str(ref['path']))
        actual_ref = self.snapshots.get(ref['path'], ref)
        _require(actual_ref['sha256'] == ref['sha256'], 'Historical snapshot must preserve original bytes')
        actual = _ref(self.root, actual_ref['path'], self.locale)
        _require(actual == actual_ref, 'Evidence SHA256 mismatch: ' + ref['path'])
        self.saved[actual_ref['path']] = actual_ref
        return _safe(self.root, actual_ref['path'], self.locale)

    def read(self, ref):
        return _json(self.path(ref))

    def nested(self, ref):
        # Legacy manifests already declare their own raw evidence hashes.
        _require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'Invalid legacy reference')
        old = self.allowed.get(ref['path'])
        _require(old in (None, ref['sha256']), 'Conflicting evidence SHA256')
        self.allowed[ref['path']] = ref['sha256']
        return self.path(ref)


def _locale(root, locale):
    matrix = _json(_safe(root, 'tools/multilingual/renderer-matrix.json'))
    configs = matrix['locales']
    codes = [r['siteLocale'] for r in configs]
    _require(len(codes) == len(set(codes)) == 26, 'Expected existing 26 unique locale configurations')
    _require(isinstance(locale, str) and locale in codes and locale not in {'en', 'ru', 'zh', 'ja', 'ko'},
             'Unknown, protected or excluded locale: ' + str(locale))
    return next(r for r in configs if r['siteLocale'] == locale)


def _validate_controls(root, locale):
    """Use the frozen actual authoring implementation in an isolated Python import graph."""
    program = r'''
import json, sys
from pathlib import Path
root, locale = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(root / sys.argv[3]))
from locale_tools import Context, validate_entries
ctx = Context(root, root / 'source/multilingual/shared-8879120-03', locale)
glossary = json.loads((root/'translation'/locale/'glossary-snapshot.json').read_text())
entries = []
for path in sorted((root/'translation'/locale/'batches').glob('*.json')):
    entries.extend(json.loads(path.read_text())['entries'])
validate_entries(ctx, entries, glossary['target']['roboheart']['term'])
sys.path.insert(0, str(root/'tools'))
from authoring_omissions import validate_target_presence, validate_source_disposition
for entry in entries:
    unit = ctx.by_id[entry['id']]
    if entry['id'] not in ctx.retained:
        validate_target_presence(unit, entry)
        validate_source_disposition(unit, entry)
'''
    result = subprocess.run([sys.executable, '-B', '-c', program, str(root), locale, FROZEN],
                            capture_output=True, text=True, timeout=300)
    _require(result.returncode == 0, 'Direct-authoring structural validation: ' +
             (result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'helper failed'))


def inspect_locale(root: Path, locale: str) -> dict:
    root = Path(root).resolve()
    _locale(root, locale)
    result = {'locale': locale, 'inventorySha256': None, 'glossarySha256': None,
              'corpusSha256': None, 'authoredVisible': 0, 'totalVisible': TOTAL_VISIBLE,
              'totalOccurrences': TOTAL_OCCURRENCES, 'technicalRetentions': RETENTIONS, 'missingIds': [],
              'corpus': [], 'technicalCorpus': [], 'errors': [], 'localClassificationFindings': [],
              'localClassificationVisibleIds': []}
    try:
        inventory = _safe(root, INVENTORY)
        result['inventorySha256'] = _digest(inventory)
        _require(result['inventorySha256'] == INVENTORY_SHA256, 'Pinned canonical inventory SHA256 differs')
        units = _json(inventory)
        by_id = {u['id']: u for u in units}
        _require(len(by_id) == len(units) == TOTAL_OCCURRENCES, 'Canonical inventory ID/count mismatch')
        retained = _json(_safe(root, 'source/multilingual/shared-8879120-03/technical-retentions.json'))
        retained_ids = {u['id'] for u in retained}
        _require(len(retained_ids) == len(retained) == RETENTIONS and retained_ids <= by_id.keys(), 'Technical retention ID/count mismatch')
        for u in retained:
            _require(u['source'] == by_id[u['id']]['source'], 'Technical retention source mismatch: ' + u['id'])
        result['technicalCorpus'] = [{'id': u['id'], 'source': u['source'], 'target': u['source']}
                                     for u in units if u['id'] in retained_ids]
        visible = [u for u in units if u['id'] not in retained_ids]
        _require(len(visible) == TOTAL_VISIBLE, 'Canonical visible denominator differs')
        glossary_path = _safe(root, f'translation/{locale}/glossary-snapshot.json', locale)
        glossary = _json(glossary_path)
        result['glossarySha256'] = _digest(glossary_path)
        _require(glossary.get('siteLocale') == locale and glossary.get('sourceLocale') == 'en', 'Glossary locale/source mismatch')
        if glossary.get('targetLayerSha256'):
            target_hash = _sha(json.dumps(glossary['target'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
            _require(target_hash == glossary['targetLayerSha256'], 'Glossary target layer hash mismatch')
        authored, batch_hashes = {}, {}
        batch_dir = _safe(root, f'translation/{locale}/batches', locale)
        for path in sorted(batch_dir.glob('*.json')):
            rel = str(path.relative_to(root))
            try:
                path = _safe(root, rel, locale)
                batch_hashes[rel] = _digest(path)
                batch = _json(path)
                _require(batch.get('siteLocale') == locale and batch.get('sourceLocale') == 'en'
                         and batch.get('inventorySha256') == result['inventorySha256'], 'Batch locale/source/inventory mismatch: ' + rel)
                if batch.get('glossarySnapshotSha256') is not None:
                    _require(batch['glossarySnapshotSha256'] == result['glossarySha256'], 'Batch glossary hash mismatch: ' + rel)
                _require(isinstance(batch.get('entries'), list), 'Batch entries missing: ' + rel)
                for e in batch['entries']:
                    id_ = e['id']
                    _require(id_ in by_id and e.get('source') == by_id[id_]['source'], 'Unknown ID or changed exact source: ' + id_)
                    if e.get('sourceValueSha256') is not None:
                        _require(e['sourceValueSha256'] == _sha(e['source'].encode()), 'Authored source hash mismatch: ' + id_)
                    _require(id_ not in authored, 'Duplicate authored ID: ' + id_)
                    _require(e.get('immediateEdit') is True, 'Missing immediateEdit: ' + id_)
                    _require(isinstance(e.get('target'), str), 'Invalid target type: ' + id_)
                    if id_ in retained_ids:
                        _require(e['target'] == e['source'], 'Technical retention changed: ' + id_)
                    if e.get('sourceRoleDisposition') is not None:
                        result['localClassificationFindings'].append({'id': id_, 'disposition': e['sourceRoleDisposition']})
                    authored[id_] = e
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as exc:
                result['errors'].append(str(exc))
        local_ids = set()
        for path in sorted((root / 'translation' / locale).glob('technical-retentions*.json')):
            rel = str(path.relative_to(root))
            doc = _json(_safe(root, rel, locale))
            _require(doc.get('siteLocale') == locale and doc.get('sourceInventorySha256', doc.get('inventorySha256')) == result['inventorySha256'],
                     'Local classification locale/inventory mismatch: ' + rel)
            reference = _ref(root, rel, locale)
            for finding in doc['entries']:
                id_ = finding.get('id')
                _require(id_ in by_id and finding.get('source') == by_id[id_]['source'],
                         'Local classification exact source mismatch: ' + str(id_))
                result['localClassificationFindings'].append({'id': id_, 'finding': finding, 'evidence': reference,
                                                              'canonicalVisible': id_ not in retained_ids})
                if id_ not in retained_ids:
                    local_ids.add(id_)
        result['localClassificationVisibleIds'] = [u['id'] for u in visible if u['id'] in local_ids]
        result['missingIds'] = [u['id'] for u in visible if u['id'] not in authored]
        result['corpus'] = [{'id': u['id'], 'source': u['source'], 'target': authored[u['id']]['target']}
                            for u in visible if u['id'] in authored]
        result['authoredVisible'] = len(result['corpus'])
        result['corpusSha256'] = _sha(_bytes(result['corpus']))
        # Do not let locale-local classification remove canonical visible IDs.
        if not result['errors']:
            _validate_controls(root, locale)
        for rel, digest in batch_hashes.items():
            _require(_digest(_safe(root, rel, locale)) == digest, 'Authored inputs changed during inspection: ' + rel)
        _require(_digest(inventory) == result['inventorySha256'] and _digest(glossary_path) == result['glossarySha256'],
                 'Pinned inputs changed during inspection')
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, subprocess.SubprocessError) as exc:
        result['errors'].append(str(exc))
    return result


def _bindings(info):
    return {key: info[key] for key in BINDINGS}


def _pair(row):
    return _sha(_bytes({key: row[key] for key in ('id', 'source', 'target')}))


def _id_list(evidence, ref):
    path = evidence.path(ref)
    if path.suffix == '.json':
        ids = _json(path)
    else:
        raw = path.read_bytes()
        _require(not raw or raw.endswith(b'\n'), 'ID list requires final LF')
        ids = raw.decode('utf-8').splitlines()
    _require(isinstance(ids, list) and all(_text(x) for x in ids) and len(ids) == len(set(ids)), 'Invalid/duplicate actual read IDs')
    return ids


def _rows(document):
    rows = document if isinstance(document, list) else document.get('rows', document.get('entries'))
    _require(isinstance(rows, list), 'Missing exact review rows')
    result = {}
    for row in rows:
        target = row.get('target', row.get('authoredTarget'))
        _require(_text(row.get('id')) and isinstance(row.get('source'), str) and isinstance(target, str), 'Invalid source/target review row')
        _require(row['id'] not in result, 'Duplicate review row: ' + row['id'])
        normalized = {'id': row['id'], 'source': row['source'], 'target': target}
        for key, text in [('sourceSha256', row['source']), ('targetSha256', target)]:
            _require(key not in row or row[key] == _sha(text.encode('utf-8')), 'Reviewed pair hash mismatch')
        result[row['id']] = normalized
    return result


def _read_bundle(evidence, bundle, corpus):
    _require(bundle.get('kind') in {'semantic', 'preparatory', 'closure'} and _text(bundle.get('sessionId')), 'Unidentified read kind/session')
    raw_rows = evidence.read(bundle['rows'])
    _require(isinstance(raw_rows, list) and all(set(('sourceSha256', 'targetSha256')) <= r.keys() for r in raw_rows),
             'New reads require explicit per-ID sourceSha256 and targetSha256, not corpus enumeration')
    rows = _rows(raw_rows)
    ids = _id_list(evidence, bundle['ids'])
    _require(set(ids) == set(rows), 'Actual read IDs differ from review rows')
    decisions = evidence.read(bundle['decisions'])
    _require(isinstance(decisions, list), 'Read decisions must be an array')
    decided = set()
    for decision in decisions:
        _require(decision.get('decision') in {'clean', 'finding'} and _text(decision.get('reason')), 'Missing actual read decision/reason')
        source_rows = _rows(evidence.read(decision['sourceArtifact']))
        selected = decision.get('ids', [decision.get('id')])
        _require(isinstance(selected, list) and selected, 'Decision has no actual IDs')
        for id_ in selected:
            _require(id_ in rows and id_ not in decided and source_rows.get(id_) == rows[id_], 'Decision/source artifact pair mismatch: ' + str(id_))
            decided.add(id_)
    _require(decided == set(ids), 'Read IDs lack decisions')
    for id_, row in rows.items():
        _require(id_ in corpus and row['source'] == corpus[id_]['source'], 'Review source/ID outside canonical visible corpus: ' + id_)
    outcome = {id_: d['decision'] for d in decisions for id_ in d.get('ids', [d.get('id')])}
    return {id_: {'pairSha256': _pair(row), 'sessionId': bundle['sessionId'],
                  'kind': bundle['kind'], 'decision': outcome[id_]} for id_, row in rows.items()}


def _legacy_read(ev, item, info):
    """Import actual historical read artifacts, retaining provisional vs semantic scope."""
    manifest_path = ev.path(item['receipt'])
    doc = _json(manifest_path)
    fmt = item.get('format')
    _require(fmt in {'de-parts', 'es-catalogs', 'es419-semantic', 'fr-preparatory', 'pt-paired'}, 'Unknown legacy read format')
    _require(_text(item.get('sessionId')), 'Legacy reader identity required')
    _require(doc.get('siteLocale', ev.locale) == ev.locale, 'Legacy locale mismatch')
    corpus = {r['id']: r for r in info['corpus']}
    technical = {r['id']: r for r in _json(_safe(ev.root, 'source/multilingual/shared-8879120-03/technical-retentions.json'))}
    imported = {}
    kind = 'preparatory' if fmt in {'fr-preparatory', 'pt-paired'} else 'semantic'

    def get(relative, digest, base):
        p = Path(relative)
        if p.is_absolute():
            _require(p.is_relative_to(ev.root), 'Legacy absolute path escapes root')
            p = p.relative_to(ev.root)
        else:
            p = base / p
        ref = {'path': str(p), 'sha256': digest}
        return ev.nested(ref)

    def add(rows, ids=None):
        original_rows = rows if isinstance(rows, list) else rows.get('rows', rows.get('entries'))
        unique_rows = {}
        for row in original_rows:
            normalized = {'id': row['id'], 'source': row['source'], 'target': row.get('target', row.get('authoredTarget'))}
            if row['id'] in technical and normalized['target'] is None:
                normalized['target'] = row['source']
            _require(row['id'] not in unique_rows or unique_rows[row['id']] == normalized, 'Conflicting historical read pairs')
            unique_rows[row['id']] = normalized
        by_id = _rows(list(unique_rows.values()))
        chosen = list(by_id) if ids is None else ids
        _require(len(chosen) == len(set(chosen)) and set(chosen) <= by_id.keys(), 'Legacy read-ID/rows mismatch')
        for id_ in chosen:
            row = by_id[id_]
            expected = corpus.get(id_, technical.get(id_))
            _require(expected is not None and expected['source'] == row['source'], 'Legacy exact source mismatch: ' + id_)
            if id_ in technical:
                continue
            imported[id_] = {'pairSha256': _pair(row), 'sessionId': item['sessionId'], 'kind': kind}

    locale_base = Path('translation') / ev.locale
    if fmt == 'de-parts':
        _require(doc.get('inventorySha256') == info['inventorySha256'] and
                 doc.get('glossarySnapshotSha256') == info['glossarySha256'], 'Legacy de input binding mismatch')
        hashes = doc.get('evidenceHashes', {})
        required = ['paired-read-ids.txt', 'paired-read-rows.json']
        found = {}
        for name in required + ['reading-notes.json']:
            paths = [p for p in hashes if p.endswith('/' + name)]
            if name == 'reading-notes.json' and not paths:
                continue
            _require(len(paths) == 1, 'Missing/ambiguous legacy read artifact: ' + name)
            found[name] = get(paths[0], hashes[paths[0]], locale_base)
        _require('reading-notes.json' in found or _text(doc.get('readingMethod')), 'Actual reading notes required')
        if 'reading-notes.json' in found:
            _require(bool(_json(found['reading-notes.json'])), 'Empty reading notes')
        ids = found['paired-read-ids.txt'].read_text().splitlines()
        add(_json(found['paired-read-rows.json']), ids)
    elif fmt == 'es-catalogs':
        _require(doc.get('sourceInventorySha256') == info['inventorySha256'] and
                 doc.get('glossarySnapshotSha256') == info['glossarySha256'], 'Legacy es input binding mismatch')
        hashes = doc.get('evidence', {})
        base = manifest_path.parent.relative_to(ev.root)
        actual_rows, catalogs, ids = [], [r for r in doc.get('catalogs', []) if isinstance(r, dict) and r.get('path')], []
        for name, digest in hashes.items():
            if ('-rows-' in name or '-rows.' in name) and name.endswith('.jsonl'):
                p = get(name, digest, base)
                loaded = [json.loads(line) for line in p.read_text().splitlines()]
                match = re.search(r'-rows-(\d{4})-\d+-\d+\.jsonl$', name)
                if match:
                    matches = list({c['path']: c for c in catalogs if Path(c['path']).name.startswith(ev.locale + '-' + match.group(1) + '-')}.values())
                    _require(len(matches) == 1, 'Ambiguous saved read page/catalog binding')
                    for row in loaded:
                        row['batch'] = Path(matches[0]['path']).name
                        row['index'] = row.get('row', row.get('index', row.get('index0')))
                actual_rows.extend(loaded)
            elif '-decisions' in name and name.endswith('.json'):
                decisions = _json(get(name, digest, base))
                catalogs.extend(decisions.get('catalogs', []))
            elif name.endswith('-read-ids.txt') and 'cumulative' not in name :
                ids.extend(get(name, digest, base).read_text().splitlines())
        _require(actual_rows and catalogs and ids, 'Legacy es lacks actual rows/decisions/read IDs')
        decided = set()
        for catalog in catalogs:
            _require(_text(catalog.get('decision')), 'Legacy catalog lacks read decision')
            name = Path(catalog['path']).name
            selected = [r for r in actual_rows if Path(str(r.get('batch', r.get('authoredBatch', r.get('batchPath', r.get('catalog', '')))))).name == name]
            indices = set()
            for lo, hi in catalog.get('pages', []):
                _require(isinstance(lo, int) and isinstance(hi, int) and 0 <= lo < hi <= catalog['count'], 'Invalid actual read page')
                indices.update(range(lo, hi))
            indexed = {r.get('index', r.get('index0')) for r in selected}
            if indexed == {None}:
                _require(indices == set(range(catalog['count'])) and len(selected) == catalog['count']
                         and all(r.get('authoredBatchSha256') == catalog['sha256'] for r in selected),
                         'Legacy complete catalog lacks bound actual rows')
                decided.update(r['id'] for r in selected)
            else:
                _require(indices and indices <= indexed, 'Legacy decision pages lack actual read rows')
                decided.update(r['id'] for r in selected if r.get('index', r.get('index0')) in indices)
        _require(decided <= set(ids), 'Legacy decisions exceed actual read IDs')
        # Supplementary/context rows without catalog decisions are preserved, not promoted.
        add([r for r in actual_rows if r['id'] in decided])
    elif fmt == 'es419-semantic':
        _require(doc.get('sourceUnitsSha256') == info['inventorySha256'] and
                 doc.get('glossarySnapshotSha256') == info['glossarySha256'], 'Legacy es-419 binding mismatch')
        base = manifest_path.parent.relative_to(ev.root)
        rows = _json(get('review-rows.json', doc['reviewRowsSha256'], base))
        ids = get('reviewed-ids.txt', doc['reviewedIdsSha256'], base).read_text().splitlines()
        _require(doc.get('pages') and _text(doc.get('fullSemanticAudit')), 'Missing actual semantic reading record')
        # Page identities bind the actual displayed pairs, not just generated cumulative rows.
        page_ids = set()
        for page in doc['pages']:
            p = get(page['path'], page['sha256'], Path())
            page_doc = _json(p)
            displayed = page_doc if isinstance(page_doc, list) else page_doc['rows']
            for row in displayed:
                expected = corpus.get(row['id'], technical.get(row['id']))
                _require(expected is not None and expected['source'] == row['source'], 'Displayed legacy source mismatch')
                page_ids.add(row['id'])
        _require(page_ids - technical.keys() <= set(ids), 'Displayed page IDs missing from read list')
        add(rows, [id_ for id_ in ids if id_ in page_ids])
    elif fmt == 'fr-preparatory':
        _require(doc.get('status') in {'actual-paired-reading-provisional-only', 'provisional-source-target-issue-collection'},
                 'Not an actual provisional reading')
        rows_ref = item.get('rows')
        _require(rows_ref is not None, 'fr import requires declared exact saved rows reference')
        _require(rows_ref['sha256'] == doc.get('rowsSha256', doc.get('readRowsSha256')), 'fr actual-read row artifact hash mismatch')
        rows = ev.read(rows_ref)
        rows = [{**r, **r['entry']} if 'entry' in r else r for r in rows]
        if doc.get('actualReadIds'):
            selected = doc['actualReadIds']
            _require(len(selected) == doc.get('actualReadCount', doc.get('rows')), 'Provisional actual read count mismatch')
            add(rows, selected)
        else:
            selected = set()
            for page in doc.get('pages', []):
                lo = page.get('authorRowStartInclusive', page.get('offset', page.get('start')))
                hi = page.get('authorRowEndExclusive', page.get('endExclusive', page.get('end')))
                _require(isinstance(lo, int) and isinstance(hi, int) and 0 <= lo < hi, 'Invalid actual provisional read page')
                selected.update(r['id'] for r in rows if r.get('batch') == page['batch'] and lo <= r.get('authorRow', r.get('rowIndex', -1)) < hi)
            _require(len(selected) == doc.get('rows', doc.get('actualReadCount')), 'Provisional page/row count mismatch')
            add([r for r in rows if r['id'] in selected])
    else:
        source = doc.get('sourceSha256', doc.get('bindings', {}).get('source'))
        glossary = doc.get('glossarySnapshotSha256', doc.get('bindings', {}).get('glossary'))
        _require(source == info['inventorySha256'] and glossary == info['glossarySha256'], 'Legacy pt input binding mismatch')
        reads = doc.get('reads', [])
        if not reads and doc.get('mapRowsSha256'):
            stem = manifest_path.name.split('-paired-read-result')[0]
            for name, plural in [('map', 'map'), ('quest', 'quests'), ('skill', 'skills')]:
                reads.append({'file': 'validation/' + stem + '-' + plural + '-paired-rows.json',
                              'sha256': doc[name + 'RowsSha256'], 'actualReadRanges': doc[name + 'ReadRanges'],
                              'occurrencesRead': doc[name + 'OccurrencesRead']})
        _require(reads, 'pt import requires actual read ranges and hashed row artifacts; contract-only findings retain their scope')
        for read in reads:
            p = get(read['file'], read['sha256'], locale_base)
            raw = _json(p)
            rows = raw if isinstance(raw, list) else raw['rows']
            indices = set()
            for lo, hi in read['actualReadRanges']:
                _require(0 <= lo < hi <= len(rows), 'pt actual read range invalid')
                indices.update(range(lo, hi))
            _require(len(indices) == read.get('occurrencesRead', read.get('occurrences')), 'pt actual range count mismatch')
            add([rows[i] for i in sorted(indices)])
    _require(imported, 'No concrete reusable legacy pairs')
    return imported



def _legacy_obligations(ev, item, info):
    """Carry native findings into a finite ledger without generating dispositions."""
    path = ev.path(item['receipt'])
    doc = _json(path)
    corpus = {r['id']: r for r in info['corpus']}
    artifacts = [(item['receipt'], doc.get('findings', []))]
    candidates = []
    if item['format'] == 'de-parts':
        candidates = [{'path': str(Path('translation') / ev.locale / name), 'sha256': digest}
                      for name, digest in doc.get('evidenceHashes', {}).items()
                      if any(word in Path(name).name for word in ('findings', 'consolidated-proposals')) and name.endswith('.json')]
    elif item['format'] == 'es-catalogs':
        candidates = [{'path': str(path.parent.relative_to(ev.root) / name), 'sha256': digest}
                      for name, digest in doc.get('evidence', {}).items()
                      if any(word in name for word in ('decisions', 'proposal-batch', 'effect-questions')) and name.endswith('.json')]
    elif item['format'] == 'es419-semantic':
        manifest = path.parent / 'manifest.json'
        _require(manifest.is_file(), 'Legacy es-419 needs its hashed finding manifest')
        manifest_ref = _ref(ev.root, manifest.relative_to(ev.root), ev.locale)
        ev.nested(manifest_ref)
        files = _json(manifest)['files']
        if isinstance(files, dict):
            files = [{'path': name, 'sha256': digest} for name, digest in files.items()]
        _require(item['receipt'] in files, 'Legacy finding manifest does not bind the actual semantic receipt')
        candidates = [ref for ref in files if any(word in Path(ref['path']).name for word in ('findings', 'orthography-class', 'metadata-correction'))]
    for ref in candidates:
        artifacts.append((ref, _json(ev.nested(ref))))
    obligations = {}

    parsed = [0]
    def visit(value, ref, inherited_reason=None):
        if isinstance(value, list):
            for child in value:
                visit(child, ref, inherited_reason)
        elif isinstance(value, dict):
            reason = value.get('reason', value.get('finding', inherited_reason))
            id_ = value.get('id')
            if id_ in corpus and (reason or any(k in value for k in ('proposedTarget', 'proposedCorrection', 'expectedTarget'))):
                if value.get('source') is not None:
                    _require(value['source'] == corpus[id_]['source'], 'Legacy finding source mismatch: ' + id_)
                original = dict(value)
                if inherited_reason and not value.get('reason'):
                    original['reason'] = inherited_reason
                parsed[0] += 1
                stable = {'id': id_, 'source': corpus[id_]['source'],
                          'before': value.get('reviewedTarget', value.get('currentTarget', value.get('expectedTarget'))),
                          'after': value.get('proposedTarget', value.get('proposedCorrection', value.get('target')))}
                key = 'legacy:' + _sha(_bytes(stable))
                obligations[key] = {'id': id_, 'finding': original, 'artifact': ref}
                return
            for child in value.values():
                if isinstance(child, (list, dict)):
                    visit(child, ref, reason)
    for ref, data in artifacts:
        before = parsed[0]
        visit(data, ref)
        # An unparsed native finding class is an explicit reconciliation item, not zero findings.
        if parsed[0] == before and data and ref != item['receipt'] and any(
                word in Path(ref['path']).name for word in ('findings', 'proposals', 'proposal-batch', 'effect-questions', 'orthography', 'metadata-correction')):
            key = 'legacy-artifact:' + ref['sha256']
            obligations[key] = {'id': None, 'finding': data, 'artifact': ref}
    return obligations


def _canonical_ids(ids, corpus, label):
    _require(isinstance(ids, list) and len(ids) == len(set(ids)) and set(ids) <= corpus.keys(), label + ' has unknown/duplicate IDs')
    selected = set(ids)
    _require(ids == [id_ for id_ in corpus if id_ in selected], label + ' must be in canonical order')
    return selected


def _closure(ev, ref, info, old_semantic, output=None, historical=False):
    doc = ev.read(ref)
    corpus = {r['id']: r for r in info['corpus']}
    _require(doc.get('schemaVersion') == 2 and doc.get('inputBindings') == (output or _bindings(info)), 'Stale closure input bindings')
    ids = _canonical_ids(doc['ids'], corpus, 'Closure')
    if doc.get('previous'):
        previous_doc = ev.read(doc['previous'])
        previous_ids = _canonical_ids(previous_doc['ids'], corpus, 'Previous closure')
        removed = previous_ids - ids
        _require(_canonical_ids(doc.get('retiredIds', []), corpus, 'Retired IDs') == removed, 'Retired dependency IDs must match exact previous-minus-current set')
        reasons = doc.get('retirementReasons', [])
        _require(len(reasons) == len(removed) and {r.get('id') for r in reasons} == removed, 'Retired dependencies need actual justifications')
        for reason in reasons:
            _require(_text(reason.get('reason')) and _contains_exact(ev.read(reason['evidence']), {k: v for k, v in reason.items() if k != 'evidence'}),
                     'Retired dependency lacks verified selector justification')
    changed = _canonical_ids(doc['changedIds'], corpus, 'Changed IDs')
    invalidated = _canonical_ids(doc['invalidatedIds'], corpus, 'Invalidated IDs')
    _require(changed | invalidated <= ids, 'Changed/invalidated rows absent from closure')
    baseline_changes = {id_ for id_, read in old_semantic.items() if id_ in corpus and read['pairSha256'] != _pair(corpus[id_])}
    if not historical:
        _require(baseline_changes <= changed, 'Changed baseline pairs absent from closure changedIds')
    components = doc.get('components', {})
    _require(set(components) == set(COMPONENTS), 'Incomplete dependency components')
    union = set()
    for name, rows in components.items():
        union |= _canonical_ids(rows, corpus, 'Component ' + name)
    _require(union == ids, 'Closure differs from dependency components')
    recipe = ev.read(doc['recipe'])
    _require(recipe.get('schemaVersion') == 2 and recipe.get('inventorySha256') == info['inventorySha256'], 'Dependency recipe input mismatch')
    seeds = _canonical_ids(recipe['seedIds'], corpus, 'Recipe seeds')
    _require(seeds == changed | invalidated, 'Recipe seeds must equal changed/invalidated IDs')
    rows = _rows(ev.read(doc['rows']))
    _require(set(rows) == ids and all(row['source'] == corpus[id_]['source'] and (historical or row == corpus[id_]) for id_, row in rows.items()), 'Changed or unread closure rows')
    catalog = ev.read(doc['regressionCatalog'])
    _require(isinstance(catalog, list) and catalog, 'Mandatory regression catalog missing')
    catalog_ids, regression_ids = set(), set()
    for surface in catalog:
        _require(_text(surface.get('id')) and surface['id'] not in catalog_ids and _text(surface.get('reason')), 'Invalid regression surface')
        catalog_ids.add(surface['id'])
        regression_ids |= _canonical_ids(surface['unitIds'], corpus, 'Regression surface IDs')
    _require(set(MANDATORY_SURFACES) <= catalog_ids, 'Mandatory regression surfaces missing')
    registry_ref = doc['specialSceneRegistry']
    _require(registry_ref['path'] == 'source/special-scenes-8879120.json', 'Wrong special-scene registry')
    registry = ev.read(registry_ref)
    for case in registry['cases']:
        _require(case['id'] in catalog_ids, 'Mandatory special-scene case omitted: ' + case['id'])
        surface = next(s for s in catalog if s['id'] == case['id'])
        _require(set(case['unitIds']) & corpus.keys() <= set(surface['unitIds']), 'Special-scene regression IDs missing')
    _require(regression_ids <= set(components['regressions']), 'Regression catalog IDs absent from closure')
    generated = {name: set() for name in COMPONENTS}
    generated['context'] |= seeds
    generated['regressions'] |= regression_ids
    reachable = seeds | regression_ids
    edges = recipe.get('dependencies', [])
    for edge in edges:
        _require(edge.get('component') in COMPONENTS and _text(edge.get('reason')), 'Dependency edge lacks component/reason')
        _require(edge.get('from') in corpus, 'Unknown dependency edge seed')
        _canonical_ids(edge['to'], corpus, 'Dependency edge targets')
        _require(ev.path(edge['evidence']).stat().st_size > 0, 'Dependency lacks actual topology/concept evidence')
    for _ in range(len(edges) + 1):
        before_reachable = set(reachable)
        for edge in edges:
            if edge['from'] in reachable:
                generated[edge['component']].update(edge['to'])
                reachable.update(edge['to'])
        if reachable == before_reachable:
            break
    _require(all(edge['from'] in reachable for edge in edges), 'Dependency recipe has unreachable/unbound edges')
    _require(reachable == ids and all(generated[name] == set(components[name]) for name in COMPONENTS),
             'Normal dependency recipe does not reproduce exact closure/components')
    technical = ev.read(doc['technicalContext'])
    _require(isinstance(technical, list), 'Technical context must remain separate')
    retained = {r['id']: r['source'] for r in _json(_safe(ev.root, 'source/multilingual/shared-8879120-03/technical-retentions.json'))}
    for row in technical:
        _require(row.get('id') in retained and row.get('source') == retained[row['id']], 'Invalid separate technical context')
    return {'ref': ref, 'doc': doc, 'rows': rows, 'ids': ids, 'changed': changed,
            'invalidated': invalidated, 'regressionIds': regression_ids, 'catalogIds': catalog_ids, 'catalog': catalog}


def _glossary(ev, ref, info):
    doc = ev.read(ref)
    snapshot = _json(_safe(ev.root, f'translation/{ev.locale}/glossary-snapshot.json', ev.locale))
    _require(doc.get('schemaVersion') == 2 and doc.get('snapshotSha256') == info['glossarySha256'], 'Stale glossary compatibility')
    current_path = ev.path(doc['currentSource'])
    source = _json(current_path)
    source = source if isinstance(source, list) else source['entries']
    fields = lambda rows: [{k: r[k] for k in ('id', 'term', 'meaning')} for r in rows]
    _require(fields(source) == fields(snapshot['source']) and _digest(current_path) == snapshot['sourceRawSha256'], 'Current compact English source/snapshot mismatch')
    # Verify the actual current canonical source, read-only, at its declared canonical path.
    master = MASTER_SOURCE
    _require(snapshot.get('sourcePath') == str(master) and master.is_file() and not master.is_symlink()
             and _digest(master) == snapshot['sourceRawSha256'], 'Current canonical glossary source differs; compatibility reconciliation required')
    canonical_targets = _json(master.with_name('glossary-translations.json'))
    _require(canonical_targets.get(ev.locale) == snapshot['target'], 'Current canonical glossary target differs; local compatibility reconciliation required')
    owner_path = ev.path(doc['ownerAcceptance'])
    _require(owner_path == _safe(ev.root, f'glossary/{ev.locale}/acceptance.json', ev.locale), 'Wrong glossary owner acceptance path')
    owner = _json(owner_path)
    _require(owner.get('accepted') is True and owner.get('locale') == ev.locale, 'Glossary owner readiness absent')
    ids = [r['id'] for r in source]
    _require(len(ids) == len(set(ids)) and set(ids) == set(snapshot['target']), 'Glossary ID alignment mismatch')
    expected = [{'id': r['id'], 'source': {k: r[k] for k in ('term', 'meaning')},
                 'target': snapshot['target'][r['id']]} for r in source]
    layers = doc.get('layers', [])
    _require(len(layers) == 2 and layers[0] != layers[1], 'Two distinct actual glossary review layers required')
    content_hashes = []
    for layer in layers:
        layer_doc = ev.read(layer)
        _require(layer_doc.get('dimensions') == ['fidelity', 'native-language'] and _text(layer_doc.get('reviewer')),
                 'Glossary layer lacks fidelity/native-language actual reading')
        _require(layer_doc.get('rows') == expected and layer_doc.get('actualReadIds') == ids, 'Glossary layer current-source/target read coverage mismatch')
        decisions = layer_doc.get('decisions', [])
        _require([d.get('id') for d in decisions] == ids and all(d.get('decision') == 'clean' and _text(d.get('reason')) for d in decisions),
                 'Glossary layer lacks current per-ID clean decisions')
        content_hashes.append(_sha(_bytes(layer_doc)))
    _require(content_hashes[0] != content_hashes[1], 'Copied glossary layer evidence')
    return ref['sha256']


def _images(ev, ref):
    doc = ev.read(ref)
    _require(doc['sourceManifest']['path'] == MEDIA_MANIFEST and doc['sourceManifest']['sha256'] == MEDIA_SHA256,
             'Image-text classification must bind the complete pinned media inventory')
    media = ev.read(doc['sourceManifest'])['assets']
    inventory = ev.read(doc['inventory'])
    plans = ev.read(doc['plans'])
    _require(isinstance(inventory, list) and isinstance(plans, list), 'Image inventory/plans must be explicit arrays')
    _require([r.get('asset') for r in inventory] == [r['asset'] for r in media], 'Image classification omits/duplicates shared media assets')
    text_assets = []
    for original, classified in zip(media, inventory):
        _require(classified.get('sourceSha256') == original['rawSha256'] and _text(classified.get('reason'))
                 and classified.get('classification') in {'text-bearing', 'no-text'}, 'Unreviewed image-text classification')
        _require(_contains_exact(ev.read(classified['evidence']), {k: v for k, v in classified.items() if k != 'evidence'}),
                 'Image classification absent from actual visual/source evidence')
        if classified['classification'] == 'text-bearing':
            text_assets.append(classified)
    _require([r.get('asset') for r in plans] == [r['asset'] for r in text_assets], 'Image-text plan coverage differs')
    for source, plan in zip(text_assets, plans):
        _require(plan.get('sourceSha256') == source['sourceSha256'] and _text(plan.get('targetSha256'))
                 and plan.get('decision') == 'clean', 'Unaccepted image-text plan: ' + source['asset'])
        _require(plan.get('disposition') in {'localized-resource', 'intentional-retention'} and _text(plan.get('reason')),
                 'Image-text plan lacks actual resource/retention disposition')
        artifact = ev.path(plan['artifact'])
        _require(_digest(artifact) == plan['targetSha256'], 'Image target resource hash differs')
        if plan['disposition'] == 'intentional-retention':
            _require(plan['targetSha256'] == source['sourceSha256'], 'Intentional image retention changed original bytes')
        _require(_contains_exact(ev.read(plan['evidence']), {k: v for k, v in plan.items() if k != 'evidence'}),
                 'Image plan absent from actual paired source/target review evidence')
    normalized = [{'asset': r['asset'], 'classification': r['classification'], 'sourceSha256': r['sourceSha256']} for r in inventory]
    targets = [{'asset': r['asset'], 'sourceSha256': r['sourceSha256'], 'targetSha256': r['targetSha256']} for r in plans]
    return {'token': _sha(_bytes({'media': MEDIA_SHA256, 'inventory': normalized, 'plans': targets})),
            'localized': [{'asset': p['asset'], 'targetSha256': p['targetSha256']} for p in plans if p['disposition'] == 'localized-resource']}


def _native_verification(ev, role, work, info):
    """Replay the shared adapter's documented static verify entry, never a build."""
    receipt_path = ev.path(work['verification'])
    receipt = _json(receipt_path)
    manifest_path = ev.path(work['buildManifest'])
    _require(manifest_path.name == 'manifest.json' and manifest_path.is_relative_to(ev.root / 'build/multilingual-delivery'),
             'Native build manifest must be in build/multilingual-delivery')
    manifest = _json(manifest_path)
    _require(manifest.get('siteLocale') == ev.locale, 'Native build locale mismatch')
    archive_path = ev.path(work['archive']) if role == 'package' else None
    adapter = _safe(ev.root, 'tools/multilingual/delivery/native_delivery.py')
    _require(adapter.is_file(), 'Native adapter unavailable: tools/multilingual/delivery/native_delivery.py verify')
    args = [sys.executable, '-B', str(adapter), '--root', str(ev.root), '--locale', ev.locale,
            'verify', '--build', str(manifest_path.parent)]
    if archive_path:
        _require(archive_path.is_relative_to(ev.root / 'build/multilingual-delivery'), 'Archive outside native delivery scope')
        args += ['--archive', str(archive_path)]
        _require(receipt.get('archiveSha256') == _digest(archive_path)
                 and receipt.get('buildManifestSha256') == _digest(manifest_path), 'Stale native package receipt')
    reuse = _owner_checkpoint_reuse(ev.root, ev.locale)
    if reuse:
        from native_checkpoint import verify_checkpoint
        actual = verify_checkpoint(ev.root, ev.locale, manifest_path.parent,
                                   archive_path, receipt_path if archive_path else None)
        actual['checkpointDecision'] = reuse
    else:
        run = subprocess.run(args, capture_output=True, text=True, timeout=900)
        _require(run.returncode == 0, 'Native adapter verification failed: ' + run.stderr.strip()[-1500:])
        actual = json.loads(run.stdout)
    _require((reuse or actual.get('status') == 'passed-native-decrypted-readback') and actual.get('siteLocale') == ev.locale
             and actual.get('authoredEntries') == info['authoredVisible'] and actual.get('files', 0) > 0,
             'Native helper did not verify full source-bound native payload')
    if role == 'package':
        for key in ('status', 'siteLocale', 'files', 'mappedTargets', 'authoredEntries', 'archive'):
            _require(receipt.get(key) == actual.get(key), 'Package helper receipt/result mismatch: ' + key)
        _require(actual.get('archive') == str(archive_path), 'Native archive not verified')
    else:
        _require(receipt.get('siteLocale') == ev.locale and receipt.get('status') == 'passed-technical-candidate'
                 and receipt.get('manifestSha256') == _digest(manifest_path), 'Native build acceptance receipt mismatch')
    actual['nativeFiles'] = manifest['files']
    return _sha(_bytes({'bindings': _bindings(info), 'nativeFiles': manifest['files'],
                        'archive': _digest(archive_path) if archive_path else None})), actual


def _owner_checkpoint_reuse(root, locale):
    current = Path(root) / 'runtime/cli-localization/current.json'
    if not current.is_file():return None
    run = Path(_json(current)['run']).resolve()
    _require(run.is_relative_to(Path(root).resolve() / 'runtime/cli-localization/runs'), 'Queue pointer escapes project')
    ref = _json(run / 'config.json').get('nativeCheckpointDecision')
    if not ref:return None
    path = (Path(root) / ref['path']).resolve()
    _require(path.is_relative_to(run) and _digest(path) == ref['sha256'], 'Owner native-checkpoint decision changed')
    decision = _json(path)
    _require(decision.get('authority') == 'owner' and decision.get('reuseVerifiedNativeCheckpoints') is True
             and decision.get('instruction') and locale in decision.get('locales', []), 'Invalid owner native-checkpoint decision')
    return ref


def _empty_state():
    return {'semantic': {}, 'preparatory': {}, 'independent': {}, 'findings': {}, 'resolved': {},
            'handoffs': {}, 'reviewCycles': {}, 'authorSessions': set(), 'tokens': set(),
            'glossary': None, 'images': None, 'resources': None, 'package': None,
            'findingCycles': 0, 'remedialUsed': False, 'automaticReviewBlocked': False, 'legacyFindings': {}, 'legacyResolved': {}, 'recordErrors': []}


def _contains_exact(document, item):
    if document == item:
        return True
    if isinstance(document, list):
        return any(_contains_exact(value, item) for value in document)
    if isinstance(document, dict):
        return any(_contains_exact(value, item) for value in document.values())
    return False


def _common(root, locale, role, receipt_path, task, session_id, info, historical=False, queue_row=None):
    _require(role in ROLES and task.get('role') == role, 'Unknown/mismatched role; generic stage names cannot grant acceptance')
    _require(isinstance(task.get('sequence'), int) and not isinstance(task.get('sequence'), bool) and task['sequence'] >= 0,
             'Task requires a nonnegative sequence for deterministic pipeline replay')
    _require(_text(task.get('id')) and re.fullmatch(r'[A-Za-z0-9_-]+', task['id']), 'Unsafe/missing task ID')
    path = Path(receipt_path)
    if path.is_absolute():
        _require(path.is_relative_to(root), 'Receipt outside root')
        path = path.relative_to(root)
    expected = Path('translation') / locale / 'pipeline/tasks' / task['id'] / 'receipt.json'
    _require(path == expected, 'Receipt must be the immutable per-task receipt.json')
    file = _safe(root, path, locale)
    persisted_task = _json(_safe(root, str(path.parent / 'task.json'), locale))
    _require(persisted_task == task, 'Persisted task differs from dispatched task; preserve immutable task inputs')
    receipt = _json(file)
    _require(receipt.get('schemaVersion') == 2 and receipt.get('taskId') == task['id']
             and receipt.get('locale') == locale and receipt.get('role') == role, 'Receipt schema/task/locale/role mismatch')
    _require(_text(session_id) and task.get('sessionId', session_id) == session_id
             and receipt.get('sessionId') == session_id, 'Receipt must identify the actual CLI session')
    _require(receipt.get('disposition') in {'continue', 'stage-complete', 'blocked'}, 'Unknown disposition')
    _require(_text(receipt.get('summary')) and isinstance(receipt.get('blockers'), list)
             and all(_text(b) for b in receipt['blockers']), 'Missing summary or invalid blockers')
    _require(receipt.get('inputBindings') == task.get('inputBindings') and set(receipt['inputBindings']) == set(BINDINGS), 'Task input bindings mismatch')
    before = task['inputBindings']
    for key in ('inventorySha256', 'glossarySha256'):
        _require(before[key] == info[key], 'Stale input binding: ' + key)
    output = receipt.get('outputBindings', before)
    _require(set(output) == set(BINDINGS), 'Incomplete output bindings')
    if not historical:
        _require(output == _bindings(info), 'Stale output bindings; inspect actual current corpus')
    _require(output['inventorySha256'] == before['inventorySha256'] and output['glossarySha256'] == before['glossarySha256'], 'Task changed protected input binding')
    if role not in {'author', 'editor'}:
        _require(before == output, 'Reviewer/resources/package cannot edit authored text')
    unused_operational, snapshots = (), {}
    if historical and role == 'author' and _accepted_authored_replay(root, locale, _ref(root, path, locale), task, session_id, queue_row):
        # Mutable status summaries are not translation evidence. Required work refs
        # still call Evidence.path and must match their exact original hashes.
        unused_operational = tuple(f'translation/{locale}/{name}' for name in ('CHECKPOINT.md', 'CHECKPOINT.json', 'UNRESOLVED.md'))
        for record in queue_row.get('attempts', []) if queue_row is not None else _queue_locale_state(root, locale).get('attempts', []):
            if record.get('taskId') != task['id']:continue
            for item in record.get('historicalEvidenceSnapshots', []):
                original, snapshot = item['original'], item['snapshot']
                _require(original in receipt['evidence'] and original in record['validation']['savedEvidence'],
                         'Historical snapshot lacks original accepted evidence pin')
                _require(snapshot['sha256'] == original['sha256'], 'Historical snapshot must preserve original bytes')
                prefix = expected.parent / 'evidence-snapshots'
                _require(Path(snapshot['path']).is_relative_to(prefix), 'Historical snapshot outside original task')
                _require(original['path'] not in snapshots, 'Duplicate historical snapshot')
                snapshots[original['path']] = snapshot
    ev = Evidence(root, locale, receipt.get('evidence'), unused_operational, snapshots)
    ev.saved[str(path.parent / 'task.json')] = _ref(root, str(path.parent / 'task.json'), locale)
    return receipt, ev, _ref(root, path, locale), output


def _evaluate(root, locale, role, receipt_path, task, session_id, info, state, historical=False, queue_row=None):
    receipt, ev, saved_ref, output = _common(root, locale, role, receipt_path, task, session_id, info, historical, queue_row)
    work = receipt.get('work')
    _require(isinstance(work, dict), 'Role-specific work must be an object')
    allowed = {
        'author': {'authoredIds'},
        'editor': {'authoredIds', 'reads', 'importReads', 'legacyReads', 'legacyDispositions', 'findings', 'resolutions', 'closure', 'glossaryCompatibility', 'imageText'},
        'reviewer': {'handoff', 'reads', 'findings', 'regressions', 'remedialReview'},
        'resources': {'verification', 'buildManifest'},
        'package': {'verification', 'buildManifest', 'archive'},
    }
    _require(set(work) <= allowed[role], 'Unknown role work fields/stages: ' + str(sorted(set(work) - allowed[role])))
    corpus = {r['id']: r for r in info['corpus']}
    prior_tokens = set(state['tokens'])
    previous = task.get('previousProgress', task.get('previous', {}))
    _require(isinstance(previous, dict), 'previousProgress must be a snapshot')
    if previous:
        _require(previous.get('locale') == locale and previous.get('inventorySha256') == task['inputBindings']['inventorySha256']
                 and previous.get('glossarySha256') == task['inputBindings']['glossarySha256']
                 and previous.get('corpusSha256') == task['inputBindings']['corpusSha256'], 'Previous progress/task input mismatch')
    authored_ids = work.get('authoredIds', [])
    _require(isinstance(authored_ids, list) and len(authored_ids) == len(set(authored_ids))
             and set(authored_ids) <= corpus.keys(), 'Unknown/duplicate authored IDs')
    authored_progress = False
    if authored_ids and not historical:
        _require(role in {'author', 'editor'}, 'Role cannot author text')
        _require(previous and 'authoredPairHashes' in previous, 'Authored repairs require before progress snapshot')
        old_pairs = set(previous['authoredPairHashes'])
        _require(all(_pair(corpus[id_]) not in old_pairs for id_ in authored_ids), 'Authored IDs have no actual new/changed visible text')
        _require(not info['errors'], 'Authored changes fail structural validation: ' + '; '.join(info['errors']))
        authored_progress = True
    elif authored_ids and historical:
        # Replay preserves the original observed outcome. Current text can include
        # later edits; it cannot reconstruct whether this old call made progress.
        authored_progress = _accepted_authored_replay(root, locale, saved_ref, task, session_id, queue_row)
    if role in {'author', 'editor'}:
        state['authorSessions'].add(session_id)
    known_finding_ids = {f['id'] for f in state['findings'].values()}
    old_semantic = dict(state['semantic'])
    reads, finding_ids = {}, set()
    for bundle in work.get('reads', []):
        if role == 'reviewer':
            _require(bundle.get('kind') == 'closure' and bundle.get('sessionId') == session_id, 'Reviewer must perform own identifiable closure read')
        elif bundle.get('kind') != 'preparatory':
            _require(bundle.get('sessionId') == session_id, 'New semantic reads must identify the current actual session')
        imported = _read_bundle(ev, bundle, corpus)
        _require(not (set(reads) & set(imported)), 'Duplicate read IDs within task')
        reads.update(imported)
    for item in work.get('importReads', []):
        origin_path = ev.path(item['receipt'])
        origin = _json(origin_path)
        original_task_ref = _ref(root, origin_path.parent.relative_to(root) / 'task.json', locale)
        origin_task = _json(ev.nested(original_task_ref))
        _require(origin.get('schemaVersion') == 2 and origin.get('locale') == locale and origin.get('role') == 'editor'
                 and origin.get('sessionId') == origin_task.get('sessionId') and origin.get('taskId') == origin_task.get('id')
                 and origin_task.get('role') == 'editor' and origin.get('inputBindings') == origin_task.get('inputBindings'), 'Invalid original editor/session identity for read reuse')
        _require(all(origin.get('inputBindings', {}).get(k) == info[k] for k in ('inventorySha256', 'glossarySha256')),
                 'Imported read has stale source/glossary bindings')
        for original_ref in origin.get('evidence', []):
            ev.nested(original_ref)
        bundles = origin.get('work', {}).get('reads', [])
        selected = item.get('bundleIndices')
        _require(isinstance(selected, list) and selected and len(selected) == len(set(selected))
                 and all(isinstance(i, int) and 0 <= i < len(bundles) for i in selected), 'Invalid original read bundle selection')
        for index in selected:
            bundle = bundles[index]
            _require(bundle.get('sessionId') == origin['sessionId'], 'Original actual read identity mismatch')
            imported = _read_bundle(ev, bundle, corpus)
            for id_, read in imported.items():
                if id_ not in reads or read['pairSha256'] == _pair(corpus[id_]) or reads[id_]['pairSha256'] != _pair(corpus[id_]):
                    reads[id_] = read
        for finding in origin.get('work', {}).get('findings', []):
            _require(finding.get('id') in corpus, 'Imported finding outside corpus')
            key = 'imported:' + _sha(_bytes({k: v for k, v in finding.items() if k != 'evidence'}))
            state['legacyFindings'][key] = {'id': finding['id'], 'finding': finding, 'artifact': item['receipt']}
    for item in work.get('legacyReads', []):
        imported = _legacy_read(ev, item, info)
        for id_, read in imported.items():
            if id_ not in reads or read['pairSha256'] == _pair(corpus[id_]) or reads[id_]['pairSha256'] != _pair(corpus[id_]):
                reads[id_] = read
        state['legacyFindings'].update(_legacy_obligations(ev, item, info))
    for disposition in work.get('legacyDispositions', []):
        key = disposition.get('key')
        _require(key in state['legacyFindings'] and disposition.get('disposition') in {'corrected', 'rejected', 'external-blocker'}
                 and _text(disposition.get('reason')), 'Missing actual finite legacy finding disposition')
        payload = {k: v for k, v in disposition.items() if k != 'evidence'}
        _require(_contains_exact(ev.read(disposition['evidence']), payload), 'Legacy disposition absent from actual adjudication evidence')
        native = state['legacyFindings'][key]
        if disposition['disposition'] == 'corrected' and not historical:
            id_ = native['id']
            _require(id_ in corpus and disposition.get('targetSha256') == _sha(corpus[id_]['target'].encode()),
                     'Legacy correction lacks exact current target hash')
            before = native['finding'].get('reviewedTarget', native['finding'].get('currentTarget', native['finding'].get('expectedTarget')))
            _require((isinstance(before, str) and before != corpus[id_]['target']) or
                     (_text(native['finding'].get('targetSha256')) and native['finding']['targetSha256'] != disposition['targetSha256']),
                     'Legacy correction did not repair the actual reviewed target')
        state['legacyResolved'][key] = disposition
        if disposition['disposition'] != 'external-blocker':
            state['tokens'].add('resolved:' + key + ':' + disposition['disposition'])
    for id_, read in reads.items():
        if role != 'reviewer':
            category = 'preparatory' if read['kind'] == 'preparatory' else 'semantic'
            existing = state[category].get(id_)
            if existing is None or read['pairSha256'] == _pair(corpus[id_]) or existing['pairSha256'] != _pair(corpus[id_]):
                state[category][id_] = read
            state['tokens'].add(category + ':' + read['pairSha256'])
    for finding in work.get('findings', []):
        id_ = finding.get('id')
        _require(_text(finding.get('key')) and id_ in corpus and _text(finding.get('reason'))
                 and _text(finding.get('proposal')), 'Incomplete objective finding/proposal')
        _require(finding.get('sourceSha256') == _sha(corpus[id_]['source'].encode())
                 and (historical or finding.get('targetSha256') == _sha(corpus[id_]['target'].encode())), 'Stale finding pair hashes')
        payload = {k: v for k, v in finding.items() if k != 'evidence'}
        _require(_contains_exact(ev.read(finding['evidence']), payload), 'Finding absent from actual evidence artifact')
        key = finding['key']
        _require(key not in state['findings'] or state['findings'][key] == finding, 'Finding key reused with different proposal')
        state['findings'][key] = finding
        finding_ids.add(id_)
    for resolution in work.get('resolutions', []):
        key = resolution.get('key')
        _require(key in state['findings'] and resolution.get('disposition') in {'corrected', 'rejected', 'external-blocker'}
                 and _text(resolution.get('reason')), 'Unknown/unjustified finding resolution')
        payload = {k: v for k, v in resolution.items() if k != 'evidence'}
        _require(_contains_exact(ev.read(resolution['evidence']), payload), 'Resolution absent from adjudication artifact')
        if resolution['disposition'] == 'corrected' and not historical:
            id_ = state['findings'][key]['id']
            _require(resolution.get('targetSha256') == _sha(corpus[id_]['target'].encode())
                     and resolution['targetSha256'] != state['findings'][key]['targetSha256'], 'Correction did not change actual target')
        state['resolved'][key] = resolution
        if resolution['disposition'] != 'external-blocker':
            state['tokens'].add('resolved:' + key + ':' + resolution['disposition'])
    if work.get('glossaryCompatibility'):
        _glossary(ev, work['glossaryCompatibility'], info)
        state['glossary'] = info['glossarySha256']
        state['tokens'].add('glossary:' + info['glossarySha256'])
    if work.get('imageText'):
        state['images'] = _images(ev, work['imageText'])
        state['tokens'].add('imageText:' + state['images']['token'])
    if role == 'reviewer':
        _require({id_ for id_, r in reads.items() if r.get('decision') == 'finding'} == finding_ids,
                 'Independent finding decisions require exhaustive objective proposals')
    complete, next_role = False, role
    blockers = list(receipt['blockers'])
    open_findings = [key for key in state['findings'] if key not in state['resolved'] or state['resolved'][key]['disposition'] == 'external-blocker']
    current_output = output == _bindings(info)
    if role == 'author':
        complete = not info['errors'] and not info['missingIds'] and current_output
        next_role = 'editor' if complete else 'author'
    elif role == 'editor':
        closure = None
        if work.get('closure'):
            closure = _closure(ev, work['closure'], info, old_semantic, output, historical)
            _require(set(authored_ids) <= closure['changed'], 'Authored corrections omitted from changed IDs')
            previous_ref = closure['doc'].get('previous')
            previous_cycle = state['reviewCycles'].get(previous_ref['sha256']) if previous_ref else None
            if previous_cycle:
                changed_since = {id_ for id_, row in previous_cycle['rows'].items() if id_ in corpus and row != corpus[id_]}
                _require(changed_since <= closure['ids'], 'Changed prior closure row was retired without review')
                rejected_or_invalidated = set(previous_cycle.get('findingIds', [])) - changed_since
                _require(rejected_or_invalidated <= closure['invalidated'], 'Prior independent findings require explicit evidence invalidation/recheck')
        required = []
        if not historical and (info['missingIds'] or info['errors']): required.append('complete structurally valid visible corpus')
        if set(state['semantic']) != set(corpus): required.append('one complete actual semantic source-to-target read (retaining valid baseline rows)')
        if open_findings: required.append('consolidated finding dispositions: ' + ', '.join(open_findings))
        open_legacy = [key for key in state['legacyFindings'] if key not in state['legacyResolved'] or state['legacyResolved'][key]['disposition'] == 'external-blocker']
        if open_legacy: required.append('finite historical finding dispositions: ' + str(len(open_legacy)) + ' remaining')
        if state['glossary'] != info['glossarySha256']: required.append('current-source glossary compatibility and two applicable layers')
        if closure is None: required.append('reproducible finite dependency closure and mandatory regressions')
        if closure:
            for key, resolution in state['legacyResolved'].items():
                if resolution['disposition'] == 'corrected':
                    _require(state['legacyFindings'][key]['id'] in closure['changed'], 'Corrected legacy finding omitted from closure')
            for key, resolution in state['resolved'].items():
                if resolution['disposition'] == 'corrected':
                    _require(state['findings'][key]['id'] in closure['changed'], 'Corrected finding omitted from closure')
        complete = not required and (current_output or historical)
        blockers.extend(required)
        if complete:
            state['handoffs'][saved_ref['sha256']] = {'ref': saved_ref, 'closure': closure, 'sessionId': session_id,
                                                     'outputBindings': output}
            next_role = 'reviewer'
    elif role == 'reviewer':
        handoff_ref = work.get('handoff')
        ev.path(handoff_ref)
        handoff = state['handoffs'].get(handoff_ref['sha256'])
        _require(handoff is not None and handoff['ref'] == handoff_ref, 'No validated editor handoff for independent review')
        _require(session_id != handoff['sessionId'] and session_id not in state['authorSessions']
                 and all(session_id != r['sessionId'] for r in state['semantic'].values()), 'Same-session/self review is not independent')
        closure = handoff['closure']
        _require(handoff['outputBindings'] == output and (historical or output == _bindings(info)), 'Reviewer handoff changed/stale')
        previous_ref = closure['doc'].get('previous')
        previous_cycle = None
        if previous_ref:
            ev.path(previous_ref)
            previous_cycle = state['reviewCycles'].get(previous_ref['sha256'])
        if previous_cycle:
            previous_rows = previous_cycle['rows']
            changed = {id_ for id_ in closure['ids'] if id_ in previous_rows and previous_rows[id_] != closure['rows'][id_]}
            required_ids = changed | (closure['ids'] - set(previous_rows)) | closure['invalidated'] | closure['regressionIds']
        else:
            required_ids = closure['ids']
        _require(set(reads) == required_ids, 'Independent read set must equal exact closure/delta plus mandatory regressions')
        _require(all(reads[id_]['pairSha256'] == _pair(closure['rows'][id_]) for id_ in reads), 'Changed/unread independent closure pairs')
        regression = ev.read(work['regressions'])
        _require(regression.get('closureSha256') == closure['ref']['sha256'] and regression.get('sessionId') == session_id, 'Stale/self-claimed regression receipt')
        results = regression.get('results', [])
        _require(len(results) == len(closure['catalogIds']) and {r.get('id') for r in results} == closure['catalogIds'], 'Mandatory regression coverage incomplete')
        for result in results:
            _require(result.get('decision') in {'clean', 'finding'} and _text(result.get('reason')), 'Mandatory regression lacks actual decision')
            if result['decision'] == 'finding':
                surface = next(s for s in closure['catalog'] if s['id'] == result['id'])
                _require(set(surface['unitIds']) & finding_ids, 'Regression finding lacks objective proposal')
            _require(_contains_exact(ev.read(result['evidence']), {k: v for k, v in result.items() if k != 'evidence'}),
                     'Regression result absent from actual result artifact')
        if state['findingCycles'] >= 2 and not state['remedialUsed']:
            _require(work.get('remedialReview') is True, 'Repeated unrelated findings require one consolidated remedial review')
            state['remedialUsed'] = True
        elif state['remedialUsed'] and finding_ids - known_finding_ids:
            state['automaticReviewBlocked'] = True
            blockers.append('Further unrelated findings after consolidated remedial review: stop automatic cycles; bounded root-cause repair required')
        for id_, read in reads.items():
            state['tokens'].add('independent:' + read['pairSha256'])
            if id_ not in finding_ids:
                state['independent'][id_] = read
        state['reviewCycles'][closure['ref']['sha256']] = {'rows': closure['rows'], 'sessionId': session_id,
                                                         'clean': not finding_ids, 'findingIds': sorted(finding_ids), 'ref': closure['ref']}
        if finding_ids:
            state['findingCycles'] += 1
        complete = True
        next_role = None if state['automaticReviewBlocked'] else ('editor' if finding_ids else 'resources')
    elif role in {'resources', 'package'}:
        if (not historical or current_output) and receipt['disposition'] != 'blocked':
            token, actual = _native_verification(ev, role, work, info)
            state[role] = {'bindings': output, 'token': token, 'actual': actual}
            state['tokens'].add(role + ':' + token)
            complete = True
            next_role = 'package' if role == 'resources' else 'delivery'
    if receipt['disposition'] == 'stage-complete':
        _require(complete and not receipt['blockers'], 'Incomplete role-complete claim: ' + '; '.join(blockers))
    # Handoffs and clean reviews count once; closure/report byte changes do not.
    if complete and role in {'editor', 'reviewer'}:
        state['tokens'].add('stage:' + role + ':' + output['corpusSha256'])
    meaningful = authored_progress or bool(state['tokens'] - prior_tokens)
    _require(receipt['disposition'] != 'continue' or meaningful, 'Report-only continue: no actual authored/read/resolved/verified progress')
    if receipt['disposition'] == 'blocked':
        _require(receipt['blockers'], 'Blocked disposition requires concrete blockers')
        complete = False
        next_role = role
    return {'roleComplete': complete, 'meaningfulProgress': meaningful, 'nextRole': next_role,
            'blockers': list(dict.fromkeys(blockers)), 'savedEvidence': [saved_ref, *ev.saved.values()]}


def _queue_locale_state(root, locale):
    current = root / 'runtime/cli-localization/current.json'
    if not current.is_file():return {}
    run = Path(_json(current)['run']).resolve()
    _require(run.is_relative_to(root / 'runtime/cli-localization/runs'), 'Queue pointer escapes project')
    path = run / 'state.json'
    return _json(path).get('locales', {}).get(locale, {}) if path.is_file() else {}


def _accepted_authored_replay(root, locale, receipt_ref, task, session_id, queue_row=None):
    """Reuse only a real queue validation bound to the unchanged task and receipt."""
    queue_row = _queue_locale_state(root, locale) if queue_row is None else queue_row
    task_ref = _ref(root, str(Path(receipt_ref['path']).parent / 'task.json'), locale)
    for record in queue_row.get('attempts', []):
        if record.get('taskId') != task['id']:continue
        validation = record.get('validation', {})
        usage = record.get('usage', {})
        return bool(record.get('pipelineRevision') == 2
            and record.get('role') in {'author', 'editor'}
            and record.get('status') in {'continue', 'stage-complete'}
            and usage.get('session') == session_id and usage.get('tokens')
            and validation.get('meaningfulProgress') is True
            and receipt_ref in validation.get('savedEvidence', [])
            and task_ref in validation.get('savedEvidence', []))
    return False


def _record_state(root, locale, info, exclude=None):
    import copy
    state = _empty_state()
    queue_row = _queue_locale_state(root, locale)
    directory = _safe(root, f'translation/{locale}/pipeline/tasks', locale)
    records = []
    for path in sorted(directory.glob('*/receipt.json')):
        if exclude is not None and path.absolute() == Path(exclude).absolute():
            continue
        try:
            relative = path.relative_to(root)
            _safe(root, relative, locale)
            task_path = _safe(root, str(relative.parent / 'task.json'), locale)
            task = _json(task_path)
            sequence = task.get('sequence')
            _require(isinstance(sequence, int) and not isinstance(sequence, bool) and sequence >= 0,
                     'Persisted task requires nonnegative sequence for deterministic replay')
            records.append((sequence, path, task))
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, OSError) as exc:
            state['recordErrors'].append(str(path.relative_to(root)) + ': ' + str(exc))
    seen = set()
    for sequence, path, task in sorted(records, key=lambda r: (r[0], str(r[1]))):
        candidate = copy.deepcopy(state)
        try:
            _require(sequence not in seen, 'Duplicate persisted task sequence')
            seen.add(sequence)
            _evaluate(root, locale, task['role'], path, task, task['sessionId'], info, candidate, historical=True, queue_row=queue_row)
            state = candidate
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, OSError, subprocess.SubprocessError) as exc:
            state['recordErrors'].append(str(path.relative_to(root)) + ': ' + str(exc))
    try:
        _machine_package_checkpoint(root, locale, info, state, queue_row)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        state['recordErrors'].append('machine package checkpoint: ' + str(exc))
    return state


def _machine_package_checkpoint(root, locale, info, state, queue_row=None):
    if not _owner_checkpoint_reuse(root, locale):return
    queue_row = _queue_locale_state(root, locale) if queue_row is None else queue_row
    package = queue_row.get('workflow', {}).get('machinePackageCheckpoint')
    if not package or package['bindings'] != _bindings(info):return
    for key in ('manifest', 'archive', 'verification'):
        ref = package[key];path = _safe(root, ref['path'], locale)
        _require(_digest(path) == ref['sha256'], 'Machine package artifact changed: ' + key)
    from native_checkpoint import verify_checkpoint
    actual = verify_checkpoint(root, locale, Path(package['manifest']['path']).parent,
                               package['archive']['path'], package['verification']['path'])
    manifest = _json(root / package['manifest']['path']);actual['nativeFiles'] = manifest['files']
    state['package'] = {'bindings': package['bindings'], 'token': package['archive']['sha256'], 'actual': actual}
    state['tokens'].add('package:' + package['archive']['sha256'])


def _legacy_candidates(root, locale):
    patterns = {
        'de': ('de-parts', 'editorial/semantic-01/parts/*.json'),
        'es': ('es-catalogs', 'audits/semantic-01/parts/*-receipt.json'),
        'es-419': ('es419-semantic', 'editorial/attempt-*/semantic-read.json'),
        'fr': ('fr-preparatory', 'editorial/preparatory-*/read-*.receipt.json'),
        'pt-BR': ('pt-paired', 'validation/*-paired-read-result.json'),
    }
    if locale not in patterns:
        return []
    fmt, pattern = patterns[locale]
    result = []
    for path in sorted((root / 'translation' / locale).glob(pattern)):
        ref = _ref(root, path.relative_to(root), locale)
        result.append({'format': fmt, 'receipt': ref, 'credit': 'not-imported; validate actual artifacts/decisions first'})
    return result


def _progress(info, state):
    corpus = {r['id']: r for r in info['corpus']}
    current = {id_: _pair(r) for id_, r in corpus.items()}
    valid_count = lambda values: sum(current.get(id_) == r['pairSha256'] for id_, r in values.items())
    open_keys = sorted(key for key in state['findings'] if key not in state['resolved'] or state['resolved'][key]['disposition'] == 'external-blocker')
    return {'schemaVersion': 2, 'locale': info['locale'], **_bindings(info),
            'authoredVisible': info['authoredVisible'], 'totalVisible': info['totalVisible'],
            'missingVisible': len(info['missingIds']), 'structuralErrors': info['errors'],
            # Digests only, no wording, file stats or reports; needed to verify actual repairs.
            'authoredPairHashes': sorted(current.values()),
            'semanticCovered': len(state['semantic']), 'semanticCurrent': valid_count(state['semantic']),
            'preparatoryCurrent': valid_count(state['preparatory']), 'independentCurrent': valid_count(state['independent']),
            'openFindingKeys': open_keys, 'resolvedFindings': len(state['resolved']),
            'openLegacyFindingKeys': sorted(key for key in state['legacyFindings'] if key not in state['legacyResolved'] or state['legacyResolved'][key]['disposition'] == 'external-blocker'),
            'legacyFindingArtifacts': {key: value['artifact'] for key, value in state['legacyFindings'].items()},
            'glossaryCompatible': state['glossary'] == info['glossarySha256'] and state['glossary'] is not None,
            'imageTextVerified': bool(state['images']),
            'resourcesVerified': bool(state['resources'] and state['resources']['bindings'] == _bindings(info)),
            'nativeArchiveVerified': bool(state['package'] and state['package']['bindings'] == _bindings(info)),
            'needsConsolidatedRemedial': state['findingCycles'] >= 2 and not state['remedialUsed'],
            'automaticReviewBlocked': state['automaticReviewBlocked'],
            'workTokens': sorted(state['tokens']), 'recordErrors': state['recordErrors']}


def progress_snapshot(root, locale) -> dict:
    root = Path(root).resolve()
    info = inspect_locale(root, locale)
    state = _record_state(root, locale, info)
    return _progress(info, state)


def validate_receipt(root, locale, role, receipt_path, task, session_id) -> dict:
    root = Path(root).resolve()
    info = inspect_locale(root, locale)
    path = Path(receipt_path)
    if not path.is_absolute():
        path = root / path
    state = _record_state(root, locale, info, exclude=path)
    try:
        result = _evaluate(root, locale, role, path, task, session_id, info, state)
        if info['errors']:
            result['blockers'] = list(dict.fromkeys([*result['blockers'], *info['errors']]))
            result['roleComplete'] = False
        result['progress'] = _progress(info, state)
        # Compare semantic facts with the dispatch snapshot, never receipt/report bytes.
        previous = task.get('previousProgress', task.get('previous', {}))
        if previous:
            new_author = set(result['progress']['authoredPairHashes']) - set(previous.get('authoredPairHashes', []))
            new_work = set(result['progress']['workTokens']) - set(previous.get('workTokens', []))
            result['meaningfulProgress'] = bool(new_author or new_work)
            if _json(path).get('disposition') == 'continue' and not result['meaningfulProgress']:
                raise GateError('Report-only continue: no semantic progress beyond dispatch snapshot')
        return result
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, subprocess.SubprocessError) as exc:
        # Invalid evidence is never persisted as validated progress.
        state = _record_state(root, locale, info, exclude=path)
        return {'roleComplete': False, 'meaningfulProgress': False, 'nextRole': role if role in ROLES else None,
                'progress': _progress(info, state), 'blockers': [str(exc)], 'savedEvidence': []}


def _owner_media_exclusion(root, locale):
    """Honor an explicit, hashed owner scope decision without fabricating passes."""
    current = root / 'runtime/cli-localization/current.json'
    if not current.is_file():
        return None
    run = Path(_json(current)['run']).resolve()
    _require(run.is_relative_to(root / 'runtime/cli-localization/runs'), 'Queue pointer escapes project')
    ref = _json(run / 'config.json').get('mediaScopeDecision')
    if not ref:
        return None
    path = (root / ref['path']).resolve()
    _require(path.is_relative_to(run) and _digest(path) == ref['sha256'], 'Owner media-scope decision changed')
    decision = _json(path)
    if locale not in decision.get('locales', []):
        return None
    _require(decision.get('authority') == 'owner' and _text(decision.get('instruction'))
             and decision.get('images') is False and decision.get('movies') is False,
             'Media exclusion requires the explicit owner decision')
    return {'decision': ref, 'reason': decision['instruction']}


def completion(root, locale) -> dict:
    root = Path(root).resolve()
    info = inspect_locale(root, locale)
    state = _record_state(root, locale, info)
    progress = _progress(info, state)
    gates = {}
    gates['visibleCorpus'] = not info['missingIds'] and info['authoredVisible'] == info['totalVisible'] and not info['errors']
    gates['glossaryCompatibility'] = progress['glossaryCompatible']
    gates['fullSemanticCoverage'] = len(state['semantic']) == info['totalVisible']
    current_handoffs = [h for h in state['handoffs'].values() if h['outputBindings'] == _bindings(info)]
    accepted = False
    for handoff in current_handoffs[-1:]:
        closure = handoff['closure']
        cycle = state['reviewCycles'].get(closure['ref']['sha256'])
        if not cycle or not cycle['clean']:
            continue
        unaffected = set(r['id'] for r in info['corpus']) - closure['ids']
        current = {r['id']: _pair(r) for r in info['corpus']}
        if (all(state['semantic'].get(id_, {}).get('pairSha256') == current[id_] for id_ in unaffected)
                and all(state['independent'].get(id_, {}).get('pairSha256') == current[id_] for id_ in closure['ids'])):
            accepted = True
    gates['independentClosureAndRegressions'] = accepted
    gates['finiteFindingsResolved'] = not progress['openFindingKeys'] and not progress['openLegacyFindingKeys']
    gates['imageTextInventoryAndPlans'] = progress['imageTextVerified']
    gates['protectedNativeResources'] = progress['resourcesVerified']
    gates['nativeArchiveVerification'] = progress['nativeArchiveVerified']
    packaged = state['package']['actual'].get('nativeFiles', []) if state['package'] else []
    gates['imageResourcesInNativeArchive'] = bool(state['images'] and progress['nativeArchiveVerified']) and all(
        any(row.get('path') == image['asset'] and image['targetSha256'] in {row.get('sha256'), row.get('plaintextSha256')} for row in packaged)
        for image in (state['images']['localized'] if state['images'] else []))
    applicability = {}
    try:
        media_exclusion = _owner_media_exclusion(root, locale)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        info['errors'].append(str(exc))
        gates['ownerScopeBinding'] = False
        media_exclusion = None
    if media_exclusion:
        for gate in ('imageTextInventoryAndPlans', 'imageResourcesInNativeArchive'):
            gates.pop(gate)
            applicability[gate] = {'status': 'not-applicable-owner-excluded', **media_exclusion}
    remaining = [name for name, passed in gates.items() if not passed]
    return {'locale': locale, 'ready': not remaining, 'scope': 'local-static-text-font-delivery' if media_exclusion else 'local-static-delivery',
            'applicability': applicability,
            'gates': gates, 'remainingGates': remaining, 'blockers': [*info['errors'], *state['recordErrors']],
            'runtime': 'not-run', 'visual': 'not-run', 'runtimeDecision': 'accepted-static',
            'publication': 'outside-scope', 'installation': 'outside-scope',
            'progress': progress, 'legacyEvidence': _legacy_candidates(root, locale)}
