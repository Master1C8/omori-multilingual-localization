"""Reconcile source-bound author data with actual delivered plaintext resources."""
import argparse
from collections import defaultdict
import gzip
import json
import os
import tempfile
from pathlib import Path
from source_prepare import strict_json, save_json, sha
from source_text_syntax import quick_macro_names
from encoded_dialogue import load_registry, validate_entry
from verify_source_inventory import parse
from translation_batch import at
from authoring_keys import target_key
from display_mapping import validate_mapping_document
from database_modifiers import validate_description_modifiers
from text_resource_adapter import verify_delivered_spans
from script_resource_adapter import verify_resources as verify_script_resources
from authoring_omissions import validate_target_presence, validate_source_disposition


def atomic_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_reconciliation(evidence_path, index_path, evidence, index, before_index=None):
    """Two per-file commits, no cross-file transaction or evidence rollback.

    If the second commit fails, verified evidence survives and the prior index
    remains intact. Reconcile with a new immutable evidence path to retry.
    """
    if evidence_path.exists():
        raise ValueError('Preserve earlier verification evidence')
    atomic_json(evidence_path, evidence)
    if before_index is not None:
        before_index()
    atomic_json(index_path, index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve earlier verification evidence')
    root = Path(__file__).resolve().parent.parent
    corpus = root / 'source/text-corpus-8879120-02'
    manifest = strict_json((corpus / 'manifest.json').read_bytes())
    if manifest['status'] != 'passed' or manifest['sourceGate'] != 'accepted-text-inventory':
        raise ValueError('Accepted corpus required')
    for name, digest in manifest['fileHashes'].items():
        if sha((corpus / name).read_bytes()) != digest:
            raise ValueError('Accepted corpus artifact changed')
    units = {u['id']:u for u in strict_json((corpus / 'units.json').read_bytes())}
    registry = load_registry(root, units)
    glossary_path = root / 'glossary/ru/approved.json'
    label = strict_json(glossary_path.read_bytes())['roboheart']['term']
    macros = quick_macro_names(strict_json((root / 'source/parameter-roles-8879120-01/parameters.json').read_bytes()))
    index_path = root / 'translation/ru/current-builds.json'
    index = strict_json(index_path.read_bytes())
    receipts = [(p, strict_json(p.read_bytes())) for p in (root / 'build/ru/batches').glob('*/receipt.json')]
    base = root / 'source/inventory-8879120-01'
    reports = {r['asset']: r for r in strict_json((base / 'structured-assets.json').read_bytes())}
    originals = {}
    current, seen, encoded_count, resource_count, mapped_count = {}, set(), 0, 0, 0
    technical_count = 0
    for batch_path in sorted((root / 'translation/ru/batches').glob('*.json')):
        batch = strict_json(batch_path.read_bytes())
        if (batch['corpusManifestRawSha256'] != sha((corpus / 'manifest.json').read_bytes())
                or batch['glossaryRuRawSha256'] != sha(glossary_path.read_bytes())):
            raise ValueError('Author inputs changed')
        matches = [(p, r) for p, r in receipts if r['batchId'] == batch['batchId']
                   and r['batchRawSha256'] == sha(batch_path.read_bytes()) and r['status'] == 'passed']
        prior = index['buildReceipts'].get(batch['batchId'])
        preferred = [(p, r) for p, r in matches if str(p.relative_to(root)) == prior]
        if preferred:
            matches = preferred
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous current build: ' + batch['batchId'])
        path, receipt = matches[0]
        if (receipt['corpusManifestRawSha256'] != batch['corpusManifestRawSha256']
                or receipt['glossaryRuRawSha256'] != batch['glossaryRuRawSha256']
                or receipt['authoredUnits'] != len(batch['entries'])):
            raise ValueError('Build receipt inputs/count changed')
        draft = None
        if 'authoringDraft' in batch:
            draft_path = root / batch['authoringDraft']
            if sha(draft_path.read_bytes()) != batch['authoringDraftRawSha256']:
                raise ValueError('Author draft changed')
            draft = strict_json(draft_path.read_bytes())
        actual = {}
        script_pairs = [(units[e['id']], e) for e in batch['entries']
                        if 'spanUtf16' in units[e['id']] or units[e['id']]['asset'] == 'js/plugins.js']
        script_resources = [r for r in receipt['resources'] if r.get('kind') in {'script','plugin-config','structured-embedded'}]
        script_targets = verify_script_resources(root, path, script_resources, script_pairs, macros) if script_pairs else {}
        for resource in receipt['resources']:
            output = path.parent / resource['output']
            if sha(output.read_bytes()) != resource['rawSha256']:
                raise ValueError('Delivered resource changed')
            if resource not in script_resources:
                actual[resource['originalAsset']] = parse(resource['originalAsset'], output.read_bytes())
            resource_count += 1
        mapping_expected = [(units[e['id']], e) for e in batch['entries']
                            if units[e['id']]['role'] == 'visible-display-mapping']
        mapping_meta = receipt.get('displayMappings')
        mappings = {}
        if mapping_expected:
            if not mapping_meta or mapping_meta['units'] != len(mapping_expected):
                raise ValueError('Missing display mapping receipt')
            mapping_output = path.parent / mapping_meta['output']
            if sha(mapping_output.read_bytes()) != mapping_meta['rawSha256']:
                raise ValueError('Delivered display mapping changed')
            mappings = validate_mapping_document(strict_json(mapping_output.read_bytes()), mapping_expected,
                                                  batch['corpusManifestRawSha256'])
        elif mapping_meta:
            raise ValueError('Unexpected display mapping receipt')
        mixed_groups, mixed_targets = defaultdict(list), {}
        for entry in batch['entries']:
            unit = units[entry['id']]
            if unit['id'] not in script_targets and ('span' in unit or 'spanCodepoints' in unit):
                if unit['role'] != 'visible':
                    raise ValueError('Mixed display mapping needs its separate adapter')
                mixed_groups[(unit['asset'], tuple(unit['path']))].append((unit, entry))
        for (asset, field_path), edits in mixed_groups.items():
            if asset not in originals:
                originals[asset] = parse(asset, gzip.decompress((base / reports[asset]['snapshot']).read_bytes()))
            mixed_targets.update(verify_delivered_spans(at(originals[asset], field_path),
                                                        at(actual[asset], field_path), edits, macros))
        for entry in batch['entries']:
            unit = units[entry['id']]
            if entry['id'] in seen or entry['source'] != unit['source'] or entry['state'] != 'authored-edited':
                raise ValueError('Duplicate, changed or unfinished author unit')
            validate_target_presence(unit, entry)
            validate_source_disposition(unit, entry)
            technical_count += bool(entry.get('sourceRoleDisposition'))
            seen.add(entry['id'])
            delivered = (script_targets[unit['id']] if unit['id'] in script_targets
                         else mixed_targets[unit['id']] if unit['id'] in mixed_targets
                         else at(actual[unit['asset']], unit['path']))
            if unit['role'] == 'visible-display-mapping':
                if delivered != unit['source']:
                    raise ValueError('Delivered logical identity changed')
                delivered = mappings[unit['id']]['target']
                mapped_count += 1
            if delivered != entry['target']:
                raise ValueError('Delivered target differs from author data')
            validate_entry(unit, dict(entry, target=delivered), macros, registry, label)
            validate_description_modifiers(unit, delivered)
            if draft:
                key = target_key(unit, draft.get('targetKeyMode', 'catalog-text'))
                author_target = entry['encodedPayload']['decodedTarget'] if entry.get('encodedPayload') else entry['target']
                if author_target != draft['targets'][key]:
                    raise ValueError('Canonical target differs from author draft')
                if bool(entry.get('encodedPayload')) != (key in draft.get('encodedTargets', [])):
                    raise ValueError('Author encoding declaration changed')
            encoded_count += bool(entry.get('encodedPayload'))
        current[batch['batchId']] = str(path.relative_to(root))
    count = len(seen)
    index.update(authoredEditedOccurrences=count, coveragePercent=count / len(units) * 100,
                 displayMappedUnitsPrepared=mapped_count, scalarTranslatedUnits=count - mapped_count - technical_count,
                 retainedTechnicalUnits=technical_count,
                 buildReceipts=current)
    evidence = {'schemaVersion':1, 'status':'passed', 'uniqueAuthoredDeliveredUnits':count,
                'corpusUnits':len(units), 'coveragePercent':index['coveragePercent'],
                'catalogs':len(current), 'actualResourcesReparsed':resource_count,
                'encodedDecodedTargetsChecked':encoded_count, 'currentBuildReceipts':current,
                'displayMappedUnitsPrepared': mapped_count,
                'retainedTechnicalUnits': technical_count,
                'corpusManifestRawSha256':sha((corpus / 'manifest.json').read_bytes()),
                'glossaryRuRawSha256':sha(glossary_path.read_bytes()),
                'recipeRawSha256':sha(Path(__file__).read_bytes()),
                'authoringKeysRawSha256':sha((root / 'tools/authoring_keys.py').read_bytes()),
                'displayMappingRecipeRawSha256':sha((root / 'tools/display_mapping.py').read_bytes()),
                'databaseModifiersRecipeRawSha256':sha((root / 'tools/database_modifiers.py').read_bytes()),
                'mixedSpanAdapterRawSha256':sha((root / 'tools/text_resource_adapter.py').read_bytes()),
                'runtime':'not-run', 'semanticAudit':'pending-full-corpus', 'independentReview':'pending',
                'limits':['Reuses original build protected-tree validation through unchanged delivered-resource hashes.',
                          'Reparses and verifies every current delivered target and native controls; does not prove runtime or semantic quality.',
                          'Mapped-unit targets are source-bound sidecar labels; their protected original fields remain exact. Consumer integration is pending.']}
    write_reconciliation(args.evidence, index_path, evidence, index)
    print({k:evidence[k] for k in ['uniqueAuthoredDeliveredUnits','corpusUnits','coveragePercent','catalogs','actualResourcesReparsed','encodedDecodedTargetsChecked','displayMappedUnitsPrepared']})


if __name__ == '__main__':
    main()
