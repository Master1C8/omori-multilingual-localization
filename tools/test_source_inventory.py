#!/usr/bin/env python3
"""Concrete regressions for original-value safety, not semantic quality."""
import copy
import unittest
import json
from pathlib import Path
import subprocess
from source_prepare import grammar_role, strict_json, strict_yaml
from verify_source_inventory import compare_protected
from source_media_prepare import decode_rpgmvp
from source_classify import decide
from classify_event_literals import role as event_role, note_role
from source_note_programs import fragments
from source_macro_roles import macro_parts
from source_embedded_programs import discover
from classify_plugin_literals import classify as plugin_role
from classify_embedded_literals import classify as embedded_role
from source_text_syntax import protected_parts, compare_text_controls
from text_resource_adapter import splice, js_literal, literal_edit
from source_role_closure import catalog_override


class ExactProtection(unittest.TestCase):
    def test_native_yaml_choice_words_are_strings(self):
        import yaml
        original_resolvers = repr(yaml.SafeLoader.yaml_implicit_resolvers)
        parsed = strict_yaml('yes: YES\nno: NO\non: ON\noff: OFF\ntruth: true\nfalsehood: false\nquoted: "YES"\n')
        self.assertEqual(parsed, {'yes': 'YES', 'no': 'NO', 'on': 'ON',
                                 'off': 'OFF', 'truth': True, 'falsehood': False,
                                 'quoted': 'YES'})
        self.assertEqual(repr(yaml.SafeLoader.yaml_implicit_resolvers), original_resolvers)
        with self.assertRaisesRegex(ValueError, '[Dd]uplicate'):
            strict_yaml('x: YES\nx: NO\n')

    def setUp(self):
        self.original = {'text': 'SHARED', 'resource': 'SHARED', 'id': 7,
                         'conditions': {'switch': True}, 'branches': ['ok', 'cancel'],
                         'note': '<BlackLetterClue: In the grass><IconIndex:8>'}
        self.editable = {('text',): 'fixture#text'}

    def test_positive_visible_edit_only(self):
        result = copy.deepcopy(self.original)
        result['text'] = 'SYNTHETIC DISPLAY'
        compare_protected(self.original, result, self.editable)
        self.assertEqual(result['resource'], 'SHARED')

    def test_reject_same_word_technical_edit(self):
        result = copy.deepcopy(self.original)
        result['text'] = 'SYNTHETIC DISPLAY'
        result['resource'] = 'SYNTHETIC DISPLAY'
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(self.original, result, self.editable)

    def test_reject_numeric_mechanic(self):
        result = copy.deepcopy(self.original)
        result['id'] = 8
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(self.original, result, self.editable)

    def test_reject_boolean_integer_equivalence(self):
        result = copy.deepcopy(self.original)
        result['conditions']['switch'] = 1
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(self.original, result, self.editable)

    def test_reject_branch_reorder(self):
        result = copy.deepcopy(self.original)
        result['branches'].reverse()
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(self.original, result, self.editable)

    def test_reject_whole_note_replacement(self):
        result = copy.deepcopy(self.original)
        result['note'] = '<BlackLetterClue: SYNTHETIC><IconIndex:9>'
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(self.original, result, self.editable)

    def test_yaml_semantics_and_typed_keys(self):
        original = strict_yaml('0: |\n  one\n  two\n"0": >-\n  one\n  two\n')
        self.assertEqual(original[0], 'one\ntwo\n')
        self.assertEqual(original['0'], 'one two')
        compare_protected(original, strict_yaml('0: "one\\ntwo\\n"\n"0": "one two"\n'), {})
        with self.assertRaisesRegex(ValueError, 'Exact protected value'):
            compare_protected(original, {'0': 'one two'}, {})

    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate YAML key'):
            strict_yaml('message_1: A\nmessage_1: B\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            strict_json('{"id":1,"id":2}')

    def test_roles_not_research_category(self):
        self.assertEqual(grammar_role('languages/en/XX_BLUE.HERO', ('OMOCAT', 'text'), 'OMOCAT', ())[0], 'preserve-exactly')
        self.assertEqual(grammar_role('data/Items.KEL', (850, 'note'), '<BlackLetterClue: In the grass>', ())[0], 'needs-role-review')
        self.assertEqual(grammar_role('languages/en/System.HERO', ('plugins', 'albumMenu', 'legendText', 'inputs', 0), 'ok', ())[0], 'preserve-exactly')
        self.assertEqual(grammar_role('languages/en/XX_BLUE.HERO', ('Window_NameBox', 'standardFontSize'), '$gameSystem.getMessageFontSize()', ())[0], 'preserve-exactly')

    def test_rpgmvp_can_contain_jpeg(self):
        header = bytes.fromhex('5250474d560000000003010000000000')
        key = bytes(range(16))
        for signature in [b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff\xe1']:
            body = signature + b'\x00' * (20 - len(signature))
            encrypted = bytes(v ^ key[i] if i < 16 else v for i, v in enumerate(body))
            self.assertEqual(decode_rpgmvp(header + encrypted, key), body)
        with self.assertRaisesRegex(ValueError, 'header mismatch'):
            decode_rpgmvp(b'BAD HEADER' + b'\x00' * 40, key)

    def test_collision_properties_are_exact_and_unknown_text_is_pending(self):
        control = {'asset': 'maps/Tile_Collisions_32x32.AUBREY',
                   'path': ['tileproperties', '1', 'arrowImpassable'], 'source': 'left & down & right'}
        self.assertEqual(decide(control)[0], 'preserve-exactly')
        self.assertIsNone(decide({'asset': 'maps/map1.AUBREY', 'path': ['layers', 0, 'text'], 'source': 'Read me'}))
        self.assertEqual(decide({'asset': 'data/Map001.KEL', 'path': ['events', 1, 'pages', 0, 'list', 0, 'parameters', 0],
                                 'source': 'ShowMessage XX_SYSTEM.message_0', 'context': {'commandCode': 356}})[0], 'preserve-exactly')
        self.assertIsNone(decide({'asset': 'data/Map001.KEL', 'path': [],
                                  'source': 'ShowMessage_dw_flavor_text.message_669', 'context': {'commandCode': 356}}))

    def test_actual_ast_callee_for_chained_methods_and_dynamic_labels(self):
        source = '$gameActors.actor(8).setMovementGraphicData("climbing", {name:"FA_Climb"});\n$gameVariables.setValue(23,"MOVING DAY");\n$gameVariables.setValue(824,"PapaChip");'
        helper = Path(__file__).with_name('source_script_inventory.cjs')
        result = subprocess.run(['node', '--expose-internals', str(helper)],
                                input=json.dumps([{'asset': 'fixture', 'rawSha256': 'fixture', 'source': source}]),
                                text=True, capture_output=True, check=True)
        ast = json.loads(result.stdout)
        self.assertEqual(ast['errors'], [])
        rows = {r['source']: r for r in ast['strings']}
        self.assertEqual(rows['climbing']['context']['callMethod'], 'setMovementGraphicData')
        self.assertEqual(event_role(rows['climbing'])[0], 'preserve-exactly')
        self.assertEqual(event_role(rows['MOVING DAY'])[0], 'visible-display-mapping')
        self.assertEqual(event_role(rows['PapaChip'])[0], 'preserve-exactly')

    def test_note_blocks_and_action_eval_have_exact_separate_spans(self):
        source = '<IconIndex:8>\n<After Eval>\nBattleManager.addText("VISIBLE");\n</After Eval>\n<follow action>\neval: BattleManager.addText("OTHER");\nwait: 2\n</follow action>\n'
        parts = list(fragments(source))
        self.assertEqual([r['kind'] for r in parts], ['notetag-js-block', 'action-sequence-eval'])
        for part in parts:
            a, b = part['spanCodepoints']
            self.assertEqual(source[a:b], part['source'])
        self.assertEqual(len(list(fragments('<After Eval>\nmissing close'))), 1)
        self.assertEqual(list(fragments('<After Eval>\nmissing close'))[0]['kind'], 'unclosed-block')

    def test_same_name_is_protected_in_comparison_and_visible_in_display(self):
        helper = Path(__file__).with_name('source_script_inventory.cjs')
        source = 'if(target.name() === "SPACE EX-HUSBAND") {value = 0;} BattleManager.addText("SPACE EX-HUSBAND");'
        result = subprocess.run(['node', '--expose-internals', str(helper)],
                                input=json.dumps([{'asset': 'fixture-note', 'rawSha256': 'fixture', 'source': source}]),
                                text=True, capture_output=True, check=True)
        rows = json.loads(result.stdout)['strings']
        self.assertEqual(len(rows), 2)
        self.assertEqual(note_role(rows[0])[0], 'preserve-exactly')
        self.assertEqual(note_role(rows[1])[0], 'visible')

    def test_macro_name_body_and_dynamic_actor_reference_are_separate(self):
        source = r'\n<\n[1]> Next'
        parts = macro_parts(source)
        self.assertEqual(''.join(p['source'] for p in parts), source)
        self.assertEqual([p['source'] for p in parts if p['role'] == 'visible'], [' Next'])
        self.assertEqual([p['source'] for p in macro_parts(r'\n<DISPLAY>') if p['role'] == 'visible'], ['DISPLAY'])
        with self.assertRaisesRegex(ValueError, 'Unbound native macro control'):
            macro_parts(r'\unknown[9] DISPLAY')

    def test_route_script_is_discovered_before_technical_exclusion(self):
        field = {'code': 205, 'parameters': [0, {'list': [{'code': 45, 'parameters': ['this.setImage("RESOURCE",0)']}]}]}
        programs = list(discover(field, 'fixture.KEL'))
        self.assertEqual(len(programs), 1)
        self.assertEqual(programs[0]['parentPath'], ['parameters', 1, 'list', 0, 'parameters', 0])
        self.assertEqual(programs[0]['source'], 'this.setImage("RESOURCE",0)')

    def test_ast_scope_does_not_treat_iife_as_inner_consumer(self):
        source = '(function(){var label="DISPLAY"; this.drawText("VISIBLE",0,0); route.list.push({code:45,parameters:["this.setCustomFrameXY(2,0)"]});})();'
        helper = Path(__file__).with_name('source_script_inventory.cjs')
        result = subprocess.run(['node', '--expose-internals', str(helper)],
                                input=json.dumps([{'asset': 'fixture', 'rawSha256': 'fixture', 'source': source}]),
                                text=True, capture_output=True, check=True)
        rows = {r['source']: r for r in json.loads(result.stdout)['strings']}
        self.assertIsNone(rows['DISPLAY']['context']['call'])
        self.assertEqual(rows['DISPLAY']['context']['ancestorCalls'], [])
        self.assertEqual(plugin_role(rows['VISIBLE'])[0], 'visible')
        route = rows['this.setCustomFrameXY(2,0)']
        self.assertEqual(route['context']['commandCode'], 45)
        self.assertEqual(plugin_role(route)[0], 'preserve-exactly-program')

    def test_equip_parameter_duplicate_header_uses_native_body(self):
        source = '<Custom Parameters>\nluk = 3\n<Custom Parameters>'
        parts = list(fragments(source))
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]['kind'], 'notetag-js-block')
        self.assertEqual(parts[0]['source'], 'luk = 3\n')
        a, b = parts[0]['spanCodepoints']
        self.assertEqual(source[a:b], parts[0]['source'])

    def test_dynamic_password_retains_assignment_and_comparison_identity(self):
        row = {'role': 'needs-role-review', 'source': 'SWEET', 'context': {'parentType': 'ExpressionStatement', 'statement': '"SWEET"'}}
        program = {'kind': 'variable-script-operand', 'commandParameters': [105,105,0,4,'"SWEET"'], 'originalAsset': 'data/Map169.KEL'}
        self.assertEqual(embedded_role(row, program)[0], 'visible-display-mapping')
        self.assertEqual(program['commandParameters'][4], '"SWEET"')
        unknown = dict(program, commandParameters=[999,999,0,4,'"SWEET"'])
        self.assertEqual(embedded_role(row, unknown)[0], 'needs-role-review')

    def test_quick_macro_prefix_does_not_hide_joined_visible_word(self):
        source = r'\kelHey!\!'
        parts = protected_parts(source, [(3, 'kel')])
        self.assertEqual([p['source'] for p in parts], [r'\kel', r'\!'])
        self.assertEqual(source[parts[0]['spanCodepoints'][1]:parts[1]['spanCodepoints'][0]], 'Hey!')
        compare_text_controls(source, r'\kelSYNTHETIC!\!', [(3, 'kel')])
        with self.assertRaisesRegex(ValueError, 'Exact native text controls'):
            compare_text_controls(source, r'\kelSYNTHETIC!\^', [(3, 'kel')])

    def test_namebox_payload_is_editable_but_font_and_reference_are_exact(self):
        source = r'\n<DISPLAY>\fn<RESOURCE> \v[101] %1 20 [TRASH]'
        compare_text_controls(source, r'\n<SYNTHETIC>\fn<RESOURCE> \v[101] %1 20 [TRASH]')
        with self.assertRaisesRegex(ValueError, 'Exact native text controls'):
            compare_text_controls(source, r'\n<SYNTHETIC>\fn<OTHER> \v[101] %1 20 [TRASH]')
        with self.assertRaisesRegex(ValueError, 'Exact native text controls'):
            compare_text_controls(source, r'\n<SYNTHETIC>\fn<RESOURCE> \v[101] %1 21 [TRASH]')
        malformed = r'\n<DISPLAY\i[14]'
        self.assertEqual(protected_parts(malformed)[0]['kind'], 'native-unclosed-namebox-open')
        compare_text_controls(malformed, r'\n<SYNTHETIC\i[14]')

    def test_afraid_discriminator_remains_original_with_display_mapping(self):
        row = {'asset': 'js/plugins/Custom Battle Action Text.OMORI', 'source': 'AFRAID', 'role': 'needs-role-review',
               'context': {'callMethod':'parseNoEffectEmotion', 'callArgumentIndex':1, 'parentType':'CallExpression'}}
        self.assertEqual(plugin_role(row)[0], 'visible-display-mapping')
        pure_display = dict(row, source='HAPPIER!')
        self.assertEqual(plugin_role(pure_display)[0], 'visible')

    def test_js_reinsertion_uses_utf16_and_preserves_branch_and_identity(self):
        source = 'const marker="😀"; if(target.name()==="IDENTITY") value=7; this.drawText("DISPLAY",0,0);'
        helper = Path(__file__).with_name('source_script_inventory.cjs')
        def parse(value):
            p = subprocess.run(['node','--expose-internals',str(helper)], input=json.dumps([{'asset':'fixture','rawSha256':'fixture','source':value}]), text=True,capture_output=True,check=True)
            return json.loads(p.stdout)
        ast = parse(source)
        row = next(r for r in ast['strings'] if r['source']=='DISPLAY')
        edited = splice(source, [literal_edit(row, 'SYNTHETIC " ${ ` \\ VALUE')], utf16=True)
        parsed = parse(edited)
        self.assertEqual(parsed['errors'], [])
        self.assertIn('if(target.name()==="IDENTITY") value=7;', edited)
        self.assertEqual([r['source'] for r in parsed['strings']], ['😀','IDENTITY','SYNTHETIC " ${ ` \\ VALUE'])
        with self.assertRaisesRegex(ValueError, 'Pinned original span changed'):
            splice(source, [dict(literal_edit(row, 'SYNTHETIC'), original='"OTHER"')], utf16=True)

    def test_span_overlap_rejected_and_note_metadata_survives(self):
        source = '<BlackLetterClue:DISPLAY><IconIndex:8>'
        row = {'id':'fixture','span':[17,24],'original':'DISPLAY','replacement':'SYNTHETIC'}
        self.assertEqual(splice(source,[row]), '<BlackLetterClue:SYNTHETIC><IconIndex:8>')
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            splice(source,[row,dict(row,id='second')])

    def test_js_template_encoding_preserves_line_cardinality_and_value(self):
        target = 'SYNTHETIC ${noCode} ` \\ \n NEXT'
        encoded = js_literal(target, 'ORIGINAL\nBODY', 'TemplateElement')
        self.assertEqual(encoded.count('\n'), 1)
        helper = Path(__file__).with_name('source_script_inventory.cjs')
        p = subprocess.run(['node','--expose-internals',str(helper)],input=json.dumps([{'asset':'fixture','rawSha256':'fixture','source':'const text=`'+encoded+'`;'}]), text=True,capture_output=True,check=True)
        ast = json.loads(p.stdout)
        self.assertEqual(ast['errors'], [])
        self.assertEqual(ast['strings'][0]['source'], target)

    def test_database_name_and_saved_location_are_mapped_not_overwritten(self):
        name = {'asset':'data/Enemies.KEL','path':[7,'name'],'source':'IDENTITY','role':'visible'}
        self.assertEqual(catalog_override(name)[0], 'visible-display-mapping')
        description = dict(name,path=[7,'description'])
        self.assertIsNone(catalog_override(description))
        location = dict(name,asset='data/Map013.KEL',path=['displayName'])
        self.assertEqual(catalog_override(location)[0], 'visible-display-mapping')


if __name__ == '__main__':
    unittest.main()
