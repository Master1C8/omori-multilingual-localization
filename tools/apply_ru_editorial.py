#!/usr/bin/env python3
"""Apply directly authored reviewed corrections; preserve each prior revision."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from authoring_keys import target_key
from source_prepare import sha, strict_json, save_json


def current_draft(root, batch, units):
    if 'authoringDraft' in batch:
        path = root/batch['authoringDraft']
        if sha(path.read_bytes()) != batch['authoringDraftRawSha256']:
            raise ValueError('Current draft differs from its pinned version')
        return strict_json(path.read_bytes()), path
    # Early completed batches were directly authored in batch JSON. Reconstruct
    # only their exact existing values/metadata; do not invent a lost draft.
    assets = {units[e['id']]['asset'] for e in batch['entries']}
    if len(assets) != 1:
        raise ValueError('Early multi-asset batch needs a dedicated exact adapter')
    draft = {'batchId':batch['batchId'],'asset':next(iter(assets)),
             'targetKeyMode':'source-id','scope':batch['scope'],
             'contextNotes':list(batch.get('contextNotes',[])),
             'immediateEditByAssignedModel':True,'targets':{},
             'placeholderForms':{},'omissionReasons':{},'preservedTechnicalReasons':{},'encodedTargets':[]}
    for e in batch['entries']:
        draft['targets'][e['id']] = e.get('encodedPayload',{}).get('decodedTarget',e['target'])
        if e.get('encodedPayload'): draft['encodedTargets'].append(e['id'])
        if e.get('placeholderForms'): draft['placeholderForms'][e['id']] = e['placeholderForms']
        if e.get('syntacticOmission'): draft['omissionReasons'][e['id']] = e['syntacticOmission']['reason']
        if e.get('sourceRoleDisposition'): draft['preservedTechnicalReasons'][e['id']] = e['sourceRoleDisposition']['reason']
    return draft, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('corrections', type=Path)
    ap.add_argument('--history', type=Path, required=True)
    ap.add_argument('--revision', default='semantic01', help='New immutable draft/build revision suffix')
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    args.corrections = args.corrections.resolve()
    corrections = strict_json(args.corrections.read_bytes())
    if not re.fullmatch(r'[a-z0-9-]+', args.revision):
        raise ValueError('Invalid immutable revision suffix')
    if corrections['status'] not in {
        'complete paired self-edit; controls and 47 changed battle assemblies passed',
        'complete paired self-edit; selected scene groups reviewed and controls passed',
    }:
        raise ValueError('Completed source/target edit required')
    units = {u['id']: u for u in strict_json((root/'source/text-corpus-8879120-02/units.json').read_bytes())}
    grouped = defaultdict(list)
    for edit in corrections['changes']:
        grouped[edit['batch']].append(edit)
    args.history.mkdir(parents=True, exist_ok=True)
    state_path = args.history/'application.json'
    if state_path.exists():
        state = strict_json(state_path.read_bytes())
        if state['correctionsSha256'] != sha(args.corrections.read_bytes()):
            raise ValueError('Preserve execution inputs')
        if state.get('revision', 'semantic01') != args.revision:
            raise ValueError('Preserve execution revision')
    else:
        state = {'correctionsSha256':sha(args.corrections.read_bytes()),
                 'recipeSha256':sha(Path(__file__).read_bytes()),'revision':args.revision,'batches':{}}
        # Check every selected current entry and draft before any canonical edit.
        for batch_id, edits in grouped.items():
            path = root/'translation/ru/batches'/f'{batch_id}.json'
            batch = strict_json(path.read_bytes())
            entries = {e['id']:e for e in batch['entries']}
            current_draft(root, batch, units)
            for edit in edits:
                if entries[edit['id']]['target'] != edit['before'] or units[edit['id']]['source'] != edit['source']:
                    raise ValueError('Correction does not match current exact occurrence')
            state['batches'][batch_id] = {'beforeSha256':sha(path.read_bytes()),'status':'prepared'}
        save_json(state_path, state)
    for batch_id, edits in grouped.items():
        record = state['batches'][batch_id]
        batch_path = root/'translation/ru/batches'/f'{batch_id}.json'
        if record['status'] == 'passed':
            if sha(batch_path.read_bytes()) != record['afterSha256']:
                raise ValueError('Previously applied canonical batch changed')
            receipt = root/record['receipt']
            if sha(receipt.read_bytes()) != record['receiptSha256']:
                raise ValueError('Previously completed receipt changed')
            continue
        if sha(batch_path.read_bytes()) != record['beforeSha256']:
            raise ValueError('Unfinished application needs exact current-state reconciliation')
        before = strict_json(batch_path.read_bytes())
        draft, prior_draft = current_draft(root, before, units)
        historical_draft = json.loads(json.dumps(draft))
        draft['contextNotes'].append('Source-bound paired correction review: '+str(args.corrections.relative_to(root))+'. Earlier stage notes are historical. This correction is coordinator self-review; independent review of changed wording and game/visual acceptance remain pending.')
        for edit in edits:
            draft['targets'][target_key(units[edit['id']], draft.get('targetKeyMode','catalog-text'))] = edit['target']
        revision = args.history/batch_id
        revision.mkdir(exist_ok=True)
        old_batch = revision/'batch-before.json'
        old_draft = revision/'draft-before.json'
        if not old_batch.exists(): shutil.copyfile(batch_path, old_batch)
        if not old_draft.exists():
            if prior_draft: shutil.copyfile(prior_draft, old_draft)
            else: save_json(revision/'exact-prior-batch-values.json',historical_draft)
        if sha(old_batch.read_bytes()) != record['beforeSha256']:
            raise ValueError('Historical revision mismatch')
        new_draft = root/'translation/ru/drafts'/f'{batch_id}-{args.revision}.json'
        if new_draft.exists():
            if strict_json(new_draft.read_bytes()) != draft:
                raise ValueError('Prepared editorial draft changed')
        else: save_json(new_draft, draft)
        output = root/'build/ru/batches'/f'{batch_id}-{args.revision}'
        batch_path.unlink()
        try:
            subprocess.run([sys.executable,'-B',str(root/'tools/pack_authored_catalog.py'),str(new_draft)],check=True)
            subprocess.run([sys.executable,'-B',str(root/'tools/translation_batch.py'),str(batch_path),
                            '--corpus',str(root/'source/text-corpus-8879120-02'),'--output',str(output)],check=True)
        except BaseException:
            shutil.copyfile(old_batch, batch_path)
            raise
        receipt = output/'receipt.json'
        record.update(status='passed',afterSha256=sha(batch_path.read_bytes()),
                      receipt=str(receipt.relative_to(root)),receiptSha256=sha(receipt.read_bytes()),
                      draftSha256=sha(new_draft.read_bytes()),changedIds=[e['id'] for e in edits])
        save_json(state_path,state)
        print('EDITORIAL',batch_id,'passed',len(edits),'changes',flush=True)
    state['status']='passed; all selected canonical batches and new resources verified'
    save_json(state_path,state)


if __name__ == '__main__':
    main()
