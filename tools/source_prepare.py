#!/usr/bin/env python3
"""Prepare shared OMORI source evidence. Never generate translated wording.

The output is deliberately not accepted while unresolved roles/media remain.
Original installation and prior research outputs are always read-only.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import yaml
from research_source import decrypt, scalars

PROJECT = Path(__file__).resolve().parent.parent
EXPECTED_SOURCE = '11d48e714e6ba1652ca76ed45c4d7622e22312547410bc694c1f46181a18773b'
EXPECTED_RU = '100e203e9ce6282bc2023e13f8b239dbcacdb552da24a05324d7789e952c8d15'
EXPECTED_INDEX = 'd7abcbbd8204dd5adcaf7d40aae88d5897a0d704ca17b15467fb96be84ab6a13'
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods')
VISIBLE_DATABASE = {
    'Actors': {'name', 'nickname', 'profile'},
    'Armors': {'name', 'description'}, 'Items': {'name', 'description'},
    'Weapons': {'name', 'description'}, 'Classes': {'name'}, 'Enemies': {'name'},
    'Skills': {'name', 'description', 'message1', 'message2'},
    'States': {'name', 'message1', 'message2', 'message3', 'message4'},
}
BLUE_VISIBLE = {
    'Chapter_Names', 'Map_Display_Names', 'Pluto_Ride_Names', 'Quest_Names',
    'Map_Character_Tag', 'Omori_Battle_System', 'Omori_Blackletter_Menu',
    'Omori_Item_Shop', 'Omori_Mainmenu_Sceneskill', 'Omori_Mainmenu',
    'Omori_Mainmenu_Sceneoptions', 'Omori_Name_Input', 'Omori_Save_Load',
    'Yin_Omori_Fixes', 'Omori_Title_Screen', 'Yin_Pizza_Delivery',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    # Dictionary key types and ordering survive JSON storage. No marker can
    # collide with original user data because every node has an explicit tag.
    if isinstance(value, dict):
        return ['dict', [[encoded(k), encoded(v)] for k, v in value.items()]]
    if isinstance(value, list):
        return ['list', [encoded(v) for v in value]]
    return [type(value).__name__, value]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')


def save_gzip(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw, mtime=0))


def identity(asset, path):
    return asset + '#' + json.dumps(path, ensure_ascii=False, separators=(',', ':'))


def strict_yaml(text):
    class Loader(yaml.SafeLoader):
        pass

    # Match the game's js-yaml YAML1.2 boolean vocabulary. YES/NO/ON/OFF are text.
    Loader.yaml_implicit_resolvers = {
        key: [(tag, pattern) for tag, pattern in values if tag != 'tag:yaml.org,2002:bool']
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    Loader.add_implicit_resolver('tag:yaml.org,2002:bool',
        re.compile(r'^(?:true|True|TRUE|false|False|FALSE)$'), list('tTfF'))

    def mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            typed_key = (type(key), key)
            if typed_key in seen:
                raise ValueError('Duplicate YAML key at line ' + str(key_node.start_mark.line + 1))
            seen.add(typed_key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml.load(text, Loader=Loader)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def grammar_role(asset, path, value, ancestors):
    if not value.strip():
        return 'preserve-exactly', 'Empty/whitespace original value; no wording to author.'
    file = Path(asset)
    key = path[-1] if path else None
    if file.suffix == '.HERO':
        if key in {'faceset', 'faceindex', 'source', 'tag', 'replace'} or any(
                k in path for k in ('background', 'character', 'InputIcons', 'inputKeysTable')):
            return 'preserve-exactly', 'Portrait, resource, geometry or name-entry glyph mapping.'
        if re.fullmatch(r'[\w-]+\.message_\w+', value):
            return 'preserve-exactly', 'LanguageManager catalog reference.'
        if asset.endswith('/XX_BLUE.HERO') and path[:1] == ('OMOCAT',):
            return 'preserve-exactly', 'Visible developer-name comparison operand; keep OMOCAT exactly (Name Input lines 737/1497).'
        if file.name == 'XX_BLUE.HERO' and tuple(path[:2]) == ('Yin_Pizza_Delivery','theNo'):
            return 'preserve-exactly', 'Native generateHouse substring-normalization operands (The No -> No), not word-sprite captions.'
        if key in {'text', 'help'} or (file.name == 'Bestiary.HERO' and key in {'name', 'EmptyEnemyName'}):
            return 'visible', 'Catalog message/help/bestiary display field; reachability is recorded separately.'
        if file.name == 'Database.HERO':
            return 'visible', 'LanguageManager.getDatabaseText dictionary value.'
        if file.name in {'System.HERO', 'menus.HERO'}:
            if 'InputNames' in path:
                return 'needs-role-review', 'Input-name table may combine display labels and symbolic input mappings; trace consumers.'
            if 'inputs' in path:
                return 'preserve-exactly', 'Input action identifiers used to draw bound input icons.'
            return 'visible', 'System/legacy menu wording, separate from icon/action/reference fields.'
        if file.name == 'XX_BLUE.HERO':
            if path[0] in BLUE_VISIBLE:
                return 'visible', 'Declared XX_BLUE display catalog; retain all legacy/test occurrences.'
            if str(path[0]).startswith(('Window_', 'Scene_')):
                return 'preserve-exactly', 'Layout parameter/expression consumed by window/scene code.'
        return 'needs-role-review', 'No verified display or technical consumer rule yet.'
    if file.name == 'Quests.PLUTO':
        if re.fullmatch(r'[\w-]+\.message_\w+', value):
            return 'preserve-exactly', 'Quest-message reference.'
        if len(path) >= 2 and path[-2:] == ('name', 'en'):
            return 'visible', 'English fallback quest title (Quest Menu lines 613–622).'
        if len(path) >= 2 and path[-2:] == ('name', 'jp'):
            return 'preserve-exactly', 'Separate Japanese locale data; source corpus is English.'
        return 'needs-role-review', 'Unresolved quest configuration field.'
    if file.suffix == '.PLUTO':
        return 'preserve-exactly', 'Atlas resource metadata or Notes template; original whole structure retained.'
    if file.suffix == '.AUBREY':
        # Tile/layer names and object property strings are not presumed invisible.
        return 'needs-role-review', 'Tiled source string; compare importer/runtime consumer before exclusion.'
    if key in VISIBLE_DATABASE.get(file.stem, set()):
        if re.fullmatch(r'\{[^{}]+\}', value):
            return 'preserve-exactly', 'Database localization lookup; wording belongs to Database.HERO.'
        return 'visible', 'Database display field; name lookup/hidden separator use still requires binding review.'
    if key == 'displayName' or (file.stem == 'System' and any(k in path for k in (
            'terms', 'currencyUnit', 'gameTitle', 'armorTypes', 'equipTypes', 'skillTypes', 'weaponTypes'))):
        return 'visible', 'RPG Maker map/system display field.'
    if key == 'note':
        return 'needs-role-review', 'Mixed notetag/action/eval field; known visible spans extracted, remaining consumers pending.'
    if 'parameters' in path:
        command = next((a for a in reversed(ancestors) if isinstance(a, dict) and 'code' in a), None)
        if command:
            tail = path[path.index('parameters') + 1:]
            code = command['code']
            if (code in (401, 405, 320, 324, 325) and tail == (0 if code in (401, 405) else 1,)) or (
                    code == 102 and len(tail) == 2 and tail[0] == 0) or (code == 402 and tail == (1,)):
                return 'visible', 'Typed event dialogue/choice/name/nickname/profile command.'
            if code in (355, 655, 356, 122, 111):
                return 'needs-role-review', 'Script/plugin/variable/condition operand; display flow needs tracing.'
            return 'preserve-exactly', 'Typed RPG Maker command resource/control parameter.'
    return 'preserve-exactly', 'Database/event identifier, resource, mechanics or original technical value.'


def context(path, ancestors):
    result = {}
    for a in ancestors:
        if not isinstance(a, dict):
            continue
        if 'id' in a and ('name' in a or 'pages' in a):
            result['record'] = {k: a[k] for k in ('id', 'name', 'displayName') if k in a}
        if 'conditions' in a and 'list' in a:
            result['pageConditions'] = a['conditions']
        if 'code' in a and 'parameters' in a:
            result['commandCode'] = a['code']
            result['indent'] = a.get('indent')
        for k in ('faceset', 'faceindex'):
            if k in a:
                result[k] = a[k]
    if 'list' in path:
        ix = path.index('list')
        result['exchangeListPath'] = list(path[:ix + 1])
        result['commandIndex'] = path[ix + 1]
    return result


def protected_tree(value, editable, path=()):
    if path in editable:
        return ['editable', editable[path]]
    if isinstance(value, dict):
        return ['dict', [[encoded(k), protected_tree(v, editable, path + (k,))] for k, v in value.items()]]
    if isinstance(value, list):
        # Large all-mechanics arrays stay one exact-value component.
        if not any(p[:len(path)] == path for p in editable):
            return encoded(value)
        return ['list', [protected_tree(v, editable, path + (i,)) for i, v in enumerate(value)]]
    return encoded(value)


def verify_glossary():
    source_path = MASTER / 'data/games/omori/glossary.json'
    ru_path = PROJECT / 'glossary/ru/approved.json'
    source_raw, ru_raw = source_path.read_bytes(), ru_path.read_bytes()
    if sha(source_raw) != EXPECTED_SOURCE or sha(ru_raw) != EXPECTED_RU:
        raise ValueError('Approved glossary version changed; reconcile before preparing source')
    source, ru = strict_json(source_raw), strict_json(ru_raw)
    wrapper = strict_json((MASTER / 'data/games/omori/glossary-translations.json').read_bytes())
    if len(source) != 699 or [r['id'] for r in source] != list(ru) or wrapper['ru'] != ru:
        raise ValueError('Glossary IDs/order/canonical RU content mismatch')
    audits = strict_json((PROJECT / 'glossary/ru/editorial-audits.json').read_bytes())
    if audits['status'] != 'accepted' or audits['targetRawSha256'] != EXPECTED_RU or audits['sourceRawSha256'] != EXPECTED_SOURCE:
        raise ValueError('Current glossary review evidence does not match inputs')
    for audit in audits['audits']:
        covered = []
        for interval in audit['actualReadRanges']:
            if set(interval['fields']) != {'source.term', 'source.meaning', 'target.term', 'target.meaning'}:
                raise ValueError('Glossary review omitted fields')
            covered.extend(range(interval['start'], interval['end'] + 1))
        if audit['status'] != 'complete-clean' or covered != list(range(1, 700)):
            raise ValueError('Glossary review has gaps or overlapping coverage')
    if len(audits['audits']) != 2:
        raise ValueError('Expected two accepted unchanged glossary audits')
    return {'sourceRawSha256': EXPECTED_SOURCE, 'ruRawSha256': EXPECTED_RU,
            'entries': 699, 'canonicalContentParity': True, 'reusedCleanFullAudits': 2,
            'auditEvidenceRawSha256': sha(canonical(audits)),
            'reviewer': audits['author'], 'freshSemanticReview': 'not run; unchanged accepted evidence reused'}


def prepare(args):
    root, out = args.game_root.resolve(), args.output.resolve()
    if PROJECT not in out.parents or out.exists() or root == out or root in out.parents:
        raise ValueError('Choose a new immutable output directory inside the canonical game project')
    if not (root / 'languages/en').is_dir() or not (root / 'data').is_dir():
        raise ValueError('Original English asset root missing')
    glossary = verify_glossary()
    research = PROJECT / 'source/research-8879120-02'
    if sha((research / 'strings.jsonl').read_bytes()) != EXPECTED_INDEX:
        raise ValueError('Research index identity changed')
    prior = strict_json((research / 'manifest.json').read_bytes())
    for entry in prior['assets']:
        if sha((root / entry['asset']).read_bytes()) != entry['encryptedSha256']:
            raise ValueError('Original encrypted asset changed: ' + entry['asset'])
    plugins_raw = (root / 'js/plugins.js').read_bytes()
    if sha(plugins_raw) != prior['pluginConfigurationSha256']:
        raise ValueError('Original plugin configuration changed')
    steam_path = root.parents[5] / 'appmanifest_1150690.acf'
    steam = steam_path.read_text()
    required = {'appid': '1150690', 'buildid': '8879120', 'manifest': '1465189839835846191', 'language': 'english'}
    for key, value in required.items():
        if not re.search(r'"' + key + r'"\s+"' + value + r'"', steam):
            raise ValueError('Steam version identity mismatch: ' + key)
    if 'Utils.RPGMAKER_VERSION = "1.6.1"' not in (root / 'js/rpg_core.js').read_text():
        raise ValueError('RPG Maker version changed')
    out.mkdir(parents=True)
    save_json(out / 'glossary-verification.json', glossary)
    paths = sorted(p for p in root.rglob('*') if p.is_file())
    graph = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        graph.append({'asset': rel, 'bytes': p.stat().st_size, 'rawSha256': sha(p.read_bytes())})
    save_json(out / 'resource-graph.json', graph)
    row_count, roles = 0, Counter()
    unique_visible = set()
    asset_reports = []
    seen = set()
    strings_path = out / 'occurrences.jsonl'
    pending_path = out / 'unresolved.jsonl'
    visible_path = out / 'visible.jsonl'
    plugins_text = plugins_raw.decode()
    plugin_config = strict_json(plugins_text[plugins_text.index('['):].strip().removesuffix(';'))
    enabled = {p['name'] for p in plugin_config if p['status']}
    scripts = []
    with strings_path.open('w', encoding='utf-8') as strings, pending_path.open('w', encoding='utf-8') as pending, visible_path.open('w', encoding='utf-8') as visible:
        def write_record(record):
            nonlocal row_count
            if record['id'] in seen:
                raise ValueError('Duplicate source identity: ' + record['id'])
            seen.add(record['id'])
            row_count += 1
            roles[record['role']] += 1
            raw = json.dumps(record, ensure_ascii=False) + '\n'
            strings.write(raw)
            if record['role'] == 'visible':
                visible.write(raw)
                unique_visible.add(record['source'])
            elif record['role'] == 'needs-role-review':
                pending.write(raw)

        for p in paths:
            rel = p.relative_to(root).as_posix()
            structured = p.suffix in {'.KEL', '.HERO', '.PLUTO', '.AUBREY'}
            script = (p.parent == root / 'js/plugins' and p.stem in enabled) or (
                p.parent == root / 'js' and p.name in {'rpg_core.js', 'rpg_managers.js', 'rpg_objects.js', 'rpg_scenes.js', 'rpg_sprites.js', 'rpg_windows.js', 'main.js'})
            if not structured and not script:
                continue
            raw_hash = sha(p.read_bytes())
            text = decrypt(p)[0] if p.suffix in {'.KEL', '.HERO', '.PLUTO', '.AUBREY', '.OMORI'} else p.read_text()
            snapshot = 'original/' + rel + '.gz'
            save_gzip(out / snapshot, text.encode())
            if script:
                scripts.append({'asset': rel, 'rawSha256': raw_hash, 'source': text})
                continue
            data = strict_json(text) if p.suffix in {'.KEL', '.AUBREY'} else strict_yaml(text)
            result_text = json.dumps(data, ensure_ascii=False) if p.suffix in {'.KEL', '.AUBREY'} else yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            restored = strict_json(result_text) if p.suffix in {'.KEL', '.AUBREY'} else strict_yaml(result_text)
            if encoded(data) != encoded(restored):
                raise ValueError('Full typed no-op roundtrip mismatch: ' + rel)
            save_gzip(out / ('noop/' + rel + '.gz'), result_text.encode())
            editable = {}
            n = Counter()
            for path, value, ancestors in scalars(data):
                if not isinstance(value, str):
                    continue
                role, reason = grammar_role(rel, path, value, ancestors)
                rid = identity(rel, path)
                record = {'id': rid, 'asset': rel, 'path': list(path), 'source': value,
                          'sourceValueSha256': sha(value.encode()), 'role': role, 'reason': reason,
                          'context': context(path, ancestors), 'reachability': 'not established by static field discovery'}
                if role == 'visible':
                    editable[path] = rid
                    # Control grammar is not yet fully bound: visible discovery
                    # does not authorize editing before the complete source gate.
                    record['protectedSyntaxStatus'] = 'needs-grammar-binding'
                write_record(record)
                n[role] += 1
                if path and path[-1] == 'note':
                    for ix, match in enumerate(re.finditer(r'<(ShortName|BlackLetterClue):([^>]*)>', value, re.I)):
                        start, end = match.span(2)
                        write_record({'id': rid + f'@note-display:{ix}', 'asset': rel, 'path': list(path),
                                      'source': value[start:end], 'role': 'visible', 'span': [start, end],
                                      'parentId': rid, 'parentValueSha256': sha(value.encode()),
                                      'reason': 'Displayed meta.' + match[1] + '; preserve the enclosing tag and all other note bytes.',
                                      'context': context(path, ancestors), 'protectedSyntaxStatus': 'parent remains wholly protected until span adapter passes'})
            protect = protected_tree(data, editable)
            protection_path = 'preserve-exactly/' + rel + '.json.gz'
            save_gzip(out / protection_path, canonical(protect))
            asset_reports.append({'asset': rel, 'rawSha256': raw_hash, 'snapshot': snapshot,
                                  'parsedSha256': sha(canonical(encoded(data))), 'stringsByRole': dict(n),
                                  'preserveExactly': protection_path, 'preserveExactlySha256': sha(canonical(protect)),
                                  'typedFullNoopRoundtrip': 'passed', 'result': 'noop/' + rel + '.gz'})
        # Parse original executable JavaScript statically; never eval or run it.
        result = subprocess.run(['node', '--expose-internals', str(PROJECT / 'tools/source_script_inventory.cjs')],
                                input=json.dumps(scripts), text=True, capture_output=True, check=True)
        parsed = strict_json(result.stdout)
        if parsed['errors']:
            raise ValueError('Original JavaScript parse errors: ' + str(parsed['errors']))
        save_json(out / 'scripts.json', parsed)
        for row in parsed['strings']:
            write_record(row)
    media = [dict(row, role='needs-visual-source-review') for row in graph if Path(row['asset']).suffix.lower() in {'.rpgmvp', '.png', '.jpg', '.webm'}]
    save_json(out / 'media.json', media)
    ancillary = [dict(row, role='needs-format-role-review') for row in graph if Path(row['asset']).suffix in {'.yaml', '.yml', '.xlsx', '.json', '.html'}]
    save_json(out / 'ancillary.json', ancillary)
    save_json(out / 'structured-assets.json', asset_reports)
    receipt = {
        'schemaVersion': 1, 'game': 'OMORI', 'steamBuild': '8879120', 'sourceLocale': 'en',
        'targetLocaleParameter': 'ru (source IDs and classifications are shared by every locale)',
        'gameRoot': str(root), 'installationChanged': False, 'runtime': 'not-run',
        'glossary': glossary, 'researchIndexRawSha256': EXPECTED_INDEX,
        'steamManifestRawSha256': sha(steam_path.read_bytes()),
        'pluginConfigurationRawSha256': sha(plugins_raw), 'originalResearchAssetsExactParity': len(prior['assets']),
        'resourceCount': len(graph), 'structuredAssetCount': len(asset_reports),
        'scriptCount': len(scripts), 'occurrenceCount': row_count, 'roles': dict(roles),
        'distinctVisibleValues': len(unique_visible), 'mediaPending': len(media), 'ancillaryPending': len(ancillary),
        'sourceGate': 'needs-review', 'translationAuthorizedByThisInventory': False,
        'limits': ['Visible means discovered display wording, not editorial acceptance or complete source coverage.',
                   'Mixed scripts, dynamic consumers, token grammar, media and ancillary files still block source handoff.',
                   'No-op semantic roundtrips do not prove OneLoader packaging, installation or game rendering.',
                   'No original script was executed; Acorn only parsed its syntax.',
                   'Independent editorial review is unavailable under current delegation permissions.'],
        'tools': {'python': sys.version.split()[0], 'pyyaml': yaml.__version__, 'node': parsed['node'], 'acorn': parsed['acorn']},
        'fileHashes': {},
    }
    for p in sorted(out.rglob('*')):
        if p.is_file():
            receipt['fileHashes'][p.relative_to(out).as_posix()] = sha(p.read_bytes())
    for p in [Path(__file__), PROJECT / 'tools/source_script_inventory.cjs', PROJECT / 'tools/research_source.py']:
        receipt.setdefault('recipeHashes', {})[p.relative_to(PROJECT).as_posix()] = sha(p.read_bytes())
    save_json(out / 'manifest.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('resourceCount', 'structuredAssetCount', 'scriptCount', 'occurrenceCount', 'roles', 'distinctVisibleValues', 'mediaPending', 'sourceGate')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    prepare(parser.parse_args())


if __name__ == '__main__':
    main()
