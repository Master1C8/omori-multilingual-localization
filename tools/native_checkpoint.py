"""Reuse source-bound native build evidence and package exact bytes without compilation.

This proves unchanged checkpoint inputs/bytes and ZIP hash readback. It does not
repeat native compilation/decryption, perform editorial review or launch the game.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

STATUS = 'passed-archive-hash-readback-from-verified-build'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def inside(root, name):
    path = root / name
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or any(p.is_symlink() for p in [path, *path.parents] if p != root):
        raise ValueError('Checkpoint path escapes root or uses symlink: ' + str(name))
    return resolved


def hashes(root, pins):
    for name, expected in pins.items():
        if digest(inside(root, name)) != expected:
            raise ValueError('Checkpoint dependency changed: ' + name)


def build_checkpoint(root, locale, build):
    root = Path(root).resolve();build = inside(root, build)
    if not build.is_relative_to(root / 'build/multilingual-delivery' / locale):
        raise ValueError('Checkpoint build outside locale')
    manifest = load(build / 'manifest.json');accepted = load(build / 'ACCEPTANCE.json')
    if (manifest.get('siteLocale') != locale or accepted.get('siteLocale') != locale
            or accepted.get('status') != 'passed-technical-candidate'
            or accepted.get('manifestSha256') != digest(build / 'manifest.json')
            or accepted.get('bindingsSha256') != digest(build / 'bindings.json')
            or manifest.get('bindingsSha256') != digest(build / 'bindings.json')):
        raise ValueError('Missing, stale or wrong-locale native build checkpoint')
    pins = manifest['inputs'];data = root / 'source/multilingual/shared-8879120-03'
    if digest(data / 'units.json') != pins['inventorySha256'] or digest(data / 'verification.json') != pins['sourceVerificationSha256']:
        raise ValueError('Checkpoint source inventory/verification changed')
    source = load(data / 'verification.json')
    hashes(data, source['files']);hashes(root, source['inputHashes'])
    hashes(root, manifest['recipeDependencies']);hashes(root, pins['authorFiles'])
    actual_authors = {str(p.relative_to(root)) for p in (root / 'translation' / locale / 'batches').glob('*.json')}
    if actual_authors != set(pins['authorFiles']):
        raise ValueError('Checkpoint authored file set changed')
    plaintext = inside(root, pins['plaintext'])
    if (digest(plaintext / 'receipt.json') != pins['plaintextReceiptSha256']
            or digest(plaintext / 'display-mappings.json') != pins['mappingSha256']):
        raise ValueError('Checkpoint plaintext bindings changed')
    plain_receipt = load(plaintext / 'receipt.json')
    for row in plain_receipt['files']:
        if digest(inside(plaintext, row['path'])) != row['sha256']:
            raise ValueError('Checkpoint plaintext bytes changed: ' + row['path'])
    expected = {'manifest.json', 'bindings.json', 'ACCEPTANCE.json', 'INCOMPLETE.json'}
    for row in manifest['files']:
        name = 'files/' + row['path'];expected.add(name)
        if digest(inside(build, name)) != row['sha256']:
            raise ValueError('Checkpoint native bytes changed: ' + name)
    actual = {str(p.relative_to(build)) for p in build.rglob('*') if p.is_file()}
    if actual != expected or any(p.is_symlink() for p in build.rglob('*')):
        raise ValueError('Checkpoint native entry set changed')
    return build, manifest


def archive_readback(build, manifest, archive):
    expected = {'files/' + row['path']: row['sha256'] for row in manifest['files']}
    expected.update({name: digest(build / name) for name in ['manifest.json', 'bindings.json', 'ACCEPTANCE.json']})
    with ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError('Checkpoint ZIP entry set changed')
        for entry in z.infolist():
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Checkpoint ZIP contains a symlink')
            if hashlib.sha256(z.read(entry.filename)).hexdigest() != expected[entry.filename]:
                raise ValueError('Checkpoint ZIP bytes differ: ' + entry.filename)


def verify_checkpoint(root, locale, build, archive=None, receipt=None):
    root = Path(root).resolve();build, manifest = build_checkpoint(root, locale, build)
    result = {'status': 'passed-technical-candidate', 'siteLocale': locale,
        'files': len(manifest['files']), 'mappedTargets': manifest['displayMappings'],
        'authoredEntries': manifest['authoredEntries'], 'archive': None,
        'runtime': 'not-run', 'visual': 'not-run', 'editorial': 'deferred',
        'verificationMode': 'reuse-native-checkpoint-with-current-input-and-byte-hashes'}
    if archive is not None:
        archive = inside(root, archive);saved = load(inside(root, receipt))
        if (saved.get('status') not in {'passed-native-decrypted-readback', STATUS}
                or saved.get('siteLocale') != locale or saved.get('archive') != str(archive)
                or saved.get('archiveSha256') != digest(archive)
                or saved.get('buildManifestSha256') != digest(build / 'manifest.json')):
            raise ValueError('Missing, stale or wrong-locale ZIP checkpoint')
        for key in ('files', 'mappedTargets', 'authoredEntries'):
            if saved.get(key) != result[key]:raise ValueError('ZIP checkpoint coverage changed: ' + key)
        result.update(status=saved['status'], archive=str(archive))
    return result


def package_once(root, locale, build, output):
    root = Path(root).resolve();build, manifest = build_checkpoint(root, locale, build)
    output = inside(root, output)
    if not output.is_relative_to(root / 'build/multilingual-delivery' / locale) or output.is_relative_to(build):
        raise ValueError('ZIP output outside locale or inside native build')
    receipt = output.with_name(output.name + '.receipt.json')
    if receipt.exists():
        return verify_checkpoint(root, locale, build, output, receipt) | {'receipt': str(receipt)}
    if not output.exists():
        names = sorted(['files/' + row['path'] for row in manifest['files']] + ['manifest.json', 'bindings.json', 'ACCEPTANCE.json'])
        with ZipFile(output, 'x', compression=ZIP_DEFLATED, compresslevel=6) as z:
            for name in names:
                entry = ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0));entry.compress_type = ZIP_DEFLATED;entry.external_attr = 0o100644 << 16
                z.writestr(entry, (build / name).read_bytes())
    # Reconcile an interrupted write by reading its actual entries, never overwrite it.
    archive_readback(build, manifest, output)
    result = {'status': STATUS, 'siteLocale': locale, 'files': len(manifest['files']),
        'mappedTargets': manifest['displayMappings'], 'authoredEntries': manifest['authoredEntries'],
        'archive': str(output), 'archiveSha256': digest(output), 'buildManifestSha256': digest(build / 'manifest.json'),
        'verificationMode': 'one ZIP readback; reuse verified native build without recompilation',
        'runtime': 'not-run', 'visual': 'not-run', 'editorial': 'deferred'}
    with receipt.open('x') as f:json.dump(result, f, ensure_ascii=False, indent=2);f.write('\n')
    return result | {'receipt': str(receipt)}
