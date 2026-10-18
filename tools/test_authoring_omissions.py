import unittest
from authoring_omissions import validate_target_presence, validate_source_disposition
from source_text_syntax import compare_text_controls
from source_prepare import sha
from script_resource_adapter import verify_program, program_edit
from text_resource_adapter import splice
from pathlib import Path
from source_prepare import grammar_role


class OmissionTests(unittest.TestCase):
    def test_exact_pizza_normalization_operands(self):
        unit={'id':'languages/en/XX_BLUE.HERO#["Yin_Pizza_Delivery","theNo",0]',
              'asset':'languages/en/XX_BLUE.HERO','path':['Yin_Pizza_Delivery','theNo',0],
              'role':'visible','source':'The No'}
        entry={'target':'The No','sourceRoleDisposition':{'role':'preserve-exactly',
               'reason':'Exact native substring-normalization operand, not a displayed word.',
               'sourceValueSha256':sha(b'The No'),
               'consumerSourceSha256':'21235ca242ec6854f23b53dd256c7f5491eb3621caf30049ea2a8c922e9c474a'}}
        validate_source_disposition(unit,entry)
        for change in [{'id':'other'},{'path':['Yin_Pizza_Delivery','partPool',0]},
                       {'source':'Other'},{'role':'visible-display-mapping'}]:
            with self.assertRaisesRegex(ValueError,'exact visible AST source'):
                validate_source_disposition(dict(unit,**change),entry)
        bad=dict(entry['sourceRoleDisposition'],consumerSourceSha256='wrong')
        with self.assertRaisesRegex(ValueError,'exact visible AST source'):
            validate_source_disposition(unit,dict(entry,sourceRoleDisposition=bad))
        with self.assertRaisesRegex(ValueError,'Retained technical source value changed'):
            validate_source_disposition(unit,dict(entry,target='Нет'))
        self.assertEqual(grammar_role(unit['asset'],tuple(unit['path']),'The No',[])[0],'preserve-exactly')
        self.assertEqual(grammar_role(unit['asset'],('Yin_Pizza_Delivery','partPool',0),'The No',[])[0],'visible')

    def test_technical_value_cannot_be_translated(self):
        unit = {'role':'visible','spanUtf16':[0,10],'source':'GameFont'}
        entry = {'target':'GameFont', 'sourceRoleDisposition':{'role':'preserve-exactly',
                 'reason':'Font-family lookup argument, not visible prose.', 'sourceValueSha256':sha(b'GameFont')}}
        validate_source_disposition(unit, entry)
        compare_text_controls(unit['source'], 'ИгровойШрифт')
        with self.assertRaisesRegex(ValueError, 'Retained technical source value changed'):
            validate_source_disposition(unit, dict(entry, target='ИгровойШрифт'))
        with self.assertRaisesRegex(ValueError, 'exact visible AST source'):
            validate_source_disposition(dict(unit, role='visible-display-mapping'), entry)

    def test_explicit_grammar_only_omission(self):
        unit = {'asset':'fixture.js', 'id':'fixture.js@js:0:6', 'source':'The ', 'role':'visible',
                'spanUtf16':[0,6], 'rawSource':'"The "', 'nodeType':'Literal'}
        entry = {'target':'', 'syntacticOmission':{'kind':'grammatical-fragment',
                'reason':'Russian has no article; the following group name and action remain.',
                'sourceValueSha256':sha(unit['source'].encode())}}
        validate_target_presence(unit, entry)
        root = Path(__file__).resolve().parent.parent
        source = '"The " + groupName + action;'
        delivered = splice(source, [program_edit(unit, entry, ())], utf16=True)
        self.assertEqual(verify_program(root, 'fixture.js', source, delivered, [(unit, entry)])[unit['id']], '')
        for changed in [{}, {'kind':'other'}, {'sourceValueSha256':'wrong'}, {'reason':''}]:
            with self.assertRaisesRegex(ValueError, 'exact authored'):
                validate_target_presence(unit, dict(entry, syntacticOmission=dict(entry['syntacticOmission'], **changed) if changed else None))
        with self.assertRaisesRegex(ValueError, 'exact authored'):
            validate_target_presence(dict(unit, role='visible-display-mapping'), entry)
        with self.assertRaisesRegex(ValueError, 'nonempty target'):
            validate_target_presence(unit, dict(entry, target='Группа'))


if __name__ == '__main__': unittest.main()
