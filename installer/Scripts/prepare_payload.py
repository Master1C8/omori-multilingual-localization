#!/usr/bin/env python3
"""Repack byte-verified OMORI overlays into deduplicated compressed native objects.
No translation generation or native recompilation. The installed bytes must match ZIPs.
"""
import argparse,base64,gzip,hashlib,json,pathlib,re,sys,os
from zipfile import ZipFile
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
ROOT=pathlib.Path(__file__).resolve().parents[2]
KEY=b'6bdb2e585882fbd48826ef9cffd4c511'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text())
def safe(n):
 if not re.fullmatch(r'(?:data|js|fonts|languages/en)/[^\\:]+|index\.html',n) or any(x in ('','.','..') for x in n.split('/')):raise ValueError('Unsafe path '+n)
 return n
def main():
 global ROOT
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--root',type=pathlib.Path,default=ROOT);ap.add_argument('--allow-pending',action='store_true');ap.add_argument('--reuse',type=pathlib.Path,help='Reuse verified immutable compressed objects from a completed payload');ap.add_argument('--package-overrides',type=pathlib.Path,help='Explicit non-Russian locale checkpoint build/archive/receipt map');args=ap.parse_args()
 ROOT=args.root.resolve()
 reuse={}
 if args.reuse:
  receipt=load(args.reuse/'payload-receipt.json');raw=(args.reuse/'catalog.json').read_bytes()
  if sha(raw)!=receipt['catalogSha256']:raise ValueError('Reuse catalog checksum mismatch')
  previous=json.loads(raw)
  if previous['game']!='OMORI' or previous['sourceBuild']!='8879120' or previous['format']!='gzip-plaintext-native-ctr-v1':raise ValueError('Incompatible reused payload')
  reuse=previous['objects']
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'objects').mkdir()
 run=pathlib.Path(load(ROOT/'runtime/cli-localization/current.json')['run']);state=load(run/'state.json')
 names={'ru':'Русский','es':'Español','es-419':'Español latinoamericano','pt-BR':'Português (Brasil)','de':'Deutsch','fr':'Français','tr':'Türkçe','zh-TW':'繁體中文','pl':'Polski','it':'Italiano','th':'ไทย','vi':'Tiếng Việt','id':'Bahasa Indonesia','uk':'Українська','ar':'العربية','cs':'Čeština','hu':'Magyar','nl':'Nederlands','fa':'فارسی','ro':'Română','hi':'हिन्दी','fil':'Filipino','el':'Ελληνικά','bg':'Български','sr':'Српски','sw':'Kiswahili','he':'עברית'}
 # Presentation labels reference existing locale codes; this is not a language catalog.
 originals={r['asset']:r['encryptedSha256'] for r in load(ROOT/'source/research-8879120-02/manifest.json')['assets']}
 originals.update({r['asset']:r['rawSha256'] for r in load(ROOT/'source/inventory-8879120-01/structured-assets.json')})
 originals.update({r['asset']:r['rawSha256'] for r in load(ROOT/'source/inventory-8879120-01/scripts.json')['scripts']})
 originals['js/plugins.js']=load(ROOT/'source/research-8879120-02/manifest.json')['pluginConfigurationSha256']
 originals['index.html']='a977a14387ec968c183584f7ad2984bd73475cb9bca7bb3504b917a67db7557c'
 # Native-verified level-field repair; historical payload folders remain immutable.
 packages=[('ru',ROOT/'dist/ru-direct-level-fix-20261017-01/omori-ru-direct-8879120.zip')]
 if sha(packages[0][1].read_bytes())!='614605b33be71241f2e604e61910c6738b51e9d8c564f332adfc685f3cf7704c':raise ValueError('Russian checkpoint archive changed')
 pending=[]
 for loc,v in state['locales'].items():
  status=v['status'];hold=v.get('workflow',{}).get('queueHold',{})
  if status=='blocked' and hold.get('reason','').startswith('Owner pause remains active for this locale;'):status=hold['status']
  if status not in ('packaged-awaiting-review','local-scope-complete'):
   pending.append(loc);continue
  cp=v['workflow']['machinePackageCheckpoint'];p=ROOT/cp['deliveredArchive'];expected=cp['archive']['sha256']
  if sha(p.read_bytes())!=expected:raise ValueError('Archive changed '+loc)
  packages.append((loc,p))
 if pending and not args.allow_pending:raise ValueError('Pending packages: '+str(pending))
 if args.package_overrides:
  sys.path.insert(0,str(ROOT/'tools'))
  from native_checkpoint import verify_checkpoint
  overrides=load(args.package_overrides)
  known={code for code,_ in packages}-{'ru'}
  if not isinstance(overrides,dict) or not set(overrides)<=known:raise ValueError('Unknown, unavailable or protected locale package override')
  selected={}
  for code,row in overrides.items():
   if set(row)!={'build','archive','receipt'}:raise ValueError('Incomplete locale package override')
   receipt_path=(ROOT/row['receipt']).resolve()
   if not receipt_path.is_relative_to(ROOT/'build/multilingual-delivery'):raise ValueError('Package receipt outside native build scope')
   if load(receipt_path).get('verificationMode')=='native-ui-prefix-derivative-v1':
    sys.path.insert(0,str(ROOT/'tools/visual-qa'))
    from ui_derivative import verify as verify_ui_derivative
    verify_ui_derivative(code,row['build'],row['archive'],row['receipt'])
   else:verify_checkpoint(ROOT,code,row['build'],row['archive'],row['receipt'])
   selected[code]=ROOT/row['archive']
  packages=[(code,selected.get(code,path)) for code,path in packages]
 locales=[];objects={};licenses={};readback=0
 for loc,p in packages:
  print('packing',loc,flush=True)
  with ZipFile(p) as z:
   if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP entry')
   m=json.loads(z.read('manifest.json'));rows=m['files'];files={}
   if m['sourceBuild']!='8879120' or (loc!='ru' and m.get('siteLocale')!=loc):raise ValueError('Wrong game build or locale')
   if len({r['path'].casefold() for r in rows})!=len(rows):raise ValueError('Case-colliding paths')
   if {n for n in z.namelist() if n.startswith('files/') and not n.endswith('/')}!={'files/'+r['path'] for r in rows}:raise ValueError('Unexpected archive payload')
   for r in rows:
    n=safe(r['path']);raw=z.read('files/'+n)
    if sha(raw)!=r['sha256'] or len(raw)!=r['bytes']:raise ValueError('ZIP byte mismatch '+n)
    if n.startswith('fonts/') and n.endswith('.txt'):
     licenses[sha(raw)]={'bytes':raw,'origins':licenses.get(sha(raw),{}).get('origins',[])+[loc+':'+n]}
    encrypted=pathlib.PurePosixPath(n).suffix in ('.KEL','.HERO','.PLUTO','.OMORI')
    iv=raw[:16] if encrypted else b''
    if encrypted:
     worker=Cipher(algorithms.AES(KEY),modes.CTR(iv)).decryptor();plain=worker.update(raw[16:])+worker.finalize()
     worker=Cipher(algorithms.AES(KEY),modes.CTR(iv)).encryptor();assert iv+worker.update(plain)+worker.finalize()==raw
    else:plain=raw
    obj=sha(plain)
    if obj not in objects:
     if obj in reuse:
      metadata=reuse[obj];old=args.reuse/'objects'/obj;packed=old.read_bytes()
      if len(packed)!=metadata['bytes'] or sha(packed)!=metadata['sha256'] or metadata['unpackedBytes']!=len(plain) or gzip.decompress(packed)!=plain:raise ValueError('Reused object differs '+obj)
      os.link(old,out/'objects'/obj);objects[obj]=metadata
     else:
      packed=gzip.compress(plain,compresslevel=9,mtime=0);(out/'objects'/obj).write_bytes(packed);objects[obj]={'sha256':sha(packed),'bytes':len(packed),'unpackedBytes':len(plain)}
    files[n]={'object':obj,'sha256':sha(raw),'bytes':len(raw),'iv':base64.b64encode(iv).decode()}
    readback+=1
   locales.append({'code':loc,'name':names[loc],'files':files,'archiveSha256':sha(p.read_bytes()),'reviewStatus':'pending-full-review' if loc=='ru' or state['locales'][loc]['status']!='local-scope-complete' else 'accepted'})
 catalog={'schemaVersion':1,'game':'OMORI','steamAppID':'1150690','sourceBuild':'8879120','version':'1.0.0','runtimeCode':'en','originals':{k:v for k,v in originals.items() if any(k in l['files'] for l in locales)},'objects':objects,'locales':locales,'pendingLocales':pending,'runtimeQA':'not-run','format':'gzip-plaintext-native-ctr-v1'}
 raw=(json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode();(out/'catalog.json').write_bytes(raw)
 (out/'Licenses').mkdir()
 for key,row in licenses.items():(out/'Licenses'/(key+'.txt')).write_bytes(row['bytes'])
 (out/'Licenses/index.json').write_text(json.dumps({k:r['origins'] for k,r in licenses.items()},indent=2)+'\n')
 meta={'catalogSha256':sha(raw),'compressedBytes':sum(v['bytes'] for v in objects.values()),'objects':len(objects),'locales':[l['code'] for l in locales],'verifiedDeliveredFiles':readback,'pendingLocales':pending}
 (out/'payload-receipt.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
