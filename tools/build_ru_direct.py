#!/usr/bin/env python3
"""Build a pinned native-file Russian overlay without a third-party loader."""
import argparse,hashlib,json,gzip
from pathlib import Path
from zipfile import ZipFile
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
from script_resource_adapter import original_resource,parse_config
ROOT=Path(__file__).resolve().parents[1]
GAME=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
OUT=ROOT/'dist/ru-direct-8879120-2026-10-14-01'
ZIP=ROOT/'dist/ru-text-8879120-2026-10-14-11/omori-ru-text-8879120.zip'
DISPLAY=ROOT/'build/ru/display-2026-10-14-19'
COMBINED=ROOT/'build/ru/combined-2026-10-14-10'
def sha(b):return hashlib.sha256(b).hexdigest()
def encrypt(b):
    iv=hashlib.sha256(b).digest()[:16];enc=Cipher(algorithms.AES(b'6bdb2e585882fbd48826ef9cffd4c511'),modes.CTR(iv)).encryptor()
    return iv+enc.update(b)+enc.finalize()
def main():
    global OUT,DISPLAY,COMBINED
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);ap.add_argument('--display',type=Path,default=DISPLAY);ap.add_argument('--combined',type=Path,default=COMBINED);a=ap.parse_args();OUT=a.output.resolve();DISPLAY=a.display.resolve();COMBINED=a.combined.resolve();assert all(p.is_relative_to(ROOT) for p in [OUT,DISPLAY,COMBINED])
    assert not OUT.exists(),'Preserve prior direct package';assert sha(ZIP.read_bytes())=='a6fc962f793647e2006e97877a831fc56e8d797731dd9125592772d2fac2600e'
    combined=json.loads((COMBINED/'receipt.json').read_text());display=json.loads((DISPLAY/'receipt.json').read_text())
    assert display['combinedReceiptSha256']==sha((COMBINED/'receipt.json').read_bytes()),'Display/combined input mismatch'
    resources={r['originalAsset']:r for r in combined['resources']}
    for r in resources.values():assert sha((COMBINED/r['output']).read_bytes())==r['rawSha256']
    for entry,h in display['compiledOutputs'].items():assert sha((DISPLAY/entry).read_bytes())==h
    native={}
    for p in GAME.rglob('*'):
        if p.is_file() and p.parts[len(GAME.parts)] not in ['mods','modloader']:
            key=str(p.relative_to(GAME)).casefold();assert key not in native;native[key]=str(p.relative_to(GAME))
    items={};plain={}
    with ZipFile(ZIP) as z:
        prefix='omori-ru-text-8879120/';proof=json.loads(z.read(prefix+'evidence/package-inputs.json'));manifest=json.loads(z.read(prefix+'mod.json'))
        sources={r['file']:r['asset'] for r in proof['resourceSources']}
        for entry,destination in proof['injections'].items():
            if entry.startswith('fonts/'):path=entry;data=z.read(prefix+entry)
            else:
                path=native.get(destination.casefold())
                if path is None:
                    assert entry in ['plugins/OmoriRu_Bootstrap.js','plugins/OmoriRu_Install.js'];path='js/plugins/'+Path(entry).stem+'.OMORI'
                if entry in display['compiledOutputs']:raw=(DISPLAY/entry).read_bytes()
                else:
                    assert entry in sources,'Unbound native resource: '+entry
                    raw=(COMBINED/resources[sources[entry]]['output']).read_bytes()
                data=encrypt(raw);plain[path]=sha(raw)
            assert path not in items;items[path]=data
    raw,plugins=original_resource(ROOT,'js/plugins.js')
    assert len(plugins)==173 and not any(p['name'].lower().startswith('omoriru') for p in plugins)
    baseline=[dict(p) for p in plugins]
    plugins=[{'name':'OmoriRu_Bootstrap','status':True,'description':'Russian display bootstrap','parameters':{}}]+plugins+[{'name':'OmoriRu_Install','status':True,'description':'Russian display installation','parameters':{}}]
    assert plugins[1:-1]==baseline
    items['js/plugins.js']=('var $plugins =\n'+json.dumps(plugins,ensure_ascii=False,indent=2)+';\n').encode()
    original_index=ROOT/'diagnostics/ru-launch-2026-10-14/backup/index.html'
    assert original_index.is_file();items['index.html']=original_index.read_bytes()
    OUT.mkdir();files=[]
    for path,data in sorted(items.items()):
        p=OUT/'files'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        files.append({'path':path,'sha256':sha(data),'plaintextSha256':plain.get(path),'bytes':len(data)})
    doc={'status':'built-native-overlay','sourceBuild':'8879120','sourceZipSha256':sha(ZIP.read_bytes()),'combinedReceiptSha256':sha((COMBINED/'receipt.json').read_bytes()),'displayReceiptSha256':sha((DISPLAY/'receipt.json').read_bytes()),'sourceExtensionSha256':sha((ROOT/'source/native-yaml-8879120-01/manifest.json').read_bytes()),'nativeYamlAuthorSha256':sha((ROOT/'translation/ru/native-yaml-supplement.json').read_bytes()),'recipeSha256':sha(Path(__file__).read_bytes()),'files':files,'nativePlugins':173,'injectedPlugins':2,'runtime':'pending','loader':'none; original index and native encrypted resource loading','translationChange':'Combined and display receipts supply every resource; 19 recovered YAML choice captions translated as ДА/НЕТ. Legacy ZIP supplies verified destinations and unchanged fonts only.'}
    (OUT/'manifest.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({'files':len(files),'bytes':sum(r['bytes'] for r in files),'output':str(OUT)}))
if __name__=='__main__':main()
