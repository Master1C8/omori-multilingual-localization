"""Bind a fully rebuilt menu repair to its actual native acceptance."""
import argparse
from pathlib import Path
from ui_derivative import ROOT,UI,BOOT,pins,parent,build_checkpoint,archive_readback,crypt,load,digest,relative,inside,raw

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',required=True);p.add_argument('--locale',choices=['tr','uk','ar'],default='tr');a=p.parse_args();code=a.locale
old=f'build/multilingual-delivery/{code}/native-quest-ui-20261017-07'
old_zip=f'build/multilingual-delivery/{code}/OMORI-{code}-quest-ui-20261017-07.zip'
full=f'build/multilingual-delivery/{code}/native-menu-ui-20261018-02'
full_zip=f'build/multilingual-delivery/{code}/OMORI-{code}-menu-ui-20261018-02.zip'
if code=='ar':
    old='build/multilingual-delivery/ar/native-visual-repair-20261017-17'
    old_zip='build/multilingual-delivery/ar/OMORI-ar-visual-repair-20261017-17.zip'
    full='build/multilingual-delivery/ar/native-item-help-20261018-01'
    full_zip='build/multilingual-delivery/ar/OMORI-ar-item-help-20261018-01.zip'
b,z,m,previous,i=parent(code,old,old_zip)
f,fm=build_checkpoint(ROOT,code,full);archive_readback(f,fm,inside(ROOT,full_zip))
expected_boot=crypt((ROOT/UI).read_bytes()+b'\n'+previous[i:])
assert {r['path'] for r in m['files']}=={r['path'] for r in fm['files']}
for row in fm['files']:
    wanted=expected_boot if row['path']==BOOT else (b/'files'/row['path']).read_bytes()
    assert (f/'files'/row['path']).read_bytes()==wanted,'Full build differs beyond UI prefix: '+row['path']
assert m['inputs']==fm['inputs'] and m['fonts']==fm['fonts'] and m['config']==fm['config']
assert (b/'bindings.json').read_bytes()==(f/'bindings.json').read_bytes()
run=a.run.resolve();assert run.is_relative_to(ROOT/'runtime/visual-qa')
review=run/code/'visual-review.json';picture=ROOT/'dist/screenshots/20261017-native'/f'{code}-04-omori-equipment.png'
installed=load(run/f'{code}-installation.json');cap=load(run/code/'equipment-capture.json')
stopped=load(run/code/'stopped.json');base=load(ROOT/'runtime/visual-qa/20261017-native/baseline.json')
assert load(review)['status']=='pass' and load(review)['sha256']==digest(picture)==cap['sha256']
assert installed['packageArchiveSha256']==digest(ROOT/full_zip) and installed['locale']==code and installed['runtimeChannel']=='en'
assert installed['fileHashes']=={r['path']:r['sha256'] for r in fm['files']}
assert stopped['stopped'] and stopped['protectedFiles']==base['saves']
assert load(run/'russian-level-restoration.json')['status']=='verified'
assert load(run/'restoration.json')['status']=='verified' and load(run/'equipment-status.json')['status']=='complete'
result=dict(status='passed-full-build-and-native-control',currentPins=pins(),fullBuild=full,fullManifestSha256=digest(f/'manifest.json'),
    nativeReview=relative(review),nativeReviewSha256=digest(review),nativeImage=relative(picture),nativeImageSha256=digest(picture),
    nativeResourcesCompared=len(fm['files']),changedResources=[BOOT])
output=inside(ROOT,a.output);assert not output.exists();output.write_bytes(raw(result))
assert load(output)==result
print('FULL_AND_NATIVE_MENU_CONTROL',len(fm['files']))
