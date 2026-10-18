"""Source-bound UI-prefix derivatives of immutable native translation packages.

Unchanged native resources retain their parent's compilation evidence. A fully
rebuilt and visually accepted Vietnamese control binds the current presentation
change. This tool does not claim to recompile other translation resources.
"""
import argparse,copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/multilingual/delivery'),str(ROOT/'tools/multilingual'),str(ROOT/'tools')]
from native_delivery import crypt,locale_config
from native_checkpoint import inside,hashes,archive_readback,build_checkpoint
MODE='native-ui-prefix-derivative-v1'
UI='tools/multilingual/delivery/ui_layout.js'
SELF='tools/visual-qa/ui_derivative.py'
HISTORY=['tools/multilingual/delivery/compiler.py','tools/multilingual/delivery/native_delivery.py','tools/multilingual/delivery/locales.json']
BOOT='js/plugins/OmoriLocale_Bootstrap.OMORI'
MARK=b'/* Typed display adapters. Native names, values, keys and comparisons stay raw. */'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blobsha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def raw(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def relative(p):return str(Path(p).resolve().relative_to(ROOT))
def pins():return {n:digest(ROOT/n) for n in [UI,SELF,*HISTORY,'tools/native_checkpoint.py']}
def parent(locale,build_name,archive_name):
    build=inside(ROOT,build_name);archive=inside(ROOT,archive_name)
    if not build.is_relative_to(ROOT/'build/multilingual-delivery'/locale):raise ValueError('Wrong parent locale directory')
    m=load(build/'manifest.json');a=load(build/'ACCEPTANCE.json')
    if m['siteLocale']!=locale or a['siteLocale']!=locale or a['status']!='passed-technical-candidate' or a['manifestSha256']!=digest(build/'manifest.json') or a['bindingsSha256']!=digest(build/'bindings.json') or m['bindingsSha256']!=digest(build/'bindings.json'):raise ValueError('Parent native acceptance changed')
    if m['config']!=locale_config(locale):raise ValueError('Parent locale configuration changed')
    p=m['inputs'];data=ROOT/'source/multilingual/shared-8879120-03'
    if digest(data/'units.json')!=p['inventorySha256'] or digest(data/'verification.json')!=p['sourceVerificationSha256']:raise ValueError('Parent source identity changed')
    source=load(data/'verification.json');hashes(data,source['files']);hashes(ROOT,source['inputHashes']);hashes(ROOT,p['authorFiles'])
    if {relative(f) for f in (ROOT/'translation'/locale/'batches').glob('*.json')}!=set(p['authorFiles']):raise ValueError('Parent author file set changed')
    plain=inside(ROOT,p['plaintext'])
    if digest(plain/'receipt.json')!=p['plaintextReceiptSha256'] or digest(plain/'display-mappings.json')!=p['mappingSha256']:raise ValueError('Parent plaintext binding changed')
    for row in load(plain/'receipt.json')['files']:
        if digest(inside(plain,row['path']))!=row['sha256']:raise ValueError('Parent plaintext resource changed')
    expected={'manifest.json','bindings.json','ACCEPTANCE.json','INCOMPLETE.json'}
    for row in m['files']:
        name='files/'+row['path'];expected.add(name)
        if digest(inside(build,name))!=row['sha256']:raise ValueError('Parent native resource changed: '+name)
    if {str(p.relative_to(build)) for p in build.rglob('*') if p.is_file()}!=expected:raise ValueError('Parent native file set changed')
    archive_readback(build,m,archive)
    old=crypt((build/'files'/BOOT).read_bytes(),True);i=old.index(MARK)
    if not old[:i].endswith(b'\n') or blobsha(old[:i-1])!=m['recipeDependencies'][UI]:raise ValueError('Parent UI prefix does not match its source hash')
    if old[:i-1]==(ROOT/UI).read_bytes():raise ValueError('Parent already contains the target UI prefix; reuse its checkpoint')
    for name,h in m['recipeDependencies'].items():
        if name==UI:continue
        if digest(inside(ROOT,name))==h:continue
        frozen=ROOT/'diagnostics/native-artifacts-20261017/recipe-02'/name
        if name not in HISTORY or not frozen.is_file() or digest(frozen)!=h:raise ValueError('Unchanged parent recipe dependency differs: '+name)
    return build,archive,m,old,i
def expected(locale,build_name,archive_name,control_name):
    control_path=inside(ROOT,control_name);control=load(control_path)
    if control['status']!='passed-full-build-and-native-control' or control['currentPins']!=pins():raise ValueError('UI positive-control source changed')
    review=inside(ROOT,control['nativeReview']);picture=inside(ROOT,control['nativeImage'])
    if digest(review)!=control['nativeReviewSha256'] or digest(picture)!=control['nativeImageSha256'] or load(review)['status']!='pass':raise ValueError('Native UI control acceptance changed')
    build,archive,m,old,i=parent(locale,build_name,archive_name)
    new_plain=(ROOT/UI).read_bytes()+b'\n'+old[i:]
    subprocess.run(['node','--check'],input=new_plain,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
    changed=crypt(new_plain);rows=copy.deepcopy(m['files'])
    row=next(r for r in rows if r['path']==BOOT);row.update(sha256=blobsha(changed),plaintextSha256=blobsha(new_plain),bytes=len(changed))
    proof={'kind':MODE,'parentBuild':relative(build),'parentArchive':relative(archive),'parentManifestSha256':digest(build/'manifest.json'),'parentAcceptanceSha256':digest(build/'ACCEPTANCE.json'),'parentArchiveSha256':digest(archive),'control':relative(control_path),'controlSha256':digest(control_path),'oldUiSourceSha256':m['recipeDependencies'][UI],'newUiSourceSha256':digest(ROOT/UI),'changedFiles':[BOOT],'unchangedResourcesRetainParentEvidence':True}
    result=copy.deepcopy(m);result['files']=rows;result['recipeDependencies']=pins();result['derivation']=proof
    return result,changed,build
def verify(locale,build_name,archive_name,receipt_name=None):
    build=inside(ROOT,build_name);archive=inside(ROOT,archive_name);m=load(build/'manifest.json');proof=m['derivation']
    wanted,changed,parent_build=expected(locale,proof['parentBuild'],proof['parentArchive'],proof['control'])
    if m!=wanted:raise ValueError('UI derivative manifest differs from its bound transformation')
    a=load(build/'ACCEPTANCE.json')
    if a['status']!='passed-technical-candidate' or a['manifestSha256']!=digest(build/'manifest.json') or a['bindingsSha256']!=digest(build/'bindings.json') or (build/'bindings.json').read_bytes()!=(parent_build/'bindings.json').read_bytes():raise ValueError('UI derivative acceptance/bindings differ')
    wanted_names={'manifest.json','bindings.json','ACCEPTANCE.json','INCOMPLETE.json'}|{'files/'+r['path'] for r in m['files']}
    if {str(p.relative_to(build)) for p in build.rglob('*') if p.is_file()}!=wanted_names:raise ValueError('UI derivative file set changed')
    for row in m['files']:
        p=inside(build,'files/'+row['path'])
        if digest(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('UI derivative native file changed')
    if (build/'files'/BOOT).read_bytes()!=changed:raise ValueError('UI derivative bootstrap differs')
    archive_readback(build,m,archive)
    if receipt_name is not None:
        r=load(inside(ROOT,receipt_name))
        if r['verificationMode']!=MODE or r['archiveSha256']!=digest(archive) or r['buildManifestSha256']!=digest(build/'manifest.json') or r['controlSha256']!=proof['controlSha256']:raise ValueError('UI derivative package receipt changed')
    return {'status':'passed-ui-prefix-native-readback','siteLocale':locale,'files':len(m['files']),'archiveSha256':digest(archive),'buildManifestSha256':digest(build/'manifest.json'),'controlSha256':proof['controlSha256']}
def create(locale,build_name,archive_name,control_name,output_name,zip_name):
    output=inside(ROOT,output_name);archive=inside(ROOT,zip_name)
    scope=ROOT/'build/multilingual-delivery'/locale
    if not output.is_relative_to(scope) or not archive.is_relative_to(scope) or archive.is_relative_to(output):raise ValueError('UI derivative output outside locale build scope')
    if output.exists() or archive.exists():raise ValueError('Preserve existing derivative outputs')
    m,changed,source=expected(locale,build_name,archive_name,control_name);output.mkdir(parents=True)
    (output/'INCOMPLETE.json').write_bytes(raw({'status':'incomplete','siteLocale':locale,'acceptance':False}))
    for row in m['files']:
        name=row['path'];target=output/'files'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if name==BOOT:target.write_bytes(changed)
        else:shutil.copy2(source/'files'/name,target)
        if digest(target)!=row['sha256']:raise ValueError('UI derivative write readback failed')
    shutil.copy2(source/'bindings.json',output/'bindings.json');(output/'manifest.json').write_bytes(raw(m))
    if digest(output/'bindings.json')!=m['bindingsSha256'] or load(output/'manifest.json')!=m:raise ValueError('UI derivative metadata write readback failed')
    (output/'ACCEPTANCE.json').write_bytes(raw({'status':'passed-technical-candidate','siteLocale':locale,'manifestSha256':digest(output/'manifest.json'),'bindingsSha256':digest(output/'bindings.json'),'verificationMode':MODE,'runtime':'not-run','visual':'not-run','editorial':'pending-coordinator-evidence'}))
    archive.parent.mkdir(parents=True,exist_ok=True)
    names=sorted(['files/'+r['path'] for r in m['files']]+['manifest.json','bindings.json','ACCEPTANCE.json'])
    with ZipFile(archive,'x',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for name in names:
            info=ZipInfo(name,date_time=(2026,10,17,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,(output/name).read_bytes())
    result=verify(locale,relative(output),relative(archive))
    receipt=archive.with_name(archive.name+'.receipt.json');content=raw(dict(result,verificationMode=MODE));receipt.write_bytes(content)
    if receipt.read_bytes()!=content:raise ValueError('UI derivative package receipt write failed')
    return {'build':relative(output),'archive':relative(archive),'receipt':relative(receipt)}
def control(output_name):
    old='build/multilingual-delivery/vi/native-visual-repair-20261017-02';old_zip='build/multilingual-delivery/vi/OMORI-vi-visual-repair-20261017-02.zip'
    full='build/multilingual-delivery/vi/native-visual-repair-20261017-06';full_zip='build/multilingual-delivery/vi/OMORI-vi-visual-repair-20261017-06.zip'
    b,z,m,previous,i=parent('vi',old,old_zip);f,fm=build_checkpoint(ROOT,'vi',full);archive_readback(f,fm,inside(ROOT,full_zip))
    expected_boot=crypt((ROOT/UI).read_bytes()+b'\n'+previous[i:])
    for row in fm['files']:
        wanted=expected_boot if row['path']==BOOT else (b/'files'/row['path']).read_bytes()
        if (f/'files'/row['path']).read_bytes()!=wanted:raise ValueError('Full native positive control differs beyond UI prefix')
    if m['inputs']!=fm['inputs'] or m['fonts']!=fm['fonts'] or m['config']!=fm['config'] or (b/'bindings.json').read_bytes()!=(f/'bindings.json').read_bytes():raise ValueError('Full positive control changed authored/font/binding inputs')
    review=ROOT/'runtime/visual-qa/20261017-mari-vi-09/vi/visual-review.json';picture=ROOT/'dist/screenshots/20261017-native/vi-03-mari-quests.png';native=ROOT/'runtime/visual-qa/20261017-mari-vi-09/vi-installation.json'
    installed=load(native);cap=load(review.parent/'mari-capture.json');stopped=load(review.parent/'stopped.json');base=load(ROOT/'runtime/visual-qa/20261017-native/baseline.json')
    if load(review)['status']!='pass' or load(review)['sha256']!=digest(picture) or installed['packageArchiveSha256']!=digest(ROOT/full_zip) or installed['locale']!='vi' or installed['runtimeChannel']!='en' or installed['fileHashes']!={r['path']:r['sha256'] for r in fm['files']} or cap['sha256']!=digest(picture) or stopped['protectedFiles']!=base['saves'] or load(review.parent.parent/'russian-level-restoration.json')['status']!='verified':raise ValueError('Native Vietnamese control not accepted')
    result={'status':'passed-full-build-and-native-control','currentPins':pins(),'fullBuild':full,'fullManifestSha256':digest(f/'manifest.json'),'nativeReview':relative(review),'nativeReviewSha256':digest(review),'nativeImage':relative(picture),'nativeImageSha256':digest(picture),'nativeResourcesCompared':len(fm['files']),'changedResources':[BOOT]}
    output=inside(ROOT,output_name)
    if output.exists():raise ValueError('Preserve existing positive-control receipt')
    output.write_bytes(raw(result));print('FULL_AND_NATIVE_CONTROL',len(fm['files']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['control','build','verify']);p.add_argument('--output');p.add_argument('--locale');p.add_argument('--parent-build');p.add_argument('--parent-archive');p.add_argument('--control');p.add_argument('--archive');p.add_argument('--build');p.add_argument('--receipt');a=p.parse_args()
    if a.command=='control':control(a.output)
    elif a.command=='verify':print(json.dumps(verify(a.locale,a.build,a.archive,a.receipt)))
    else:print(json.dumps(create(a.locale,a.parent_build,a.parent_archive,a.control,a.output,a.archive)))
