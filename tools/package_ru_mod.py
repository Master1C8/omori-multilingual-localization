#!/usr/bin/env python3
"""Deterministic local OneLoader text/font review archive. Never installs it."""
import argparse
import json
import shutil
import subprocess
import shlex
import zipfile
from pathlib import Path
from source_prepare import strict_json, save_json, sha


def verify_outputs(directory, expected, label):
    actual={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file() and p!=directory/'receipt.json'}
    if not expected or set(actual)!=set(expected):raise ValueError(label+' output inventory changed')
    for name,path in actual.items():
        if path.is_symlink() or sha(path.read_bytes())!=expected[name]:raise ValueError(label+' output bytes changed: '+name)


def rebuild_recipe(root, args):
    relative=lambda p:Path(p).resolve().relative_to(root).as_posix()
    command=['python3','-B','tools/package_ru_mod.py','--combined',relative(args.combined),
             '--display',relative(args.display),'--fonts',relative(args.fonts),
             '--editorial',relative(args.editorial),'--font-reproducibility',relative(args.font_reproducibility)]
    if args.independent:command+=['--independent',relative(args.independent)]
    reproduction='dist/ru-text-8879120-rebuild'
    if (root/reproduction).exists():
        # The proof's immutable cycle identifies the replay, independently of
        # the first/reproduction output path. Otherwise replay metadata changes.
        reproduction+='-'+Path(args.editorial).parent.name
    command+=['--output',reproduction]
    return {'fontPreparation':{'mode':'reuse-verified-byte-checkpoint','directory':relative(args.fonts),
                              'receipt':relative(args.fonts/'receipt.json'),
                              'reproducibility':relative(args.font_reproducibility)},
            'prerequisiteOrder':['source-and-glossary','verified-font-byte-checkpoint','combined-resources','display-compilation','package'],
            'commands':['python3 -B tools/assemble_ru_resources.py --output build/ru/combined-rebuild',
                        shlex.join(['python3','-B','tools/compile_ru_display.py','--combined','build/ru/combined-rebuild',
                                    '--fonts',relative(args.fonts),'--output','build/ru/display-rebuild']),
                        shlex.join(command)],
            'commandsScope':'The first two commands rebuild resources into new directories. Fonts reuse the verified existing checkpoint established before compilation. Exact ZIP reproduction uses the final command and its pinned original combined/display/font/proof paths; newly rebuilt directory paths would change provenance metadata. Existing output directories reject; choose a fresh output path.'}


