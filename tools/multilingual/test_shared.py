#!/usr/bin/env python3
"""Static source/adapter regressions with positive controls; never translation."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml
from source_prepare import strict_json, strict_yaml, sha, save_json, encoded
from verify_source_inventory import compare_protected
from locale_tools import Context, locale_config, validate_entries, assemble
from text_resource_adapter import splice, literal_edit
from script_resource_adapter import verify_program
from encoded_dialogue import authored_encoding, validate_entry
from prepare_source import native_typed

CTX = None
OUTPUT = None
MODULE = None
RESULTS = {}


class SharedTests(unittest.TestCase):
    def test_explicit_locale(self):
        for code in ['es', 'es-419', 'sr', 'zh-TW']:
            self.assertEqual(locale_config(code)['siteLocale'], code)
        self.assertEqual(locale_config('sr')['script'], 'Cyrillic')
        for code in [None, '', 'unknown', 'ru', 'en', 'zh', 'ja', 'ko']:
            with self.assertRaisesRegex(ValueError, 'Unknown or excluded target locale'):
                locale_config(code)
        run = subprocess.run(['python3', '-B', str(Path(__file__).with_name('locale_tools.py')),
            '--project-root', str(CTX.root), '--data-root', str(CTX.data), 'scope'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('required: --locale', run.stderr)

    def test_complete_record_equality_and_native19(self):
        old = strict_json((CTX.root / 'source/text-corpus-8879120-02/units.json').read_bytes())
        extra = strict_json((CTX.root / 'source/native-yaml-8879120-01/units.json').read_bytes())
        self.assertEqual(CTX.units, old + extra)
        self.assertEqual(len(CTX.by_id), 20794)
        self.assertEqual(len(extra), 19)
        self.assertEqual(len(CTX.retained), 77)
        for u in extra:
            self.assertEqual(type(CTX.original(u['asset'])[1]), dict)
            value = CTX.original(u['asset'])[1]
            for key in u['path']: value = value[key]
            self.assertIs(type(value), str)
            self.assertEqual(value, u['source'])

    def test_yaml_typing_and_key_projection(self):
        original_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
        actual = strict_yaml('YES: NO\na: ON\nb: OFF\nc: true\nd: false\ne: 12\n')
        self.assertEqual(actual['YES'], 'NO')
        self.assertEqual(actual['a'], 'ON'); self.assertEqual(actual['b'], 'OFF')
        self.assertIs(actual['c'], True); self.assertIs(actual['d'], False)
        self.assertIs(type(actual['e']), int)
        self.assertEqual(yaml.SafeLoader.yaml_implicit_resolvers, original_resolvers)
        with self.assertRaisesRegex(ValueError, 'Duplicate YAML key'):
            strict_yaml('a: 1\na: 2\n')
        original = {3: {'text': 'A'}, 'EMPTY': {'flag': False}, 1: {'text': 'B'}}
        native = {'1': {'text': 'B'}, '3': {'text': 'A'}, 'EMPTY': {'flag': False}}
        self.assertEqual(encoded(native_typed(original, native)), encoded(original))
        with self.assertRaisesRegex(ValueError, 'Ambiguous native YAML property projection'):
            native_typed({1: 'A', '1': 'B'}, {'1': 'A'})

    def test_protected_typed_values_with_positive_control(self):
        original = {'id': 7, 'flag': True, 'branches': ['ok', 'cancel'], 'visible': 'A'}
        positive = copy.deepcopy(original); positive['visible'] = 'SYNTHETIC LABEL'
        compare_protected(original, positive, {('visible',): 'fixture'})
        for key, value in [('id', 8), ('flag', 1), ('branches', ['cancel', 'ok'])]:
            negative = copy.deepcopy(positive); negative[key] = value
            with self.assertRaisesRegex(ValueError, 'Exact protected value/structure/type/order mismatch'):
                compare_protected(original, negative, {('visible',): 'fixture'})

    def test_retention_and_control_rejection(self):
        unit = CTX.by_id[next(iter(CTX.retained))]
        positive = {'id': unit['id'], 'source': unit['source'], 'target': unit['source']}
        validate_entries(CTX, [positive], 'ROBOHEART')
        negative = dict(positive, target='SYNTHETIC LABEL')
        with self.assertRaisesRegex(ValueError, 'Technical preserved value changed'):
            validate_entries(CTX, [negative], 'ROBOHEART')
        unit = next(u for u in CTX.units if u['source'].startswith('\\kel') and u['id'] not in CTX.registry and u['id'] not in CTX.retained)
        positive = {'id': unit['id'], 'source': unit['source'], 'target': unit['source']}
        validate_entries(CTX, [positive], 'ROBOHEART')
        negative = dict(positive, target=unit['source'].replace('\\kel', '', 1))
        with self.assertRaisesRegex(ValueError, 'Exact native text controls/numbers changed'):
            validate_entries(CTX, [negative], 'ROBOHEART')

    def test_encoded_frame_and_inner_lf(self):
        for id, row in CTX.registry.items():
            u = CTX.by_id[id]
            target, metadata = authored_encoding(u, row['decodedEnglish'], 'ROBOHEART', CTX.registry)
            e = {'id': id, 'source': u['source'], 'target': target, 'encodedPayload': metadata}
            validate_entries(CTX, [e], 'ROBOHEART')
            if row.get('codec') == 'base64-battle-utf8':
                with self.assertRaisesRegex(ValueError, 'Encoded battle prefix/frame changed'):
                    validate_entries(CTX, [dict(e, target=target[:-1])], 'ROBOHEART')
        u = next(u for u in CTX.units if u['id'] in CTX.registry and u.get('path') == ['message_127', 'text'])
        row = CTX.registry[u['id']]
        self.assertTrue(row['decodedEnglish'].endswith('\n'))
        with self.assertRaisesRegex(ValueError, 'Decoded battle line breaks changed'):
            authored_encoding(u, row['decodedEnglish'].rstrip('\n'), 'ROBOHEART', CTX.registry)

    def test_utf16_actual_output_and_untouched_code(self):
        source = 'var a="😀"; var b="Hello";\n'
        a = len(source[:source.index('"Hello"')].encode('utf-16-le')) // 2
        u = {'id': 'fixture', 'asset': 'fixture.js', 'source': 'Hello', 'rawSource': '"Hello"',
             'spanUtf16': [a, a + 7], 'nodeType': 'Literal', 'role': 'visible'}
        e = {'target': 'SYNTHETIC "LABEL" 😀'}
        delivered = splice(source, [literal_edit(u, e['target'])], utf16=True)
        self.assertEqual(verify_program(CTX.root, 'fixture.js', source, delivered, [(u, e)]), {'fixture': e['target']})
        with self.assertRaisesRegex(ValueError, 'Delivered JS differs from exact literal assembly'):
            verify_program(CTX.root, 'fixture.js', source, delivered.replace('var a', 'var z'), [(u, e)])
        wrong = dict(u, spanUtf16=[a - 1, a + 6])
        with self.assertRaisesRegex(ValueError, 'Pinned original span changed'):
            splice(source, [literal_edit(wrong, e['target'])], utf16=True)

    def test_locale_write_isolation(self):
        allowed = CTX.locale_root / '_test-revision'
        self.assertEqual(CTX.output(allowed), allowed.resolve())
        for path in [CTX.root / 'runtime/multilingual/locales/fr/build', CTX.root / 'translation/ru/new', CTX.root / 'source/new']:
            with self.assertRaisesRegex(ValueError, 'Locale write isolation'):
                CTX.output(path)
        with tempfile.TemporaryDirectory() as temp:
            link = Path(temp) / 'out'
            link.symlink_to(CTX.root / 'translation/ru', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Locale write isolation'):
                CTX.output(link / 'new')

    def test_native19_actual_plaintext_and_mapping(self):
        units = strict_json((CTX.root / 'source/native-yaml-8879120-01/units.json').read_bytes())
        units.append(CTX.by_id['data/Actors.KEL#[1,"name"]'])
        entries = [{'id': u['id'], 'source': u['source'], 'target': 'SYNTHETIC LABEL ' + chr(65+i)} for i,u in enumerate(units)]
        pairs = validate_entries(CTX, entries, 'ROBOHEART')
        target = OUTPUT / 'native19'
        result = assemble(CTX, pairs, target, MODULE)
        self.assertEqual(result['units'], 20)
        receipt = strict_json((target / 'receipt.json').read_bytes())
        mappings = strict_json((target / 'display-mappings.json').read_bytes())
        self.assertEqual(mappings['siteLocale'], 'es')
        self.assertEqual(mappings['entries'][0]['target'], entries[-1]['target'])
        self.assertEqual(receipt['displayMappings'], 1)
        actor = next(row for row in receipt['files'] if row['originalAsset'] == 'data/Actors.KEL')
        self.assertEqual(strict_json((target / actor['path']).read_bytes())[1]['name'], 'OMORI')
        RESULTS['native19'] = result

    def test_full_inventory_noop_delivered_readback(self):
        # This is source-preserving test data, not a translated locale batch.
        pairs = [(u, {'id': u['id'], 'source': u['source'], 'target': u['source']}) for u in CTX.units]
        result = assemble(CTX, pairs, OUTPUT / 'full-source-noop', MODULE)
        self.assertEqual(result['units'], 20794)
        receipt = strict_json((OUTPUT / 'full-source-noop/receipt.json').read_bytes())
        self.assertEqual(len(set(receipt['entryIds'])), 20794)
        self.assertEqual(receipt['displayMappings'], 3505)
        RESULTS['fullSourceNoop'] = result | {'purpose': 'original-English technical no-op only; zero translation/editorial credit'}

    def test_between_write_failure_boundary(self):
        u = [CTX.by_id['data/Actors.KEL#[1,"name"]'], CTX.by_id['languages/en/XX_GENERAL.HERO#["message_4","text"]']]
        pairs = [(x, {'id': x['id'], 'source': x['source'], 'target': x['source']}) for x in u]
        output = OUTPUT / 'injected-partial'
        with self.assertRaisesRegex(ValueError, 'Injected between-file failure'):
            assemble(CTX, pairs, output, MODULE, fail_after=1)
        self.assertTrue(output.exists())
        self.assertFalse((output / 'receipt.json').exists())
        self.assertEqual(len(list((output / 'resources').rglob('*.json'))), 1)
        # Existing output rejection is checked before another production attempt.
        with self.assertRaisesRegex(ValueError, 'Preserve existing locale evidence'):
            # Use a real allowed locale path to isolate the existence guard.
            with tempfile.TemporaryDirectory(dir=str(CTX.locale_root)) as tmp:
                CTX.output(Path(tmp))


def main():
    global CTX, OUTPUT, MODULE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--yaml-module', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    CTX=Context(a.project_root, a.data_root, 'es')
    OUTPUT=a.output.resolve(); MODULE=a.yaml_module.resolve()
    if not OUTPUT.is_relative_to(CTX.root / 'runtime/multilingual') or OUTPUT.exists():
        raise ValueError('Use a new test output inside runtime/multilingual')
    OUTPUT.mkdir(parents=True); CTX.locale_root.mkdir(parents=True, exist_ok=True)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SharedTests)
    with (OUTPUT / 'unittest.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    receipt={'schemaVersion':1,'status':'passed-static' if result.wasSuccessful() else 'failed', 'tests':result.testsRun,
        'errors':len(result.errors),'failures':len(result.failures), 'inventorySha256':CTX.inventory_sha, 'results':RESULTS,
        'runtime':'not-run','visual':'not-run','nativeBoot':'not-run','editorial':'not-run',
        'recipeSha256':sha(Path(__file__).read_bytes()),
        'boundary':'Exact snapshots and actual plaintext files; bundled js-yaml and Acorn run. Game loader, native boot, fonts, Canvas, installer, saves and editorial judgments are not exercised.'}
    save_json(OUTPUT / 'result.json',receipt)
    print(json.dumps(receipt,indent=2))
    if not result.wasSuccessful():
        print((OUTPUT / 'unittest.log').read_text())
        raise SystemExit(1)


if __name__=='__main__':main()
