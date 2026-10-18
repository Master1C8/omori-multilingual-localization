"""Full-rebuild equivalence and real native prefix/source rejection fixtures."""
import copy,json,shutil,sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/visual-qa'))
import ui_derivative as d
control='diagnostics/native-artifacts-20261017/quest-ui-positive-control-07.json'
old='build/multilingual-delivery/vi/native-visual-repair-20261017-02';old_zip='build/multilingual-delivery/vi/OMORI-vi-visual-repair-20261017-02.zip'
new='build/multilingual-delivery/vi/native-quest-ui-control-20261017-07';new_zip='build/multilingual-delivery/vi/OMORI-vi-quest-ui-control-20261017-07.zip'
d.verify('vi',new,new_zip,new_zip+'.receipt.json')
full=d.load(ROOT/'build/multilingual-delivery/vi/native-visual-repair-20261017-06/manifest.json');derived=d.load(ROOT/new/'manifest.json')
assert {r['path']:r['sha256'] for r in derived['files']}=={r['path']:r['sha256'] for r in full['files']}
bad_control=ROOT/'runtime/visual-qa/20261017-level-audit/ui-control-negative-07.json';assert not bad_control.exists()
bad=d.load(ROOT/control);bad['currentPins'][d.UI]='0'*64;bad_control.write_bytes(d.raw(bad))
try:d.expected('vi',old,old_zip,d.relative(bad_control))
except ValueError as e:assert str(e)=='UI positive-control source changed'
else:raise AssertionError('Changed source/control binding accepted')
fixture=ROOT/'build/multilingual-delivery/vi/ui-prefix-rejection-fixture-20261017-07';archive=fixture.with_suffix('.zip');assert not fixture.exists() and not archive.exists()
shutil.copytree(ROOT/old,fixture)
path=fixture/'files'/d.BOOT;plain=d.crypt(path.read_bytes(),True)
assert b'/* Presentation geometry' in plain
changed=plain.replace(b'/* Presentation geometry',b'/* presentation geometry',1);path.write_bytes(d.crypt(changed))
m=d.load(fixture/'manifest.json');row=next(r for r in m['files'] if r['path']==d.BOOT);row.update(sha256=d.digest(path),plaintextSha256=d.blobsha(changed),bytes=path.stat().st_size)
(fixture/'manifest.json').write_bytes(d.raw(m));gate=d.load(fixture/'ACCEPTANCE.json');gate['manifestSha256']=d.digest(fixture/'manifest.json');(fixture/'ACCEPTANCE.json').write_bytes(d.raw(gate))
with ZipFile(ROOT/old_zip) as source,ZipFile(archive,'x',compression=ZIP_DEFLATED) as target:
 for name in source.namelist():target.writestr(name,(fixture/name).read_bytes())
try:d.parent('vi',d.relative(fixture),d.relative(archive))
except ValueError as e:assert str(e)=='Parent UI prefix does not match its source hash',str(e)
else:raise AssertionError('A native-valid but source-mismatched UI prefix was accepted')
result={'status':'pass','nativeResourcesEquivalentToFullRebuild':len(full['files']),'changedControlSourceRejected':True,'sourceMismatchedNativePrefixRejectedAtIntendedBoundary':True,'negativeFixture':d.relative(fixture),'scope':'Real native AES/ZIP/readback inputs; no runtime or Canvas mocked. Per-locale visual acceptance remains separate.'}
(ROOT/'runtime/visual-qa/20261017-level-audit/ui-derivative-regression-07.json').write_bytes(d.raw(result));print(json.dumps(result))
