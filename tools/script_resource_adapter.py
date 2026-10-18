"""Source-bound JS literal/config assembly. Parses code; never executes game code."""
import copy
import gzip
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from source_prepare import strict_json, sha, save_json
from text_resource_adapter import splice, literal_edit, exact_span_edit
from verify_source_inventory import parse, compare_protected


def at(value, path):
    for key in path:
        value = value[key]
    return value


def put(value, path, target):
    at(value, path[:-1])[path[-1]] = target


def parse_config(raw):
    text = raw.decode() if isinstance(raw, bytes) else raw
    return strict_json(text[text.index('['):].strip().removesuffix(';'))


def programs(root):
    result = {}
    for name in ['classification-8879120-03/event-programs.json',
                 'note-programs-8879120-04/programs.json',
                 'embedded-programs-8879120-02/programs.json']:
        for row in strict_json((root / 'source' / name).read_bytes()):
            if sha(row['source'].encode()) != row['rawSha256']:
                raise ValueError('Pinned embedded program changed')
            if row['asset'] in result and result[row['asset']] != row:
                raise ValueError('Ambiguous embedded program identity')
            result[row['asset']] = row
    return result


def original_resource(root, asset):
    base = root / 'source/inventory-8879120-01'
    if asset == 'js/plugins.js':
        raw = gzip.decompress((root / 'source/text-corpus-8879120-02/original-plugins.js.gz').read_bytes())
        manifest = strict_json((base / 'manifest.json').read_bytes())
        if sha(raw) != manifest['pluginConfigurationRawSha256']:
            raise ValueError('Pinned plugin configuration changed')
        return raw.decode(), parse_config(raw)
    if asset.startswith('js/'):
        raw = gzip.decompress((base / 'original' / (asset + '.gz')).read_bytes())
        return raw.decode(), None
    reports = {r['asset']: r for r in strict_json((base / 'structured-assets.json').read_bytes())}
    report = reports[asset]
    raw = gzip.decompress((base / report['snapshot']).read_bytes())
    return raw.decode(), parse(asset, raw)


def recover_program(record, original):
    if 'linePaths' in record:
        source = ''.join(at(original, p) + '\n' for p in record['linePaths'])
    elif 'spanCodepoints' in record:
        a, b = record['spanCodepoints']
        field = at(original, record['parentPath'])
        if sha(field.encode()) != record['parentValueSha256']:
            raise ValueError('Pinned embedded program parent changed')
        source = field[a:b]
    else:
        source = at(original, record['parentPath'])
    if source != record['source']:
        raise ValueError('Embedded source versus original parent mismatch')
    return source


def parsed_literals(root, asset, source):
    result = subprocess.run(['node', '--expose-internals', str(root / 'tools/source_literal_values.cjs')],
        input=json.dumps([{'asset': asset, 'source': source, 'rawSha256': sha(source.encode())}]),
        text=True, capture_output=True)
    if result.returncode:
        raise ValueError('Literal parser failed: ' + result.stderr[-1500:])
    report = strict_json(result.stdout)
    if report['errors']:
        raise ValueError('Delivered JavaScript does not parse: ' + str(report['errors']))
    return {tuple(r['spanUtf16']): r for r in report['strings']}


def verify_program(root, asset, original, delivered, pairs, macros=()):
    edits = [program_edit(unit, entry, macros) for unit, entry in pairs]
    if delivered != splice(original, edits, utf16=True):
        raise ValueError('Delivered JS differs from exact literal assembly')
    if original.count('\n') != delivered.count('\n'):
        raise ValueError('Embedded physical line count changed')
    parsed = parsed_literals(root, asset, delivered)
    targets, adjustment = {}, 0
    for edit, (unit, entry) in sorted(zip(edits, pairs), key=lambda p: p[0]['span'][0]):
        start, stop = edit['span']
        length = len(edit['replacement'].encode('utf-16-le')) // 2
        node = parsed.get((start + adjustment, start + adjustment + length))
        expected = entry['target'] if unit['role'] == 'visible' else unit['source']
        if node is None or node['source'] != expected or node['nodeType'] != unit['nodeType']:
            raise ValueError('Delivered parsed literal at adjusted boundary differs')
        targets[unit['id']] = node['source']
        adjustment += length - (stop - start)
    return targets


def program_edit(unit, entry, macros):
    edit = literal_edit(unit, entry['target'] if unit['role'] == 'visible' else unit['source'], macros)
    if unit['role'] == 'visible-display-mapping' or entry['target'] == unit['source']:
        edit['replacement'] = unit['rawSource']
    return edit


