"""Rebuild only technical presentation resources; preserve authored checkpoint inputs."""
import sys,json,subprocess,time,argparse,re
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from native_checkpoint import package_once,digest
parser=argparse.ArgumentParser();parser.add_argument('--revision',default='02');parser.add_argument('--reuse-fonts',action='store_true');parser.add_argument('locales',nargs='+');args=parser.parse_args()
assert re.fullmatch(r'[0-9]{2}',args.revision);revision=args.revision
OUT=ROOT/'diagnostics/native-artifacts-20261017';MAP=OUT/('repaired-packages-'+revision+'.json')
selected=args.locales;mapping=json.loads(MAP.read_text()) if MAP.exists() else {}
for code in selected:
 assert code in ['es','es-419','pt-BR','de','fr','tr','zh-TW','pl','it','th','vi','id','uk','ar','cs','hu','nl','fa','ro','hi','fil','el','bg','sr','sw','he']
 original=ROOT/'dist'/code/('OMORI-'+code+'-8879120.zip')
 with ZipFile(original) as z:old=json.loads(z.read('manifest.json'))
 build=ROOT/'build/multilingual-delivery'/code/('native-visual-repair-20261017-'+revision);archive=build.with_name('OMORI-'+code+'-visual-repair-20261017-'+revision+'.zip')
 if code in mapping:
  result=package_once(ROOT,code,str(build.relative_to(ROOT)),str(archive.relative_to(ROOT)));print('REUSED',code,flush=True);continue
 assert not build.exists(),'Reconcile existing candidate before rerun: '+str(build)
 cmd=[sys.executable,'-B',str(ROOT/'tools/multilingual/delivery/native_delivery.py'),'--root',str(ROOT),'--locale',code,'build','--plaintext',str(ROOT/old['inputs']['plaintext']),'--output',str(build)]
 if args.reuse_fonts:cmd+=['--reuse-font-build',str(ROOT/'build/multilingual-delivery'/code/'native-visual-repair-20261017-02')]
 if old.get('imageInputs'):cmd+=['--images',str(ROOT/old['imageInputs']['packet']['path'])]
 started=time.time();log=OUT/(code+'-build-'+revision+'.log')
 with log.open('xb') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 new=json.loads((build/'manifest.json').read_text());assert new['inputs']==old['inputs'],'Authored input bindings changed; stop before accepting package'
 result=package_once(ROOT,code,str(build.relative_to(ROOT)),str(archive.relative_to(ROOT)))
 mapping[code]={'build':str(build.relative_to(ROOT)),'archive':str(archive.relative_to(ROOT)),'receipt':str(Path(result['receipt']).relative_to(ROOT))}
 MAP.write_text(json.dumps(mapping,indent=2)+'\n')
 (OUT/(code+'-repair-build-binding-'+revision+'.json')).write_text(json.dumps({'locale':code,'oldArchiveSha256':digest(original),'newArchiveSha256':digest(archive),'buildManifestSha256':digest(build/'manifest.json'),'authoredInputsUnchanged':True,'elapsedSeconds':round(time.time()-started,2),'verification':result['verificationMode']},indent=2)+'\n')
 print('BUILT',code,'seconds',round(time.time()-started,1),flush=True)
