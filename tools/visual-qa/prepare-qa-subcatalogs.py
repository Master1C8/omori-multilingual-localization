"""Derive byte-identical two-locale QA catalogs; retain the full mandatory list.
No package rebuild, installer change, installed-file write or gameplay occurs.
"""
import argparse,copy,gzip,hashlib,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('locales',nargs='+');a=p.parse_args()
root=Path(__file__).resolve().parents[2];parent=a.catalog.resolve();out=a.output.resolve();sha=lambda b:hashlib.sha256(b).hexdigest()
assert parent.is_relative_to(root/'build/installer') and out.is_relative_to(root/'build/installer') and not out.exists()
raw=(parent/'catalog.json').read_bytes();receipt=json.loads((parent/'payload-receipt.json').read_text());assert sha(raw)==receipt['catalogSha256'];full=json.loads(raw)
base=json.loads((root/'runtime/visual-qa/20261017-native/baseline.json').read_text());assert set(base['requiredLocales'])<={l['code'] for l in full['locales']}
assert a.locales and len(a.locales)==len(set(a.locales)) and 'ru' not in a.locales
verified=set();out.mkdir();mapping={}
for code in a.locales:
 selected=[next(l for l in full['locales'] if l['code']==c) for c in ['ru',code]]
 objects={f['object'] for l in selected for f in l['files'].values()};paths={n for l in selected for n in l['files']}
 d=copy.deepcopy(full);d['locales']=selected;d['objects']={k:full['objects'][k] for k in sorted(objects)};d['originals']={k:v for k,v in full['originals'].items() if k in paths}
 folder=out/code;folder.mkdir();(folder/'objects').mkdir()
 for k in objects:
  source=parent/'objects'/k
  if k not in verified:
   packed=source.read_bytes();metadata=full['objects'][k];plain=gzip.decompress(packed)
   assert len(packed)==metadata['bytes'] and sha(packed)==metadata['sha256'] and len(plain)==metadata['unpackedBytes'] and sha(plain)==k
   verified.add(k)
  os.link(source,folder/'objects'/k)
 content=(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode();(folder/'catalog.json').write_bytes(content)
 proof={'kind':'selected-locale-native-QA-only','catalogSha256':sha(content),'parentCatalog':str(parent),'parentCatalogSha256':sha(raw),'locales':['ru',code],'mandatoryLocales':base['requiredLocales'],'objects':len(objects),'localeRowsUnchanged':True,'originalResourcesUnchanged':True,'packageArchivesUnchanged':True,'notAReleaseCatalog':True}
 (folder/'payload-receipt.json').write_text(json.dumps(proof,indent=2)+'\n');mapping[code]=str(folder)
(out/'catalog-map.json').write_text(json.dumps(mapping,indent=2)+'\n');print('Verified',len(mapping),'QA catalogs; mandatory locale list retained:',len(base['requiredLocales']))
