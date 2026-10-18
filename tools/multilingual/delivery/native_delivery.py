#!/usr/bin/env python3
"""Explicit-locale source-bound OMORI encrypted native overlay candidate builder."""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

HERE=Path(__file__).resolve().parent
TOOLS=HERE.parents[1]
sys.path[:0]=[str(HERE),str(TOOLS/'multilingual'),str(TOOLS)]
from source_prepare import strict_json, sha, save_json
from locale_tools import Context, unique, validate_entries, mapping_row, assemble
from compiler import compile_resources
from fonts import prepare as prepare_fonts, script_font_dependencies, GAME
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

INVENTORY='4faf2a7b0bc682febcbcb03fe67ea7c2cad1ead21723ba5ae47c6f33d265214d'
DATA='source/multilingual/shared-8879120-03'
EXCLUDED={'en','zh','ja','ko','ru'}
_PREFLIGHT_CACHE={}


def locale_config(locale):
    configs=strict_json((HERE/'locales.json').read_bytes())['locales']
    if locale in EXCLUDED or locale not in configs:raise ValueError('Unknown or excluded target locale: '+str(locale))
    return copy.deepcopy(configs[locale])


def safe_relative(name):
    p=PurePosixPath(name)
    if not isinstance(name,str) or not name or '\\' in name or p.is_absolute() or any(x in ['.','..',''] for x in name.split('/')) or ':' in name:
        raise ValueError('Unsafe relative path: '+str(name))
    return p


def inside(path, base, new=False):
    path,base=Path(path).absolute(),Path(base).resolve()
    resolved=path.resolve()
    if not resolved.is_relative_to(base) or resolved==base:raise ValueError('Path outside authorized delivery scope: '+str(path))
    for part in [path,*path.parents]:
        if part==base:break
        if part.is_symlink():raise ValueError('Symlink path forbidden: '+str(part))
    if new and path.exists():raise ValueError('Preserve existing immutable revision: '+str(path))
    return resolved


def crypt(raw, decrypt=False):
    key=b'6bdb2e585882fbd48826ef9cffd4c511'
    if decrypt:
        if len(raw)<16:raise ValueError('Truncated native ciphertext')
        iv,raw=raw[:16],raw[16:]
    else:iv=hashlib.sha256(raw).digest()[:16]
    worker=Cipher(algorithms.AES(key),modes.CTR(iv)).decryptor() if decrypt else Cipher(algorithms.AES(key),modes.CTR(iv)).encryptor()
    result=worker.update(raw)+worker.finalize()
    return result if decrypt else iv+result


def recipe_dependencies(root):
    # Include the actual imported Python closure and JS helpers, not only this launcher.
    paths={p.resolve() for p in HERE.iterdir() if p.is_file() and p.suffix in ['.py','.js','.json','.cjs']}
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            p=Path(name).resolve()
            if p.is_relative_to(TOOLS) and p.suffix=='.py':paths.add(p)
    paths.update(TOOLS/p for p in ['display_calls.cjs','multilingual/source_literal_values.cjs','multilingual/native_yaml.cjs','multilingual/renderer-matrix.json'])
    paths.update(root/name for name in script_font_dependencies(root))
    return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(paths) if p.is_file()}


def mapping_gate(locale, receipt, mapping, expected, mapping_digest):
    unique(mapping['entries'])
    if mapping.get('siteLocale')!=locale or mapping.get('inventorySha256')!=INVENTORY:
        raise ValueError('Wrong-locale/source display mappings')
    if mapping.get('entries')!=expected or receipt.get('displayMappings')!=len(expected) or receipt.get('displayMappingsSha256')!=mapping_digest:
        raise ValueError('Incomplete or changed authored display mappings')


def author_gate(authors, entries):
    if authors!=entries:raise ValueError('Stale author receipt: current authored batches differ from plaintext receipt')