def verify_independent(root, report_path, combined_path, display_path, fonts_path):
    report=strict_json(report_path.read_bytes())
    if report.get('passStatus')!='passed-clean-delta' or report.get('findings'):
        raise ValueError('Clean independent delta receipt required')
    reviewer=report.get('reviewer',{})
    if reviewer.get('taskIdentity')!='/root/omori_independent_review' or reviewer.get('model')!='gpt-6.1-sol' or reviewer.get('reasoning')!='high':
        raise ValueError('Authorized independent reviewer identity required')
    manifest_path=root/report['inputManifest']
    if sha(manifest_path.read_bytes())!=report['inputManifestSha256']:raise ValueError('Independent manifest changed')
    manifest=strict_json(manifest_path.read_bytes())
    source_units=strict_json((root/'source/text-corpus-8879120-02/units.json').read_bytes())
    known={u['id'] for u in source_units}
    prior_manifest=root/manifest['previousManifest']
    prior_doc=strict_json(prior_manifest.read_bytes())
    if 'currentClosureIds' in prior_doc:previous=set(prior_doc['currentClosureIds'])
    else:
        prior_closure=prior_manifest.parent/prior_doc['components']['closure']['path']
        if sha(prior_closure.read_bytes())!=prior_doc['components']['closure']['sha256']:
            raise ValueError('Independent previous closure changed')
        previous=set(strict_json(prior_closure.read_bytes()))
    current=set(manifest['currentClosureIds']);changed=set(manifest['changedIds']);invalidated=set(manifest['invalidatedIds'])
    expected=changed | (current-previous) | invalidated
    if not current<=known or not invalidated<=known or not changed<=known or set(manifest['reviewIds'])!=expected:
        raise ValueError('Independent dependency delta differs')
    pins={**manifest['inputs'],**manifest['authorDependencies']}
    for name,digest in pins.items():
        if sha((root/name).read_bytes())!=digest:raise ValueError('Independent graph changed: '+name)
    for path in [combined_path/'receipt.json',display_path/'receipt.json',fonts_path/'receipt.json']:
        name=str(path.resolve().relative_to(root))
        if pins.get(name)!=sha(path.read_bytes()):raise ValueError('Independent artifact graph mismatch')
    if set(report['reviewedIds'])!=set(manifest['reviewIds']) or len(report['reviewedIds'])!=len(set(report['reviewedIds'])):
        raise ValueError('Independent delta coverage mismatch')
    if report.get('mandatoryRegressionStatus')!='passed-static':raise ValueError('Independent mandatory regressions incomplete')
    prior=root/report['priorReport']
    if sha(prior.read_bytes())!=report['priorReportSha256']:raise ValueError('Independent prior pass changed')
    first=strict_json(prior.read_bytes())
    first_manifest=root/manifest.get('firstManifest',manifest['previousManifest'])
    if sha(first_manifest.read_bytes())!=first['inputManifestSha256']:
        raise ValueError('Independent first manifest changed')
    previous_report=root/report.get('previousReport',report['priorReport'])
    previous_review=strict_json(previous_report.read_bytes())
    if sha(previous_report.read_bytes())!=report.get('previousReportSha256',report['priorReportSha256']):
        raise ValueError('Independent previous report changed')
    if sha(prior_manifest.read_bytes())!=previous_review['inputManifestSha256']:
        raise ValueError('Independent previous manifest changed')
    if not manifest['authorDependencies'].items()<=first['pinnedInputs'].items() and not changed:
        raise ValueError('Unchanged editorial authors differ from first pass')
    if first['readCoverage']['closureCount']!=284 or len(set(first['readCoverage']['reviewedIds']))!=284 or first['readCoverage']['mandatoryUniqueIds']!=824:
        raise ValueError('Independent complete first-pass coverage required')
    if set(report['resolvedFindingIds'])!={f['id'] for r in [first,previous_review] for f in r['findings']}:
        raise ValueError('Independent finding disposition incomplete')
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['combined','display','fonts','output']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--editorial',type=Path,required=True)
    ap.add_argument('--font-reproducibility',type=Path,required=True)
    ap.add_argument('--independent',type=Path)
    args=ap.parse_args();root=Path(__file__).resolve().parent.parent
    for name in ['combined','display','fonts','output']:
        path=getattr(args,name).resolve();path.relative_to(root);setattr(args,name,path)
    if args.output.exists():raise ValueError('Preserve previous package')
    combined=strict_json((args.combined/'receipt.json').read_bytes());display=strict_json((args.display/'receipt.json').read_bytes())
    if combined['occurrences']!=20775 or combined['status']!='passed':raise ValueError('Complete combined resources required')
    from assemble_ru_resources import read_pairs
    pairs,corpus_sha,current_dependencies=read_pairs(root)
    if combined['dependencies']!=current_dependencies or combined['corpusManifestRawSha256']!=corpus_sha:
        raise ValueError('Combined current dependency graph changed')
    for name,digest in combined['recipeDependencies'].items():
        if sha((root/'tools'/name).read_bytes())!=digest:raise ValueError('Combined recipe changed: '+name)
    verify_outputs(args.combined,combined.get('compiledOutputs'), 'Combined')
    if display['combinedReceiptSha256']!=sha((args.combined/'receipt.json').read_bytes()):raise ValueError('Display adapter is stale')
    if display.get('status')!='passed-static-assembly':raise ValueError('Validated display assembly required')
    verify_outputs(args.display,display.get('compiledOutputs'), 'Display')
    for path,digest in display['recipeDependencies'].items():
        if sha((root/path).read_bytes())!=digest:raise ValueError('Display recipe changed')
    font_receipt=strict_json((args.fonts/'receipt.json').read_bytes())
    if font_receipt['status']!='passed-static':raise ValueError('Validated font build required')
    editorial=strict_json(args.editorial.read_bytes())
    if editorial['fullPairedRead']!=20775 or editorial['status']!='complete coordinator semantic self-audit; independent diff review pending':
        raise ValueError('Complete recorded semantic self-audit required')
    for path,digest in editorial['authorDependencies'].items():
        if sha((root/path).read_bytes())!=digest:raise ValueError('Editorial author input changed')
    actual_authors={p:h for p,h in current_dependencies.items() if p.startswith('translation/ru/batches/')}
    if editorial['authorDependencies']!=actual_authors or display['authorDependencies']!=actual_authors:
        raise ValueError('Current reviewed author graph differs')
    if font_receipt.get('authorDependencies')!=editorial['authorDependencies']:
        raise ValueError('Font required-character inventory is stale')
    special_review = None
    if editorial.get('specialSceneReview'):
        from ru_special_scene_review import verify_review
        binding = editorial['specialSceneReview']
        special_path = (root/binding['path']).resolve()
        if not special_path.is_relative_to(root) or sha(special_path.read_bytes()) != binding['sha256']:
            raise ValueError('Special-scene editorial proof changed')
        special_review = verify_review(root, special_path)
    if font_receipt['recipeSha256']!=sha((root/'tools/build_ru_fonts.py').read_bytes()):
        raise ValueError('Font recipe changed')
    font_repro=strict_json(args.font_reproducibility.read_bytes())
    if font_repro['currentReceiptSha256']!=sha((args.fonts/'receipt.json').read_bytes()):
        raise ValueError('Font reproducibility evidence is stale')
    expected_fonts={r['path']:r['sha256'] for r in font_repro['files']}
    if set(expected_fonts)!={p.name for p in args.fonts.iterdir() if p.name!='receipt.json'}:
        raise ValueError('Font artifact inventory differs')
    for path,digest in expected_fonts.items():
        if sha((args.fonts/path).read_bytes())!=digest:raise ValueError('Font artifact changed')
    if display['fontInputs']['receiptSha256']!=sha((args.fonts/'receipt.json').read_bytes()) or display['fontInputs']['files']!=expected_fonts:
        raise ValueError('Display font/CSS input graph changed')
    independent=verify_independent(root,args.independent,args.combined,args.display,args.fonts) if args.independent else None
    plan=[]
    for row in combined['resources']:
        asset=row['originalAsset'];name=Path(asset).stem
        if asset.startswith('data/'):
            suffix=Path(asset).suffix
            if suffix=='.KEL':extension='.json'
            elif suffix=='.PLUTO':extension='.yml'
            else:raise ValueError('Unsupported native data format: '+asset)
            plan.append({'category':'data','file':'data/'+name+extension,'originalAsset':asset})
        elif asset.startswith('languages/en/'):
            plan.append({'category':'text','file':'text/'+name+'.yml','originalAsset':asset})
        elif not asset.startswith('js/'):raise ValueError('Unknown native injection category')
    for path in sorted((args.display/'plugins').glob('*.js')):
        plan.append({'category':'plugins','file':'plugins/'+path.name,'originalAsset':'js/plugins/'+path.stem+'.OMORI'})
    verified=subprocess.run(['node',str(root/'tools/loader_resource_paths.cjs')],input=json.dumps(plan),text=True,capture_output=True,cwd=root)
    if verified.returncode:raise ValueError(verified.stderr)
    args.output.mkdir(parents=True)
    identity='omori-ru-text-8879120';folder=args.output/identity;folder.mkdir()
    files={'data':[],'text':[],'plugins':[],'assets':[]};injection={};source_rows=[]
    for row in combined['resources']:
        asset=row['originalAsset'];source=args.combined/row['output']
        if sha(source.read_bytes())!=row['rawSha256']:raise ValueError('Combined resource changed')
        name=Path(asset).stem
        if asset.startswith('data/'):
            suffix=Path(asset).suffix
            if suffix=='.KEL':extension='.json'
            elif suffix=='.PLUTO':extension='.yml'
            else:raise ValueError('Unsupported native data format: '+asset)
            category='data';relative='data/'+name+extension;destination=asset.lower()
            override=args.display/'data'/(name+'.json')
            if override.exists():source=override
        elif asset.startswith('languages/en/'):
            category='text';relative='text/'+name+'.yml';destination='languages/en/'+name.lower()+'.hero'
        elif asset.startswith('js/'):
            # Core/config are represented by bootstrap function/parameter
            # patches. Full protected core files never enter the mod manifest.
            continue
        else:raise ValueError('Unknown injection category')
        path=folder/relative;path.parent.mkdir(exist_ok=True);shutil.copyfile(source,path)
        files[category].append(relative);injection[relative]=destination
        source_rows.append({'asset':asset,'file':relative,'sha256':sha(path.read_bytes()),'preparedSource':str(source.relative_to(root))})
    for source in sorted((args.display/'plugins').glob('*.js')):
        relative='plugins/'+source.name;path=folder/relative;path.parent.mkdir(exist_ok=True);shutil.copyfile(source,path)
        files['plugins'].append(relative);injection[relative]='js/plugins/'+source.stem.lower()+'.omori'
    for source in sorted(args.fonts.iterdir()):
        if source.name=='receipt.json':continue
        relative='fonts/'+source.name;path=folder/relative;path.parent.mkdir(exist_ok=True);shutil.copyfile(source,path)
        files['assets'].append(relative);injection[relative]=relative.lower()
    if len(set(injection.values()))!=len(injection):raise ValueError('Duplicate case-insensitive injection path')
    protected=['js/rpg_core.js','js/rpg_managers.js','js/rpg_objects.js','js/rpg_scenes.js','js/rpg_windows.js','js/plugins.js']
    if any(path in protected for path in injection.values()):raise ValueError('Protected core-file injection')
    manifest={'id':identity,'name':'OMORI Russian text — local review build','description':'Russian text and outline font fallback for Steam build 8879120. Independent editorial review, game runtime, visual QA and installation are not verified. No localized images/textures.',
        'version':'0.1.0-static-review','manifestVersion':1,'_flags':[], 'files':files,
        'plugins_ordered':{'omoriru_bootstrap':{'at':0},'omoriru_install':{'at':-1,'weight':-100000}}}
    save_json(folder/'mod.json',manifest)
    (folder/'README.md').write_text('''# OMORI Russian text: local review build

Supported source: Steam build 8879120, English resource channel. This mod replaces
the English text channel with Russian. Select the English channel in the base
game when this package is eventually tested. The package does not change native
database names, variable keywords, event choices, asset keys or comparison tables.

This is a local review artifact, not an accepted release. Independent editorial
review, actual loader boot, game runtime, installation and visual QA are pending.
The assigned author's complete 20,775-pair semantic self-audit and corrections
and source-bound dependency review are recorded in evidence/editorial-self-audit.json.
Images, textures, OCR and localized image lettering are excluded. English text
inside original images therefore remains. Older save metadata lacking typed
actor/map provenance keeps its original labels; this path needs runtime review.

No game or installer was launched to create or validate this package. Nothing
was written to the installed game or existing saves. The archive includes no
installer, loader binaries, game executable, shutdown action or network service.

Intended loader: OneLoader 1.5 or compatible. The manifest follows its official
resource and plugin-order rules. Loader-safe bootstrap plugins apply the protected
core text function changes and exact plugin parameter edits before native plugins
capture/read them. Exact source mismatch stops initialization instead of guessing.
Do not combine this review build with overlapping text/database/plugin mods until
conflict behavior is tested. This archive has not been installed.

Russian fallback outlines preserve the original Latin font faces, add Cyrillic
faces with measured baselines, and cover retained Chinese dialogue and symbols.
Static coverage does not establish readability, wrapping or visual parity.
The included font software remains under its accompanying SIL OFL licenses.
The bundled mplus fallback is referenced from the existing game, not redistributed.

Rebuild from the canonical project using the commands recorded in
`evidence/package-inputs.json`. ZIP timestamps, order and permissions are fixed.
The accompanying package receipt records byte hashes read from the actual ZIP.

Official format reference: https://github.com/rphsoftware/OneLoader
''')
    if independent:
        manifest['description']='Russian text and outline font fallback for Steam build 8879120. Static independent editorial review passed. Game runtime, visual QA and installation remain unverified. No localized images/textures.'
        save_json(folder/'mod.json',manifest)
        readme=folder/'README.md';text=readme.read_text()
        text=text.replace('Independent editorial\nreview, actual loader boot, game runtime, installation and visual QA are pending.',
            'Independent static editorial review passed. Actual loader boot, game runtime,\ninstallation and visual QA remain pending. See evidence/independent-review.json.')
        readme.write_text(text)
    evidence=folder/'evidence';evidence.mkdir()
    shutil.copyfile(args.editorial,evidence/'editorial-self-audit.json')
    if independent:shutil.copyfile(args.independent,evidence/'independent-review.json')
    if special_review:
        shutil.copyfile(special_path,evidence/'special-scene-review.json')
        shutil.copyfile(root/special_review['rows'],evidence/'special-scene-pairs.jsonl')
        shutil.copyfile(root/special_review['decisions'],evidence/'special-scene-decisions.json')
    inputs={'combinedReceipt':str((args.combined/'receipt.json').relative_to(root)),'combinedReceiptSha256':sha((args.combined/'receipt.json').read_bytes()),
        'displayReceipt':str((args.display/'receipt.json').relative_to(root)),'displayReceiptSha256':sha((args.display/'receipt.json').read_bytes()),
        'fontReceipt':str((args.fonts/'receipt.json').relative_to(root)),'fontReceiptSha256':sha((args.fonts/'receipt.json').read_bytes()),
        'editorialReceipt':str(args.editorial.resolve().relative_to(root)),'editorialReceiptSha256':sha(args.editorial.read_bytes()),
        'fontReproducibility':str(args.font_reproducibility.resolve().relative_to(root)),'fontReproducibilitySha256':sha(args.font_reproducibility.read_bytes()),
        'corpusManifestRawSha256':combined['corpusManifestRawSha256'],'occurrences':20775,'retainedTechnicalUnits':editorial['retainedTechnicalUnits'],
        'displayMappings':3505,'injections':injection,'resourceSources':source_rows,
        'nativeInjectionVerification':strict_json(verified.stdout),
        'loaderReferences':{p.name:sha(p.read_bytes()) for p in (root/'source/loader-reference').glob('*.js')},
        **rebuild_recipe(root,args),
        'packageRecipeSha256':sha(Path(__file__).read_bytes()),'runtime':'not-run','visual':'not-run','independentReview':'passed-static' if independent else 'pending'}
    if independent:inputs['independentReceipt']={'path':str(args.independent.resolve().relative_to(root)),'sha256':sha(args.independent.read_bytes())}
    if special_review:inputs['specialSceneReview']=editorial['specialSceneReview']
    save_json(evidence/'package-inputs.json',inputs)
    expected={str(p.relative_to(args.output)):p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}
    archive=args.output/(identity+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as stream:
        for name,raw in sorted(expected.items()):
            info=zipfile.ZipInfo(name,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16;stream.writestr(info,raw,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(archive) as stream:
        if len(stream.namelist())!=len(set(stream.namelist())) or set(stream.namelist())!=set(expected):raise ValueError('ZIP entry coverage mismatch')
        for name,raw in expected.items():
            if stream.read(name)!=raw:raise ValueError('Delivered ZIP bytes differ')
        if stream.testzip() is not None:raise ValueError('ZIP CRC failure')
    receipt={'status':'passed-local-package','archive':archive.name,'archiveSha256':sha(archive.read_bytes()),'archiveBytes':archive.stat().st_size,
        'entries':len(expected),'occurrences':20775,'files':{name:sha(raw) for name,raw in expected.items()},
        'inputs':inputs,'semanticSelfAudit':'complete; 20775 pairs, '+str(editorial['correctedOccurrences'])+' corrected occurrences, '+str(len(editorial['dependencyIds']))+' dependency IDs',
        'editorialAcceptance':'passed-static' if independent else 'independent diff review pending','loaderRuntime':'not-run','visual':'not-run','installedGameWrites':False}
    save_json(args.output/'receipt.json',receipt)
    print({k:receipt[k] for k in ['status','archive','archiveSha256','archiveBytes','entries','occurrences']})

if __name__=='__main__':main()
