"""Recorded recipe preserves prerequisites and proof selection; no build launch."""
import argparse
import contextlib
import io
import shlex
import unittest
from pathlib import Path
from compile_ru_display import argument_parser
from package_ru_mod import rebuild_recipe

ROOT=Path(__file__).resolve().parents[1]


class RebuildRecipeTests(unittest.TestCase):
    def recipe(self, independent, output='first'):
        return rebuild_recipe(ROOT,argparse.Namespace(
            combined=ROOT/'build/ru/combined-2026-10-14-06',
            display=ROOT/'build/ru/display-2026-10-14-15',
            fonts=ROOT/'build/ru/fonts-2026-10-14-12',
            editorial=ROOT/'translation/ru/audits/2026-10-14-full-01/result-02.json',
            font_reproducibility=ROOT/'source/ru-font-reproducibility-2026-10-14-04.json',
            independent=independent,output=ROOT/'dist'/output))

    def test_compiler_shape_and_declared_font_reuse_prerequisite(self):
        recipe=self.recipe(None)
        self.assertLess(recipe['prerequisiteOrder'].index('verified-font-byte-checkpoint'),
                        recipe['prerequisiteOrder'].index('display-compilation'))
        self.assertEqual(recipe['fontPreparation']['mode'],'reuse-verified-byte-checkpoint')
        command=next(c for c in recipe['commands'] if 'compile_ru_display.py' in c)
        parsed=argument_parser().parse_args(shlex.split(command)[3:])
        self.assertEqual(str(parsed.fonts),'build/ru/fonts-2026-10-14-12')
        self.assertEqual(str(parsed.output),'build/ru/display-rebuild')
        self.assertFalse((ROOT/parsed.output).exists())

    def test_obsolete_compiler_shape_rejects_at_required_font_argument(self):
        error=io.StringIO()
        with contextlib.redirect_stderr(error),self.assertRaises(SystemExit) as raised:
            argument_parser().parse_args(['--combined','unused','--output','unused'])
        self.assertEqual(raised.exception.code,2)
        self.assertIn('the following arguments are required: --fonts',error.getvalue())

    def test_actual_package_proof_choice_and_bound_inputs_survive_recipe(self):
        proof=ROOT/'translation/ru/audits/2026-10-14-independent-03/reviewer/report-03.json'
        for independent in [None,proof]:
            recipe=self.recipe(independent);args=shlex.split(recipe['commands'][-1])
            self.assertEqual(args[args.index('--combined')+1],'build/ru/combined-2026-10-14-06')
            self.assertEqual(args[args.index('--display')+1],'build/ru/display-2026-10-14-15')
            self.assertEqual(args[args.index('--fonts')+1],'build/ru/fonts-2026-10-14-12')
            if independent:
                self.assertEqual(args[args.index('--independent')+1],str(proof.relative_to(ROOT)))
            else:self.assertNotIn('--independent',args)

    def test_reproduction_path_does_not_depend_on_output_directory(self):
        first=self.recipe(None,'first')['commands'][-1]
        second=self.recipe(None,'first-rebuild')['commands'][-1]
        self.assertEqual(first,second)
        self.assertIn('ru-text-8879120-rebuild-2026-10-14-full-01',first)
        # The old replay exists. The immutable editorial cycle supplies a new
        # stable replay identity; building it must not change its own metadata.
        self.assertNotIn('--output dist/ru-text-8879120-rebuild ',first)


if __name__=='__main__':unittest.main()