def build_resources(root, output, pairs, macros):
    """Assemble direct scripts/config and source-bound embedded programs."""
    known = programs(root)
    grouped, originals, trees, changes = defaultdict(list), {}, {}, defaultdict(list)
    for unit, entry in pairs:
        binding = known.get(unit['asset'])
        asset = binding['originalAsset'] if binding else unit['asset']
        if asset not in originals:
            originals[asset], trees[asset] = original_resource(root, asset)
        grouped[unit['asset']].append((unit, entry))
    results = copy.deepcopy(trees)
    script_outputs, holes = {}, defaultdict(dict)
    for source_asset, rows in grouped.items():
        record = known.get(source_asset)
        asset = record['originalAsset'] if record else source_asset
        if 'spanUtf16' in rows[0][0]:
            source = recover_program(record, trees[asset]) if record else originals[asset]
            edits = [program_edit(u, e, macros) for u, e in rows]
            result = splice(source, edits, utf16=True)
            verify_program(root, source_asset, source, result, rows, macros)
            if record:
                if 'linePaths' in record:
                    lines = result.splitlines(keepends=True)
                    if len(lines) != len(record['linePaths']) or any(not s.endswith('\n') for s in lines):
                        raise ValueError('Embedded event line binding changed')
                    for p, text in zip(record['linePaths'], lines):
                        put(results[asset], p, text[:-1]); holes[asset][tuple(p)] = source_asset
                elif 'spanCodepoints' in record:
                    path = tuple(record['parentPath'])
                    changes[(asset, path)].append({'id': source_asset, 'span': record['spanCodepoints'],
                                                  'original': source, 'replacement': result})
                    holes[asset][path] = source_asset
                else:
                    put(results[asset], record['parentPath'], result)
                    holes[asset][tuple(record['parentPath'])] = source_asset
            else:
                script_outputs[asset] = result
        else:
            if asset != 'js/plugins.js':
                raise ValueError('Only plugin configuration supports non-AST script fields')
            for unit, entry in rows:
                path = tuple(unit['path'])
                if 'spanCodepoints' in unit or 'span' in unit:
                    field = at(trees[asset], path)
                    if sha(field.encode()) != unit['parentValueSha256']:
                        raise ValueError('Pinned plugin macro parent changed')
                    changes[(asset, path)].append(exact_span_edit(unit, entry['target'], macros))
                else:
                    if at(trees[asset], path) != unit['source']:
                        raise ValueError('Pinned plugin configuration value changed')
                    put(results[asset], path, entry['target'])
                holes[asset][path] = unit['id']
    for (asset, path), edits in changes.items():
        put(results[asset], path, splice(at(trees[asset], path), edits))
    built = []
    for asset in originals:
        if asset in script_outputs:
            serialized, kind = script_outputs[asset], 'script'
        elif asset == 'js/plugins.js':
            text = originals[asset]
            begin, end = text.index('['), text.rfind(']') + 1
            serialized = text[:begin] + json.dumps(results[asset], ensure_ascii=False, indent=2) + text[end:]
            compare_protected(trees[asset], parse_config(serialized), holes[asset])
            parsed_literals(root, asset, serialized)
            kind = 'plugin-config'
        else:
            serialized = json.dumps(results[asset], ensure_ascii=False, indent=2) + '\n'
            compare_protected(trees[asset], parse(asset, serialized.encode()), holes[asset])
            kind = 'structured-embedded'
        out = output / 'resources' / (asset + ('.json' if kind == 'structured-embedded' else ''))
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(serialized)
        built.append({'originalAsset': asset, 'output': str(out.relative_to(output)), 'rawSha256': sha(out.read_bytes()),
                      'kind': kind, 'originalPlaintextSha256': sha(originals[asset].encode())})
    return built


def verify_resources(root, receipt_path, resources, pairs, macros):
    known = programs(root)
    actual, originals = {}, {}
    for row in resources:
        path = receipt_path.parent / row['output']
        raw = path.read_bytes()
        if sha(raw) != row['rawSha256']:
            raise ValueError('Delivered script/config resource changed')
        asset = row['originalAsset']
        text, tree = original_resource(root, asset)
        if sha(text.encode()) != row['originalPlaintextSha256']:
            raise ValueError('Original script/config receipt binding changed')
        originals[asset] = (text, tree)
        actual[asset] = raw.decode() if row['kind'] == 'script' else parse_config(raw) if row['kind'] == 'plugin-config' else parse(asset, raw)
    grouped = defaultdict(list)
    for pair in pairs:
        grouped[pair[0]['asset']].append(pair)
    values = {}
    for source_asset, rows in grouped.items():
        record = known.get(source_asset)
        asset = record['originalAsset'] if record else source_asset
        text, tree = originals[asset]
        if 'spanUtf16' in rows[0][0]:
            original = recover_program(record, tree) if record else text
            if record:
                if 'linePaths' in record:
                    delivered = ''.join(at(actual[asset], p) + '\n' for p in record['linePaths'])
                elif 'spanCodepoints' in record:
                    field = at(actual[asset], record['parentPath'])
                    # Match exact whole parent using source-based edits, including all sibling blocks.
                    sibling = [(u, e) for u, e in pairs if u['asset'] in known and
                               known[u['asset']].get('parentPath') == record['parentPath'] and
                               known[u['asset']]['originalAsset'] == asset]
                    blocks = defaultdict(list)
                    for u, e in sibling: blocks[u['asset']].append((u, e))
                    block_edits = []
                    offset = 0
                    for key, pp in sorted(blocks.items(), key=lambda v: known[v[0]]['spanCodepoints'][0]):
                        rec = known[key]; src = recover_program(rec, tree)
                        replacement = splice(src, [program_edit(u, e, macros) for u, e in pp], utf16=True)
                        block_edits.append({'id': key, 'span': rec['spanCodepoints'], 'original': src, 'replacement': replacement})
                        if key == source_asset:
                            start = rec['spanCodepoints'][0] + offset
                            delivered = field[start:start + len(replacement)]
                        offset += len(replacement) - len(src)
                    if field != splice(at(tree, record['parentPath']), block_edits):
                        raise ValueError('Delivered embedded note parent differs')
                else:
                    delivered = at(actual[asset], record['parentPath'])
            else:
                delivered = actual[asset]
            values.update(verify_program(root, source_asset, original, delivered, rows, macros))
        else:
            from text_resource_adapter import verify_delivered_spans
            mixed = defaultdict(list)
            for unit, entry in rows:
                if 'spanCodepoints' in unit or 'span' in unit: mixed[tuple(unit['path'])].append((unit, entry))
                else: values[unit['id']] = at(actual[asset], unit['path'])
            for p, pp in mixed.items(): values.update(verify_delivered_spans(at(tree, p), at(actual[asset], p), pp, macros))
    return values