def input_state(root, locale, plaintext, full=True):
    config=locale_config(locale) # Always reject before writes, including verify/package.
    plaintext=inside(plaintext,root/'runtime/multilingual/locales'/locale)
    ctx=Context(root,root/DATA,locale)
    for field,shared_field in [('siteLocale','siteLocale'),('script','script'),('direction','direction'),('nativeChannel','nativeResourceChannel')]:
        if config[field]!=ctx.config[shared_field]:raise ValueError('Locale renderer configuration mismatch: '+field)
    if ctx.inventory_sha!=INVENTORY:raise ValueError('Stale source inventory identity')
    receipt_path=plaintext/'receipt.json';receipt=strict_json(receipt_path.read_bytes())
    if receipt.get('siteLocale')!=locale or receipt.get('inventorySha256')!=INVENTORY or receipt.get('status')!='passed-plaintext':raise ValueError('Plaintext receipt locale/source/status mismatch')
    entries=unique(receipt['entries'])
    if receipt.get('entryIds')!=list(entries):raise ValueError('Plaintext receipt entry IDs/order mismatch')
    if set(ctx.by_id)-set(entries)-set(ctx.retained) or set(entries)-set(ctx.by_id):raise ValueError('Incomplete authored source coverage')
    authors={}; author_hashes={}
    batch_dir=root/'translation'/locale/'batches'
    for path in sorted(batch_dir.glob('*.json')):
        doc=strict_json(path.read_bytes())
        if doc.get('siteLocale')!=locale or doc.get('sourceLocale')!='en' or doc.get('inventorySha256')!=INVENTORY:raise ValueError('Author batch locale/source mismatch: '+str(path))
        author_hashes[str(path.relative_to(root))]=sha(path.read_bytes())
        for e in doc['entries']:
            if e['id'] in authors:raise ValueError('Duplicate authored ID: '+e['id'])
            if e.get('immediateEdit') is not True:raise ValueError('Missing immediate edit evidence')
            authors[e['id']]=e
    author_gate(authors,entries)
    labels={e['encodedPayload']['targetNamebox'] for e in entries.values() if 'encodedPayload' in e}
    if len(labels)!=1:raise ValueError('Encoded namebox binding absent/ambiguous')
    pairs=validate_entries(ctx,list(entries.values()),next(iter(labels)))
    mapping_path=plaintext/'display-mappings.json';mapping=strict_json(mapping_path.read_bytes())
    expected=[mapping_row(u,e) for u,e in pairs if u['role']=='visible-display-mapping']
    mapping_gate(locale,receipt,mapping,expected,sha(mapping_path.read_bytes()))
    files=receipt['files'];unique(files,'path');unique(files,'originalAsset')
    for row in files:
        safe_relative(row['path']);safe_relative(row['originalAsset'])
        path=inside(plaintext/row['path'],plaintext)
        if path.is_symlink() or sha(path.read_bytes())!=row['sha256']:raise ValueError('Stale plaintext resource receipt: '+row['path'])
    if {str(p.relative_to(plaintext)) for p in (plaintext/'resources').rglob('*') if p.is_file()}!={r['path'] for r in files}:raise ValueError('Plaintext resource entry set mismatch')
    module=GAME/'js/libs/js-yaml-master'
    for name,h in ctx.manifest['nativeParserPins'].items():
        if sha((GAME/name).read_bytes())!=h:raise ValueError('Native YAML parser dependency changed: '+name)
    for name,digest in ctx.manifest['inputHashes'].items():
        if sha((root/name).read_bytes())!=digest:raise ValueError('Shared original dependency changed: '+name)
    fingerprint=sha(serialized({'source':ctx.manifest,'inventory':ctx.inventory_sha,'authors':author_hashes,
        'receipt':sha(receipt_path.read_bytes()),'files':files,'mappings':sha(mapping_path.read_bytes()),'recipe':recipe_dependencies(root)}))
    cache_key=(str(root),locale,str(plaintext),fingerprint)
    if full and cache_key not in _PREFLIGHT_CACHE:
        assemble(ctx,pairs,plaintext,module,verify_only=True)
        _PREFLIGHT_CACHE[cache_key]=True
    pinned={'plaintext':str(plaintext.relative_to(root)),'plaintextReceiptSha256':sha(receipt_path.read_bytes()),
            'mappingSha256':sha(mapping_path.read_bytes()),'authorFiles':author_hashes,'inventorySha256':ctx.inventory_sha,
            'sourceVerificationSha256':sha((root/DATA/'verification.json').read_bytes())}
    return ctx,pairs,expected,config,pinned


