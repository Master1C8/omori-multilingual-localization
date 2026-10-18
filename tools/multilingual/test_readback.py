#!/usr/bin/env python3
"""Verify new receipt revalidation and frozen tooling against delivered test files."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from source_prepare import sha, strict_json, save_json, canonical
from locale_tools import Context, assemble, glossary_check


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--yaml-module', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args();ctx=Context(a.project_root,a.data_root,'es')
    if a.output.exists() or not a.output.resolve().is_relative_to(ctx.root/'runtime/multilingual'):
        raise ValueError('Use a fresh multilingual evidence path')
    receipt=strict_json((a.fixture/'receipt.json').read_bytes())
    pairs=[(ctx.by_id[e['id']],e) for e in receipt['entries']]
    positive=assemble(ctx,pairs,a.fixture,a.yaml_module,verify_only=True)
    controls=[]
    with tempfile.TemporaryDirectory() as tmp:
        temp=Path(tmp)
        changed=temp/'tampered';shutil.copytree(a.fixture,changed)
        row=next(r for r in receipt['files'] if r['originalAsset']=='data/Actors.KEL')
        file=changed/row['path'];tree=strict_json(file.read_bytes());tree[1]['name']='SYNTHETIC LOGIC MUTATION'
        file.write_text(json.dumps(tree,ensure_ascii=False,indent=2)+'\n')
        forged=copy.deepcopy(receipt);next(r for r in forged['files'] if r['originalAsset']=='data/Actors.KEL')['sha256']=sha(file.read_bytes());save_json(changed/'receipt.json',forged)
        try:assemble(ctx,pairs,changed,a.yaml_module,verify_only=True)
        except ValueError as error:
            assert 'Delivered plaintext differs from current authored source assembly' in str(error)
            controls.append('Changed protected identity rejected despite forged receipt hash')
        else:raise AssertionError('Protected mutation accepted')
        extra=temp/'extra';shutil.copytree(a.fixture,extra);(extra/'resources/EXTRA.json').write_text('{}')
        try:assemble(ctx,pairs,extra,a.yaml_module,verify_only=True)
        except ValueError as error:
            assert 'Delivered resource file set mismatch' in str(error);controls.append('Extra delivered file rejected')
        else:raise AssertionError('Extra delivered file accepted')
        frozen=temp/'tooling';shutil.copytree(Path(__file__).parent,frozen,ignore=shutil.ignore_patterns('__pycache__'))
        command=['python3','-B',str(frozen/'locale_tools.py'),'--project-root',str(ctx.root),'--data-root',str(ctx.data),'--locale','es','scope']
        frozen_run=subprocess.run(command,text=True,capture_output=True,check=True)
        assert strict_json(frozen_run.stdout)['siteLocale']=='es'
        subprocess.run(['node','--expose-internals',str(frozen/'source_literal_values.cjs')],input=json.dumps([{'asset':'fixture','source':'var a="SAMPLE";'}]),text=True,capture_output=True,check=True)
        controls.append('Frozen tooling runs outside tools with explicit project/data roots')
        # Synthetic glossary contract: the CLI transport is replaced here only.
        # Real current-canonical CLI evidence is environment-01.json.
        folder=temp/'glossary';folder.mkdir()
        source=[{'id':'sample','term':'SAMPLE','meaning':'Synthetic contract fixture.'}]
        target=copy.deepcopy(source);save_json(folder/'source.json',source);save_json(folder/'target.json',target)
        reference_sha=sha(canonical({'sourceLocale':'en','entries':source}))
        snapshot={'siteLocale':'es','sourceLocale':'en','sourceReferenceSha256':reference_sha,
            'sourceFile':'source.json','targetFile':'target.json'}
        for kind in ['source','target']:
            digest=sha((folder/(kind+'.json')).read_bytes())
            review={'status':'accepted','standard':'standard','artifactSha256':digest,'sourceReferenceSha256':reference_sha,'unresolved':[],
                'layers':[{'status':'complete-clean','actualReadIds':['sample'],'dimensions':['fidelity','native-language'],'reviewer':'synthetic evidence fixture'} for _ in range(2)]}
            save_json(folder/(kind+'-readiness.json'),review)
            snapshot.update({kind+'Sha256':digest,kind+'ReadinessFile':kind+'-readiness.json',kind+'ReadinessSha256':sha((folder/(kind+'-readiness.json')).read_bytes())})
        save_json(folder/'snapshot.json',snapshot)
        with patch('locale_tools.current_glossary',return_value={'reference':{'sha256':reference_sha}}):
            assert glossary_check(ctx,folder/'snapshot.json',temp)['entries']==1
        with patch('locale_tools.current_glossary',return_value={'reference':{'sha256':'0'*64}}):
            try:glossary_check(ctx,folder/'snapshot.json',temp)
            except ValueError as error:
                assert 'CURRENT canonical English revision' in str(error);controls.append('Old glossary revision rejected with matching positive control')
            else:raise AssertionError('Old glossary source accepted')
    result={'schemaVersion':1,'status':'passed-static','positiveDeliveredReadback':positive,'negativeControls':controls,
        'inventorySha256':ctx.inventory_sha,'fixtureReceiptSha256':sha((a.fixture/'receipt.json').read_bytes()),
        'recipeSha256':sha(Path(__file__).read_bytes()),'localeToolSha256':sha(Path(__file__).with_name('locale_tools.py').read_bytes()),
        'runtime':'not-run','nativeBoot':'not-run','visual':'not-run',
        'boundary':'Actual delivered plaintext, independent authored reconstruction and relocated tooling. Glossary CLI transport replaced only for synthetic dependency contract controls; no semantic review.'}
    save_json(a.output,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
