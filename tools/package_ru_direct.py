#!/usr/bin/env python3
"""Deterministically archive and verify the complete native-file overlay."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ap=argparse.ArgumentParser();ap.add_argument('build',type=Path);a=ap.parse_args();manifest=json.loads((a.build/'manifest.json').read_text());out=a.build/'omori-ru-direct-8879120.zip';assert not out.exists()
with ZipFile(out,'w',compression=ZIP_DEFLATED,compresslevel=1) as z:
 for r in manifest['files']:
  p=a.build/'files'/r['path'];raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];i=ZipInfo('files/'+r['path'],date_time=(2026,10,14,0,0,0));i.compress_type=ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,raw)
 i=ZipInfo('manifest.json',date_time=(2026,10,14,0,0,0));i.compress_type=ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,(a.build/'manifest.json').read_bytes())
with ZipFile(out) as z:
 assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==len(manifest['files'])+1
 for r in manifest['files']:assert hashlib.sha256(z.read('files/'+r['path'])).hexdigest()==r['sha256']
receipt={'status':'archive-and-all-file-readback-verified','path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'entries':len(manifest['files'])+1,'buildManifestSha256':hashlib.sha256((a.build/'manifest.json').read_bytes()).hexdigest(),'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(a.build/'package-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