def expected_payload(ctx,pairs,mapping,config,font_checkpoint=None):
    if font_checkpoint is None:fonts,probes,font_evidence=prepare_fonts(ctx,pairs,config)
    else:
        from font_checkpoint import reuse
        pinned=input_state(ctx.root,ctx.locale,ctx.root/font_checkpoint['plaintext'],full=False)[-1]
        fonts,probes,font_evidence=reuse(ctx,pinned,config,font_checkpoint)
    native,proof=compile_resources(ctx,pairs,mapping,config,probes)
    # Parse the actual newly emitted YAML with the game's retained parser.
    from prepare_source import native_parse, native_typed
    import yaml
    requests=[{'asset':a,'text':b.decode()} for a,b in native.items() if a in ctx.native]
    for row in native_parse(GAME/'js/libs/js-yaml-master',requests):
        tree=yaml.safe_load(native[row['asset']])
        if native_typed(tree,row['value'])!=tree:raise ValueError('Native emitted YAML typed readback mismatch')
    # Syntax validation batches all delivered plugins and protected core overrides.
    requests=[{'asset':a,'source':b.decode(),'rawSha256':sha(b)} for a,b in native.items() if a.startswith('js/')]
    run=subprocess.run(['node','--expose-internals',str(TOOLS/'multilingual/source_literal_values.cjs')],input=json.dumps(requests),text=True,capture_output=True)
    if run.returncode or strict_json(run.stdout)['errors']:raise ValueError('Compiled native JavaScript parse failure: '+run.stderr[-500:])
    payload={};file_rows=[]
    for a,raw in sorted((native|fonts).items()):
        safe_relative(a)
        encrypted=a.startswith(('data/','languages/','js/plugins/'))
        if encrypted and not a.endswith(('.KEL','.HERO','.OMORI','.PLUTO')):raise ValueError('Unsupported native resource extension: '+a)
        data=crypt(raw) if encrypted else raw
        if encrypted and crypt(data,True)!=raw:raise ValueError('Native codec roundtrip failed')
        payload['files/'+a]=data
        file_rows.append({'path':a,'sha256':sha(data),'plaintextSha256':sha(raw),'bytes':len(data),'encrypted':encrypted})
    return payload,file_rows,proof,font_evidence


def check_consumers(root, payload, proof, mapping):
    resources={}
    for name,raw in payload.items():
        if name.startswith('files/data/') and name.endswith('.KEL'):
            resources[name[len('files/'):]]=strict_json(crypt(raw,True))
    # Unchanged resources are deliberately absent from the overlay. Their pinned original
    # records provide the consumer context, while delivered overrides are always decrypted.
    from script_resource_adapter import original_resource
    for asset in {b['asset'] for b in proof['variables']}:
        if asset not in resources:resources[asset]=original_resource(root,asset)[1]
    for row in mapping:
        if 'path' in row and row['asset'] not in resources:
            resources[row['asset']]=original_resource(root,row['asset'])[1]
    request={'resources':resources,'proof':proof,'mapping':mapping}
    result=subprocess.run(['node',str(HERE/'check_consumers.cjs')],input=json.dumps(request),text=True,capture_output=True)
    if result.returncode:raise ValueError('Decrypted consumer binding check failed: '+result.stderr[-1800:])
    return strict_json(result.stdout)


def write_new(path, raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw)


