"""Static supplemental-font regressions; no renderer or gameplay claims."""
import json
import io
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
for directory in ('tools','tools/multilingual','tools/multilingual/delivery'):
    sys.path.insert(0,str(ROOT/directory))
import fonts


class SupplementalFonts(unittest.TestCase):
    def test_hindi_keyboard_and_clusters_use_licensed_devanagari_face(self):
        from fontTools.pens.boundsPen import BoundsPen
        config=json.loads((ROOT/'tools/multilingual/delivery/locales.json').read_text())['locales']['hi']
        rows=config['keyboardLayouts']['default'];keys=[key for row in rows for key in row]
        self.assertTrue({'{lock}','{bksp}','{confirm}','{space}'}<=set(keys))
        self.assertEqual(len(rows),6);self.assertLessEqual(max(map(len,rows)),14)
        self.assertTrue(set('कखगङअआऋािीुूंँ़्०१२३४५६७८९')<=set(config['keyboardExtra']))
        payload,_,evidence=fonts.prepare(SimpleNamespace(root=ROOT,locale='hi'),[(None,{'target':'हिन्दी क्ष त्र ज्ञ श्रद्धा कि कु क़ 123 OMORI'})],config)
        self.assertIn('fonts/Locale-Devanagari-Primary.ttf',payload)
        self.assertIn('fonts/Locale-Devanagari-Secondary.ttf',payload)
        self.assertIn(b'SIL OPEN FONT LICENSE',payload['fonts/Locale-Devanagari-Primary.ttf.OFL.txt'])
        font=fonts.TTFont(ROOT/'source/font-reference/Devanagari-NotoSansDevanagari[wdth,wght].ttf')
        try:
            self.assertIn('GSUB',font);self.assertIn('GPOS',font)
            cmap=font.getBestCmap();glyphs=font.getGlyphSet()
            for c in config['keyboardExtra']:
                pen=BoundsPen(glyphs);glyphs[cmap[ord(c)]].draw(pen);self.assertIsNotNone(pen.bounds,c)
        finally:font.close()
        self.assertEqual(evidence['rendering'],'not-run')

    def test_arabic_keyboard_and_sample_receive_a_joining_font_and_license(self):
        config=json.loads((ROOT/'tools/multilingual/delivery/locales.json').read_text())['locales']['ar']
        keys=[key for row in config['keyboardLayouts']['default'] for key in row]
        self.assertTrue({'{lock}','{bksp}','{confirm}','{space}'}<=set(keys))
        self.assertEqual(max(map(len,config['keyboardLayouts']['default'])),14)
        self.assertEqual(len(config['keyboardLayouts']['default']),5)
        payload,_,evidence=fonts.prepare(SimpleNamespace(root=ROOT,locale='ar'),[(None,{'target':'السَّلَام 123 OMORI'})],config)
        self.assertIn('fonts/Locale-Arabic-Primary.ttf',payload)
        derived=fonts.TTFont(io.BytesIO(payload['fonts/Locale-Arabic-Primary.ttf']))
        self.assertIn('GPOS',derived);self.assertIn('GSUB',derived);self.assertNotIn('fvar',derived)
        derived.close()
        self.assertIn('fonts/Locale-Arabic-Primary.ttf.OFL.txt',payload)
        font=fonts.TTFont(ROOT/'source/font-reference/Arabic-NotoSansArabic[wdth,wght].ttf')
        try:
            self.assertIn('GSUB',font);self.assertIn('GPOS',font)
            self.assertTrue(set(map(ord,config['keyboardExtra']))<=set(font.getBestCmap()))
        finally:font.close()
        face=next(row for row in evidence['faces'] if row['destination']=='fonts/Locale-Arabic-Primary.ttf')
        self.assertIn(0x200d,face['codes'])
        self.assertEqual(evidence['rendering'],'not-run')

    def test_thai_actual_missing_symbols_have_outlines_and_packaged_license(self):
        from fontTools.pens.boundsPen import BoundsPen
        font=fonts.TTFont(ROOT/'source/font-reference/Thai-NotoSansThai[wdth,wght].ttf')
        try:
            glyphs=font.getGlyphSet();cmap=font.getBestCmap()
            text='กขคฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรฤลวศษสหฬอฮะัาำิีึืุูเแโใไๆ็่้๊๋์'
            for code in map(ord,text):
                pen=BoundsPen(glyphs);glyphs[cmap[code]].draw(pen)
                self.assertIsNotNone(pen.bounds)
        finally:font.close()
        config=json.loads((ROOT/'tools/multilingual/delivery/locales.json').read_text())['locales']['th']
        payload,_,evidence=fonts.prepare(SimpleNamespace(root=ROOT,locale='th'),[(None,{'target':text})],config)
        self.assertIn('fonts/Locale-Thai-Primary.ttf',payload)
        self.assertIn('fonts/Locale-Thai-Primary.ttf.OFL.txt',payload)
        self.assertIn(b'SIL OPEN FONT LICENSE',payload['fonts/Locale-Thai-Primary.ttf.OFL.txt'])
        self.assertEqual(evidence['rendering'],'not-run')

    def test_latin_locale_does_not_receive_thai_payload(self):
        config=json.loads((ROOT/'tools/multilingual/delivery/locales.json').read_text())['locales']['de']
        payload,_,_=fonts.prepare(SimpleNamespace(root=ROOT,locale='de'),[(None,{'target':'ABC ÄÖÜ'})],config)
        self.assertFalse(any('Locale-Thai' in name for name in payload))

    def test_latin_accents_and_retained_names_share_native_role_metrics(self):
        from fontTools.pens.boundsPen import BoundsPen
        config=json.loads((ROOT/'tools/multilingual/delivery/locales.json').read_text())['locales']['pt-BR']
        payload,probes,evidence=fonts.prepare(SimpleNamespace(root=ROOT,locale='pt-BR'),[(None,{'target':'OPCOES NIVEL'})],config)
        primary=fonts.TTFont(io.BytesIO(payload['fonts/Locale-Latin-Primary.ttf']))
        secondary=fonts.TTFont(io.BytesIO(payload['fonts/Locale-Latin-Secondary.ttf']))
        try:
            for derived,source in [(primary,'OMORI_GAME2.ttf'),(secondary,'OMORI_GAME.ttf')]:
                base=fonts.TTFont(fonts.GAME/'fonts'/source)
                try:
                    self.assertEqual(derived['head'].unitsPerEm,base['head'].unitsPerEm)
                    self.assertEqual(derived['hhea'].ascent,base['hhea'].ascent)
                    self.assertEqual(derived['hhea'].descent,base['hhea'].descent)
                    # Missing accents and Cyrillic retained in old save metadata
                    # are supplied by the scaled face, never a system fallback.
                    self.assertTrue(set(map(ord,'\u00c7\u00d5\u00cd\u00d3\u041b\u0435\u0441'))<=set(derived.getBestCmap()))
                    self.assertNotIn(ord('A'),derived.getBestCmap())
                    space=derived.getBestCmap()[32];self.assertGreater(derived['hmtx'][space][0],0)
                    native=base.getGlyphSet();pen=BoundsPen(native);native[base.getBestCmap()[ord('A')]].draw(pen)
                    face=next(f for f in evidence['faces'] if f['destination'].endswith('-'+('Primary' if source=='OMORI_GAME2.ttf' else 'Secondary')+'.ttf') and 'Latin' in f['destination'])
                    self.assertEqual(face['targetCapHeight'],pen.bounds[3])
                finally:base.close()
            self.assertNotEqual(payload['fonts/Locale-Latin-Primary.ttf'],payload['fonts/Locale-Latin-Secondary.ttf'])
            self.assertEqual(evidence['rendering'],'not-run')
        finally:primary.close();secondary.close()

    def test_changed_supplemental_font_or_license_rejected_at_input_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            refs=fonts.script_font_dependencies(ROOT)
            for name in refs:
                destination=root/name;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,destination)
            self.assertEqual(fonts.script_font_dependencies(root),refs)
            for name in refs:
                path=root/name;raw=path.read_bytes();path.write_bytes(raw+b'tampered')
                with self.assertRaisesRegex(ValueError,'Supplemental font identity changed'):
                    fonts.script_font_dependencies(root)
                path.write_bytes(raw)


if __name__=='__main__':unittest.main()