def serialized(doc):return (json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode()


def image_payload(root, locale, packet):
    from image_resources import load
    from script_resource_adapter import original_resource
    system=original_resource(root,'data/System.KEL')[1]
    key=bytes.fromhex(system['encryptionKey'])
    return (*load(root,locale,packet,GAME,key),key)


def merge_images(payload, rows, image_files, image_rows):
    if set(payload) & set(image_files):raise ValueError('Image destination collides with native resource')
    payload.update(image_files)
    rows.extend(image_rows)
    rows.sort(key=lambda row:row['path'])


def build(root,locale,plaintext,output,fail_after=None,images=None,reuse_font_build=None):
    locale_config(locale)
    output=inside(output,root/'build/multilingual-delivery',new=True)
    ctx,pairs,mapping,config,pinned=input_state(root,locale,plaintext)
    font_checkpoint=None
    if reuse_font_build is not None:
        from font_checkpoint import checkpoint
        font_checkpoint=checkpoint(root,reuse_font_build)|{'plaintext':pinned['plaintext']}
    payload,rows,proof,font_evidence=expected_payload(ctx,pairs,mapping,config,font_checkpoint)
    image_pins,image_key=None,None
    if images is not None:
        image_files,image_rows,image_pins,image_key=image_payload(root,locale,images)
        merge_images(payload,rows,image_files,image_rows)
    consumer_result=check_consumers(root,payload,proof,mapping)
    deps=recipe_dependencies(root)
    if input_state(root,locale,plaintext,full=False)[-1]!=pinned:raise ValueError('Source/authors changed during compilation')
    if images is not None and image_payload(root,locale,images)[2]!=image_pins:raise ValueError('Image inputs changed during compilation')
    output.mkdir(parents=True)
    # There is deliberately no cross-file transaction. Acceptance is the LAST write.
    write_new(output/'INCOMPLETE.json',serialized({'status':'incomplete','siteLocale':locale,'acceptance':False,'failureSemantics':'An interrupted revision must be preserved. Use a new output path.'}))
    for i,(name,raw) in enumerate(sorted(payload.items()),1):
        write_new(output/name,raw)
        if fail_after is not None and i==fail_after:raise ValueError('Injected between-write failure; revision explicitly incomplete')
    proof_raw=serialized(proof);write_new(output/'bindings.json',proof_raw)
    manifest={'schemaVersion':1,'status':'technical-candidate','siteLocale':locale,'sourceBuild':'8879120','sourceLocale':'en',
              'inputs':pinned,'recipeDependencies':deps,'config':config,'files':rows,'bindingsSha256':sha(proof_raw),
              'authoredEntries':len(pairs),'visibleUnits':len(ctx.units)-len(ctx.retained),'technicalRetentions':len(ctx.retained),
              'displayMappings':len(mapping),'consumerChecks':consumer_result,'fonts':font_evidence,'runtime':'not-run','visual':'not-run','editorial':'coordinator-acceptance-required',
              'rendering':'unverified-static-candidate','limitations':[config['mechanismBoundary'],'Complex-script input/IME and fixed-cell keyboard rendering are unverified.','No installer, game, save or installed-game changes performed.']}
    if font_checkpoint is not None:manifest['fontCheckpoint']=font_checkpoint
    if image_pins is not None:manifest['imageInputs']=image_pins
    write_new(output/'manifest.json',serialized(manifest))
    # Verify actual delivered bytes before acceptance is issued.
    verify_bytes(payload,rows,lambda name:(output/name).read_bytes(),image_key)
    write_new(output/'ACCEPTANCE.json',serialized({'status':'passed-technical-candidate','siteLocale':locale,'manifestSha256':sha((output/'manifest.json').read_bytes()),'bindingsSha256':sha(proof_raw),'editorial':'pending-coordinator-evidence','runtime':'not-run','visual':'not-run'}))
    return {'status':'technical-candidate','siteLocale':locale,'build':str(output),'files':len(rows),'displayMappings':len(mapping)}


def verify_bytes(payload, rows, read, image_key=None):
    for row in rows:
        name='files/'+row['path'];actual=read(name)
        if actual!=payload[name] or sha(actual)!=row['sha256']:raise ValueError('Actual delivered bytes differ: '+name)
        if row.get('encoding')=='rpgmv-image':
            from image_resources import decode
            plain,expected=decode(actual,image_key),decode(payload[name],image_key)
        else:
            plain=crypt(actual,True) if row['encrypted'] else actual
            expected=crypt(payload[name],True) if row['encrypted'] else payload[name]
        if plain!=expected or sha(plain)!=row['plaintextSha256']:raise ValueError('Actual decrypted native bytes differ: '+name)


def verify(root,locale,revision,archive=None):
    locale_config(locale)
    revision=inside(revision,root/'build/multilingual-delivery')
    accepted=strict_json((revision/'ACCEPTANCE.json').read_bytes())
    manifest_raw=(revision/'manifest.json').read_bytes();m=strict_json(manifest_raw)
    if m.get('siteLocale')!=locale or accepted.get('siteLocale')!=locale:raise ValueError('Build locale mismatch')
    if m.get('status')!='technical-candidate' or m.get('editorial')!='coordinator-acceptance-required' or m.get('runtime')!='not-run' or m.get('visual')!='not-run':raise ValueError('Technical candidate metadata cannot grant editorial/runtime acceptance')
    if accepted.get('status')!='passed-technical-candidate' or accepted.get('manifestSha256')!=sha(manifest_raw):raise ValueError('Incomplete or changed build acceptance')
    for name,h in m['recipeDependencies'].items():
        safe_relative(name)
        if sha((root/name).read_bytes())!=h:raise ValueError('Delivery recipe dependency changed: '+name)
    ctx,pairs,mapping,config,pinned=input_state(root,locale,root/m['inputs']['plaintext'])
    if pinned!=m['inputs']:raise ValueError('Stale source/author receipt dependency')
    if m.get('displayMappings')!=len(mapping) or m.get('authoredEntries')!=len(pairs) or m.get('visibleUnits')!=len(ctx.units)-len(ctx.retained) or m.get('technicalRetentions')!=len(ctx.retained):raise ValueError('Candidate coverage metadata changed')
    payload,rows,proof,font_evidence=expected_payload(ctx,pairs,mapping,config,m.get('fontCheckpoint'))
    image_key=None
    if m.get('imageInputs') is not None:
        image_files,image_rows,pins,image_key=image_payload(root,locale,root/m['imageInputs']['packet']['path'])
        if pins!=m['imageInputs']:raise ValueError('Stale image input binding')
        merge_images(payload,rows,image_files,image_rows)
    if rows!=m['files'] or config!=m['config'] or font_evidence!=m['fonts']:raise ValueError('Native manifest differs from actual source-bound compilation')
    if check_consumers(root,payload,proof,mapping)!=m['consumerChecks']:raise ValueError('Consumer check receipt changed')
    proof_raw=serialized(proof)
    if (revision/'bindings.json').read_bytes()!=proof_raw or sha(proof_raw)!=m['bindingsSha256'] or accepted.get('bindingsSha256')!=sha(proof_raw):raise ValueError('Incomplete/unwired native mapping proof')
    expected=set(payload)|{'bindings.json','manifest.json','ACCEPTANCE.json','INCOMPLETE.json'}
    actual={str(p.relative_to(revision)) for p in revision.rglob('*') if p.is_file()}
    if actual!=expected or any(p.is_symlink() for p in revision.rglob('*')):raise ValueError('Native build entry set/symlink mismatch')
    verify_bytes(payload,rows,lambda name:(revision/name).read_bytes(),image_key)
    if archive is not None:
        archive=inside(archive,root/'build/multilingual-delivery')
        with ZipFile(archive) as z:
            names=z.namelist();archive_expected=set(payload)|{'manifest.json','bindings.json','ACCEPTANCE.json'}
            for name in names:safe_relative(name)
            if len(names)!=len(set(names)) or set(names)!=archive_expected:raise ValueError('Archive entry set mismatch')
            if any((i.external_attr>>16)&0o170000==0o120000 for i in z.infolist()):raise ValueError('Archive symlink forbidden')
            for name in ['manifest.json','bindings.json','ACCEPTANCE.json']:
                if z.read(name)!=(revision/name).read_bytes():raise ValueError('Archive evidence bytes differ')
            verify_bytes(payload,rows,z.read,image_key)
    return {'status':'passed-native-decrypted-readback','siteLocale':locale,'files':len(rows),'mappedTargets':len(proof['bindings']),
            'authoredEntries':len(pairs),'archive':str(archive) if archive else None,'runtime':'not-run','visual':'not-run','editorial':'pending-coordinator-evidence'}


def package(root,locale,revision,output):
    locale_config(locale)
    output=inside(output,root/'build/multilingual-delivery',new=True)
    revision=inside(revision,root/'build/multilingual-delivery')
    if output.is_relative_to(revision):raise ValueError('Archive must be outside immutable build revision')
    verify(root,locale,revision)
    output.parent.mkdir(parents=True,exist_ok=True)
    m=strict_json((revision/'manifest.json').read_bytes())
    names=sorted(['files/'+r['path'] for r in m['files']]+['manifest.json','bindings.json','ACCEPTANCE.json'])
    with ZipFile(output,'x',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for name in names:
            i=ZipInfo(name,date_time=(2026,10,15,0,0,0));i.compress_type=ZIP_DEFLATED;i.external_attr=0o100644<<16
            z.writestr(i,(revision/name).read_bytes())
    result=verify(root,locale,revision,output)
    receipt=output.with_name(output.name+'.receipt.json')
    write_new(receipt,serialized(result|{'archiveSha256':sha(output.read_bytes()),'buildManifestSha256':sha((revision/'manifest.json').read_bytes())}))
    return result|{'archiveSha256':sha(output.read_bytes()),'receipt':str(receipt)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--locale',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('--plaintext',type=Path,required=True);b.add_argument('--output',type=Path,required=True);b.add_argument('--images',type=Path);b.add_argument('--reuse-font-build',type=Path)
    v=sub.add_parser('verify');v.add_argument('--build',type=Path,required=True);v.add_argument('--archive',type=Path)
    p=sub.add_parser('package');p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();root=a.root.resolve();locale_config(a.locale)
    if root!=Path('/Users/antonkrutov/Desktop/omori full translation mod'):raise ValueError('Use the canonical project root')
    if a.command=='build':result=build(root,a.locale,a.plaintext,a.output,images=a.images,reuse_font_build=a.reuse_font_build)
    elif a.command=='verify':result=verify(root,a.locale,a.build,a.archive)
    else:result=package(root,a.locale,a.build,a.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,FileNotFoundError,subprocess.CalledProcessError) as error:
        print(str(error),file=sys.stderr);sys.exit(2)
