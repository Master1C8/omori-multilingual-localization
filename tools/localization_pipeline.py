#!/usr/bin/env python3
"""Finite, evidence-gated stages for the existing OMORI CLI queue.

The scheduler owns only dispatch and stage transitions. Models author/review wording;
deterministic acceptance and native-delivery adapters verify their saved artifacts.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import localization_cli as queue

ROLES = ('author', 'editor', 'reviewer', 'resources', 'package')
ROLE_STAGE = {'author': 'translate-edit', 'editor': 'editorial', 'reviewer': 'editorial',
              'resources': 'resources', 'package': 'package'}
NEXT_ROLE = {'author': 'editor', 'editor': 'reviewer', 'reviewer': 'resources',
             'resources': 'package', 'package': 'delivery'}


def acceptance():
    return importlib.import_module('localization_acceptance')


def compact_inspection(value):
    """Keep the full rows in the immutable task file, not in queue state/log output."""
    return {k: v for k, v in value.items() if k not in {'corpus', 'missingIds'}}


def compact_progress(value):
    hidden = {'authoredPairHashes', 'workTokens'}
    counts = dict(value.get('machineBaselineCounts', {}))
    counts.update({k: len(value[k]) for k in hidden if k in value})
    return {**{k: v for k, v in value.items() if k not in hidden},
            'machineBaselineCounts': counts}


def pipeline_snapshot(run, config):
    snapshot = run / config['pipelineSnapshotDirectory']
    if queue.artifacts([snapshot]) != config['pipelineSnapshotHashes']:
        raise RuntimeError('Pinned pipeline snapshot changed; no dispatch allowed')
    return snapshot


def freeze_acceptance_integration(root, snapshot):
    """Pin later-loaded code and bridge native authored-vs-visible accounting.

    The independent engineer's checkout may still be completing its report. Preserve
    that execution version; apply these queue integrations only to the immutable copy.
    This recipe reproduces the copy instead of hand-patching a running helper.
    """
    path = snapshot / 'localization_acceptance.py'
    source = path.read_text()
    changes = [
        ("sys.path.insert(0, str(root/'tools'))", "sys.path.insert(0, sys.argv[4])"),
        ("str(root), locale, FROZEN]", "str(root), locale, FROZEN, str(Path(__file__).resolve().parent)]"),
        ("result['authoredVisible'] = len(result['corpus'])", "result['authoredVisible'] = len(result['corpus'])\n        result['authoredTotal'] = len(authored)"),
        ("actual.get('authoredEntries') == info['authoredVisible']", "actual.get('authoredEntries') == info.get('authoredTotal', info['authoredVisible'])"),
        ("adapter = _safe(ev.root, 'tools/multilingual/delivery/native_delivery.py')", "adapter = Path(NATIVE_DELIVERY_ENTRY) if NATIVE_DELIVERY_ENTRY else _safe(ev.root, 'tools/multilingual/delivery/native_delivery.py')"),
        ("for path in sorted(directory.glob('*/receipt.json')):", "for path in sorted(directory.glob('*/receipt.json')):\n        if _queue_record_rejected(root, locale, path.parent.name, queue_row):\n            continue"),
    ]
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('Acceptance integration boundary changed: ' + old)
        source = source.replace(old, new)
    source += '''

# The queue's actual outcomes take precedence over an unvalidated receipt file.
NATIVE_DELIVERY_ENTRY = None

def _queue_record_rejected(root, locale, task_id, queue_row=None):
    queue_row = _queue_locale_state(root, locale) if queue_row is None else queue_row
    for record in queue_row.get('attempts', []):
        if record.get('taskId') == task_id and record.get('pipelineRevision') == 2:
            return record.get('status') not in {'continue', 'stage-complete', 'blocked'}
    return False
'''
    compile(source, str(path), 'exec')
    path.write_text(source)
    shutil.copy2(root / 'tools/authoring_omissions.py', snapshot / 'authoring_omissions.py')
    shutil.copy2(root / 'tools/native_checkpoint.py', snapshot / 'native_checkpoint.py')
    shutil.copy2(root / 'tools/test_localization_acceptance.py', snapshot / 'test_localization_acceptance.py')
    result = subprocess.run([sys.executable, '-B', str(snapshot / 'test_localization_acceptance.py')],
                            text=True, capture_output=True, cwd=root)
    (snapshot / 'acceptance-tests.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('Frozen integrated acceptance tests failed; inspect ' + str(snapshot / 'acceptance-tests.log'))
    return {'sourceSha256': queue.digest(root / 'tools/localization_acceptance.py'),
            'integratedSha256': queue.digest(path), 'changes': [old for old, _ in changes],
            'testLog': str(snapshot / 'acceptance-tests.log')}


def ensure_glossary(root, locale, master):
    """Reuse existing snapshots; canonical content remains separately owned."""
    path = root / 'translation' / locale / 'glossary-snapshot.json'
    if path.exists():
        return
    command = [str(master / 'vnrevival'), 'glossary', 'work', 'omori', locale]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Canonical glossary CLI failed: ' + result.stderr[-1000:])
    source_path = master / 'data/games/omori/glossary.json'
    source = queue.read(source_path)
    targets = queue.read(source_path.with_name('glossary-translations.json'))
    target = targets[locale]
    entries = source if isinstance(source, list) else source['entries']
    if set(target) != {e['id'] for e in entries}:
        raise ValueError('Canonical glossary target IDs differ')
    import hashlib
    queue.write(path, {'siteLocale': locale, 'sourceLocale': 'en', 'source': source,
                      'target': target, 'sourcePath': str(source_path),
                      'sourceRawSha256': queue.digest(source_path),
                      'targetLayerSha256': hashlib.sha256(json.dumps(target, ensure_ascii=False,
                          sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                      'provenance': 'Canonical files identified by glossary work; editorial acceptance is a separate gate.'})


def next_candidate(state, active_keys, shared_delivery_ready):
    """One lane owns one locale until delivery; stages never create extra lanes."""
    runnable = []
    for position, lane in enumerate(state['lanes']):
        locale = lane.get('locale')
        if not locale:
            continue
        row = state['locales'][locale]
        key = 'locale:' + locale
        if key in active_keys or row['status'] not in {'queued', 'waiting-native-adapter'}:
            continue
        role = row.get('workflow', {}).get('role', 'author')
        if role in {'resources', 'package'} and not shared_delivery_ready:
            row['status'] = 'waiting-native-adapter'
            continue
        priority = {'delivery': 0, 'package': 1, 'resources': 2,
                    'reviewer': 3, 'editor': 4, 'author': 5}[role]
        runnable.append((priority, position, locale))
    return min(runnable)[2] if runnable else None


def fill_lanes(state, capacity):
    """Release after final acceptance, or verified packaging under owner deferral."""
    lanes = state.setdefault('lanes', [{'id': i + 1, 'locale': None} for i in range(capacity)])
    if len(lanes) != capacity:
        raise ValueError('Lane capacity changed without an explicit migration')
    done = {'local-scope-complete'}
    if packaging_before_review(state):
        done.add('packaged-awaiting-review')
    occupied = {lane['locale'] for lane in lanes if lane.get('locale')}
    for lane in lanes:
        previous = lane.get('locale')
        if previous and state['locales'][previous]['status'] in done:
            lane.setdefault('completed', []).append(previous)
            lane['locale'] = None
        if lane.get('locale'):
            continue
        for locale, row in state['locales'].items():
            if locale not in occupied and row['status'] not in done:
                lane['locale'] = locale
                occupied.add(locale)
                break
    return lanes


def configure_review_schedule(root, run, config, state):
    """A hashed owner decision changes timing, never editorial acceptance."""
    ref = config.get('reviewScheduleDecision')
    if not ref:
        if state.get('reviewSchedule'):
            raise ValueError('Existing review schedule lost its owner binding')
        return
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(run.resolve()) or queue.digest(path) != ref['sha256']:
        raise ValueError('Owner review-schedule decision changed')
    decision = queue.read(path)
    if (decision.get('authority') != 'owner' or not decision.get('instruction')
            or decision.get('deferFullEditorialReview') is not True
            or decision.get('startReviewAfterAllPackages') is not True
            or set(decision.get('locales', [])) != set(state['locales'])):
        raise ValueError('Invalid owner batch-review schedule')
    schedule = state.setdefault('reviewSchedule', {'decision': ref, 'phase': 'packaging'})
    if schedule['decision'] != ref or schedule['phase'] not in {'packaging', 'reviewing'}:
        raise ValueError('Unreconciled review-schedule state')


def packaging_before_review(state):
    return state.get('reviewSchedule', {}).get('phase') == 'packaging'


def apply_locale_hold(row, hold):
    """Preserve in-flight work but stop dispatch/package after a new concrete defect."""
    workflow = row.setdefault('workflow', {})
    if hold is None:
        previous = workflow.pop('queueHold', None)
        if previous and row['status'] == 'blocked' and workflow.get('blockers') == [previous['reason']]:
            row['status'] = previous['status']
            if previous['blockers'] is None:workflow.pop('blockers', None)
            else:workflow['blockers'] = previous['blockers']
        return False
    if not isinstance(hold, dict) or not isinstance(hold.get('reason'), str) or not hold['reason'].strip():
        raise ValueError('Locale hold requires a concrete reason')
    if row['status'] != 'running':
        workflow.setdefault('queueHold', {'status': row['status'], 'blockers': workflow.get('blockers'), 'reason': hold['reason']})
        row['status'] = 'blocked';workflow['blockers'] = [hold['reason']]
    return True


def route_review_schedule(state, row):
    if row['status'] not in {'queued', 'waiting-native-adapter'}:
        return
    workflow = row.setdefault('workflow', {'role': 'author', 'stage': 'translate-edit'})
    role = workflow['role']
    if packaging_before_review(state) and role in {'editor', 'reviewer'}:
        workflow.setdefault('deferredEditorialRole', role)
        workflow.update(role='resources', stage='resources')
    elif state.get('reviewSchedule', {}).get('phase') == 'reviewing' and role in {'resources', 'package'}:
        progress = workflow.get('progress', {})
        if progress.get('resourcesVerified') and progress.get('nativeArchiveVerified'):
            # Current binding checks invalidate these flags after actual text edits.
            workflow.update(role='delivery', stage='delivery')


def advance_review_batch(state):
    if not packaging_before_review(state) or not state['locales']:
        return False
    if not all(row['status'] in {'packaged-awaiting-review', 'local-scope-complete'}
               for row in state['locales'].values()):
        return False
    state['reviewSchedule'].update(phase='reviewing', startedAt=queue.stamp())
    for row in state['locales'].values():
        if row['status'] == 'packaged-awaiting-review':
            row['status'] = 'queued'
            row['workflow'].update(role='editor', stage='editorial')
    for lane in state.get('lanes', []):
        lane['locale'] = None
    return True


def initialize_locale(root, locale, row, master):
    ensure_glossary(root, locale, master)
    info = acceptance().inspect_locale(root, locale)
    if info.get('errors'):
        raise ValueError('Existing authored inputs fail preflight: ' + json.dumps(info['errors'])[:1500])
    old = row.setdefault('workflow', {})
    old.setdefault('revision', 2)
    old.setdefault('role', 'editor' if info['authoredVisible'] == info['totalVisible'] else 'author')
    old['stage'] = ROLE_STAGE.get(old['role'], 'delivery')
    old['coverage'] = compact_inspection(info)
    row['status'] = 'queued'
    # Historical failures/blockers remain in old attempts; they are not a new final verdict.
    if row.get('error'):
        old.setdefault('legacyObserverError', row.pop('error'))
    return info


def create_task(root, run, config, state, locale, precomputed=None):
    row = state['locales'][locale]
    route_review_schedule(state, row)
    info = precomputed[0] if precomputed else acceptance().inspect_locale(root, locale)
    role = row['workflow']['role']
    number = len(row['attempts']) + 1
    task_id = '%s-%s-%04d' % (locale, role, number)
    folder = root / 'translation' / locale / 'pipeline/tasks' / task_id
    if folder.exists():
        raise RuntimeError('Task identity already exists; reconcile unknown creation outcome')
    candidate = row['workflow'].get('resourceCandidate') if role == 'resources' else None
    if candidate:
        path = acceptance()._safe(root, candidate['path'], locale)
        if queue.digest(path) != candidate['sha256']:
            raise ValueError('Pinned resource candidate changed before dispatch')
    previous = precomputed[1] if precomputed else acceptance().progress_snapshot(root, locale)
    # Replaying saved evidence can take minutes. Do it before reserving an identity;
    # an observer handoff during replay must not leave an empty dispatched-task shell.
    folder.mkdir(parents=True)
    bindings = {k: info[k] for k in ['inventorySha256', 'glossarySha256', 'corpusSha256']}
    task = {'schemaVersion': 2, 'id': task_id, 'sequence': number, 'locale': locale, 'role': role,
            'stage': ROLE_STAGE[role], 'inputBindings': bindings, 'previousProgress': previous,
            'inputs': compact_inspection(info), 'created': queue.stamp(),
            'receiptPath': str(folder / 'receipt.json'),
            'runtimeRisk': 'accepted-static; actual runtime/visual remain not-run',
            'independentReviewAuthorized': True}
    if config.get('mediaScopeDecision'):
        task['mediaScopeDecision'] = config['mediaScopeDecision']
    if state.get('reviewSchedule'):
        task['reviewSchedule'] = state['reviewSchedule']
        if row['workflow'].get('deferredWork'):
            task['savedReviewWork'] = row['workflow']['deferredWork']
    snapshot = pipeline_snapshot(run, config)
    task['contractPath'] = str(snapshot / 'acceptance-contract.json')
    task['contractSha256'] = queue.digest(snapshot / 'acceptance-contract.json')
    if row.get('workflow', {}).get('receiptRepair'):
        task['receiptRepair'] = row['workflow']['receiptRepair']
    if candidate:
        task['resourceCandidate'] = candidate
    queue.write(folder / 'task.json', task)
    queue.write(folder / 'corpus.json', info['corpus'])
    queue.write(folder / 'missing-ids.json', info['missingIds'])
    attempt = run / 'jobs' / locale / ('attempt-%04d' % number)
    attempt.mkdir(parents=True)
    task['attemptDirectory'] = str(attempt)
    queue.write(folder / 'task.json', task)
    write_task_brief(task, folder)
    return task, folder, attempt


def write_task_brief(task, folder):
    """Expose finite work, keeping per-pair machine baselines out of model context."""
    previous = task.get('previousProgress', {})
    hidden = {'authoredPairHashes', 'workTokens'}
    brief = dict(task)
    brief['previousProgress'] = {k: v for k, v in previous.items() if k not in hidden}
    brief['machineBaselineCounts'] = {k: len(previous[k]) for k in hidden if k in previous}
    brief['fullTaskPath'] = str(folder / 'task.json')
    brief['view'] = 'Operational brief only. Load full task.json in Python for receipt validation; never print its per-pair hash/token arrays.'
    queue.write(folder / 'brief.json', brief)


def render_prompt(root, run, config, locale, task, folder):
    snapshot = pipeline_snapshot(run, config)
    template = (snapshot / 'pipeline-worker.md').read_text()
    values = {'ROOT': root, 'MASTER': config.get('master', queue.MASTER), 'RUN': run, 'LOCALE': locale,
              'ROLE': task['role'], 'TASK': folder / 'brief.json', 'TASK_DIR': folder,
              'CONTRACT': snapshot / 'acceptance-contract.json',
              'AUTHOR_TOOLS': run / config['toolingDirectory'],
              'DELIVERY_TOOLS': run / config.get('deliveryToolingDirectory', 'delivery-not-yet-frozen'),
              'PIPELINE_TOOLS': snapshot,
              'MEDIA_SCOPE': 'Images and movies excluded by the explicit owner decision in the task.' if config.get('mediaScopeDecision') else 'Preserve the existing full-media scope.',
              'REVIEW_SCHEDULE': ('Owner defers full semantic/editorial and independent review until ALL locales have verified text/font/native packages. Current phase: ' + state_phase)
                  if (state_phase := task.get('reviewSchedule', {}).get('phase')) else 'Normal per-locale editorial sequence.'}
    for key, value in values.items():
        template = template.replace('{{' + key + '}}', str(value))
    return template


def launch_locale(root, run, config, state, locale, observer_fd, precomputed=None):
    task, folder, attempt = create_task(root, run, config, state, locale, precomputed)
    (attempt / 'prompt.md').write_text(render_prompt(root, run, config, locale, task, folder))
    snapshot = pipeline_snapshot(run, config)
    writable = [root / area / locale for area in ['translation', 'build', 'dist']]
    writable.extend([root / 'runtime/multilingual/locales' / locale, attempt])
    writable.append(root / 'build/multilingual-delivery' / locale)
    for path in writable:
        path.mkdir(parents=True, exist_ok=True)
    fd = queue.acquire(run / 'locks' / (locale + '.lock'))
    result = attempt / 'result.json'
    args = queue.command(config['codex'], root / 'translation' / locale,
                         result, snapshot / 'pipeline-result.schema.json', writable)
    try:
        with (attempt / 'prompt.md').open() as stdin, (attempt / 'events.jsonl').open('w') as stdout, \
                (attempt / 'stderr.log').open('w') as stderr:
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                                    pass_fds=(observer_fd, fd), start_new_session=True)
    except BaseException:
        os.close(fd)
        raise
    record = {'number': len(state['locales'][locale]['attempts']) + 1, 'pipelineRevision': 2,
              'taskId': task['id'], 'taskPath': str(folder / 'task.json'), 'role': task['role'],
              'status': 'running', 'started': queue.stamp(), 'pid': proc.pid,
              'processGroup': proc.pid, 'command': args, 'resultPath': str(result),
              'eventsPath': str(attempt / 'events.jsonl')}
    row = state['locales'][locale]
    row['attempts'].append(record)
    row['status'] = 'running'
    queue.write(run / 'state.json', state)
    return {'process': proc, 'fd': fd, 'record': record, 'task': task}


def validate_response(root, locale, record, task):
    response = queue.read(record['resultPath'])
    if response.get('taskId') != task['id'] or response.get('role') != task['role']:
        raise ValueError('Response belongs to a different task/role')
    if response.get('status') not in {'continue', 'blocked', 'stage-complete'}:
        raise ValueError('Unknown pipeline disposition; locale cannot return shared prepared')
    receipt = (root / response['receipt']).resolve()
    expected = Path(task['receiptPath']).resolve()
    if receipt != expected or not receipt.is_relative_to((root / 'translation' / locale).resolve()):
        raise ValueError('Receipt identity/locale differs')
    saved = queue.read(receipt)
    repair_timeout = False
    diagnostic = receipt.parent / 'gate-failure.json'
    if saved.get('disposition') != response['status']:
        if response['status'] == 'blocked' and task['role'] == 'author' and saved.get('disposition') in {'continue', 'stage-complete'} and not saved.get('blockers') and diagnostic.is_file():
            evidence = queue.read(diagnostic)
            repair_timeout = (evidence.get('status') == 'receipt-rejected-validation-timeout'
                and evidence.get('taskId') == task['id'] and evidence.get('sessionId') == saved.get('sessionId')
                and {'path': str(receipt.relative_to(root)), 'sha256': queue.digest(receipt)} in evidence.get('evidence', []))
        if not repair_timeout:
            raise ValueError('Response disposition differs from saved task receipt')
    measured = record['usage']
    if not measured.get('session') or not measured.get('tokens'):
        raise ValueError('No successful terminal CLI turn/session identity')
    result = acceptance().validate_receipt(root, locale, task['role'], receipt,
                                           task, measured['session'])
    if repair_timeout:
        if result.get('blockers') or not result.get('meaningfulProgress'):
            raise ValueError('Saved timeout handoff has not passed coordinator validation: ' + '; '.join(result.get('blockers', [])))
        record['responseNormalization'] = {'reason': 'Coordinator validated the unchanged saved handoff after worker-side timeout; original blocked response retained.',
            'originalResultSha256': queue.digest(record['resultPath']), 'diagnosticSha256': queue.digest(diagnostic),
            'receiptSha256': queue.digest(receipt), 'normalizedDisposition': saved['disposition']}
        response = dict(response, status=saved['disposition'])
    if response['status'] == 'stage-complete' and not result['roleComplete']:
        raise ValueError('Claimed stage completion lacks its actual acceptance evidence: ' + '; '.join(result.get('blockers', [])))
    if response['status'] == 'continue' and not result['meaningfulProgress']:
        raise ValueError('No measured authoring/review/finite-work progress; report-only continuation rejected: ' + '; '.join(result.get('blockers', [])))
    if response['status'] != 'stage-complete' and result['roleComplete']:
        # A real completed stage must advance instead of starting another self-read.
        response = dict(response, status='stage-complete')
    return response, result


def bind_session(job):
    """Use the CLI's real session identity; never let a model invent independence."""
    task = job.get('task')
    if task is None or task.get('sessionId'):
        return
    path = Path(job['record']['eventsPath'])
    if not path.is_file():
        return
    with path.open() as stream:
        for _, line in zip(range(20), stream):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get('type') == 'thread.started' and event.get('thread_id'):
                task['sessionId'] = event['thread_id']
                queue.write(job['record']['taskPath'], task)
                write_task_brief(task, Path(job['record']['taskPath']).parent)
                job['record']['sessionId'] = task['sessionId']
                return


def apply_transition(row, record, response, validated):
    workflow = row['workflow']
    record['status'] = response['status']
    progress = compact_progress(validated.get('progress', {}))
    if record.get('resultPath'):
        raw = json.dumps(validated, ensure_ascii=False, sort_keys=True).encode()
        import hashlib
        archive = Path(record['resultPath']).parent / ('validation-' + hashlib.sha256(raw).hexdigest()[:16] + '.json')
        if not archive.exists():queue.write(archive, validated)
        record['validationSnapshot'] = {'path': str(archive), 'sha256': queue.digest(archive)}
    record['validation'] = dict(validated, progress=progress)
    workflow['progress'] = progress
    workflow['lastReceipt'] = response['receipt']
    workflow['lastSession'] = record['usage']['session']
    workflow.pop('receiptRepair', None)
    row['summary'] = response
    if response['status'] == 'blocked':
        row['status'] = 'blocked'
        workflow['blockers'] = validated.get('blockers') or [response.get('summary', 'Concrete external blocker')]
    elif response['status'] == 'stage-complete':
        role = validated.get('nextRole') or NEXT_ROLE[record['role']]
        if role not in set(ROLES) | {'delivery'}:
            raise ValueError('Unknown next role')
        workflow['role'] = role
        workflow['stage'] = ROLE_STAGE.get(role, 'delivery')
        workflow.pop('blockers', None)
        row['status'] = 'queued'
    else:
        row['status'] = 'queued'


def finish_locale(root, run, state, locale, job, validation_config=None):
    record = job['record']
    proc = job['process']
    row = state['locales'][locale]
    record.update(finished=queue.stamp(), usage=queue.usage(record['eventsPath']),
                  exitCode=proc.returncode, exitCodeObserved=not getattr(proc, 'adopted', False))
    try:
        if proc.returncode not in {0, None}:
            if queue.rate_limit_failure(record['eventsPath']):
                queue.schedule_rate_limit(row, record)
                return
            raise ValueError('CLI failed; preserve saved work and unknown side effects, no blind retry')
        response, validated = validate_response(root, locale, record, job['task'])
        apply_transition(row, record, response, validated)
        row['consecutiveRateLimitFailures'] = 0
        row.pop('error', None)
    except Exception as exc:
        row['status'] = 'needs-attention'
        row['error'] = str(exc)
        record['status'] = 'needs-attention'
        # Only the known bootstrap capsule has an older contract. Reconcile its
        # successful saved work once using the finalized contract; never retranslate
        # or blindly retry a failed/unknown model turn.
        config = validation_config or queue.read(run / 'config.json')
        old_contract = task_contract(record, job['task'], run, config)
        new_contract = run / config.get('pipelineSnapshotDirectory', '') / 'acceptance-contract.json'
        if (record['usage'].get('tokens') and Path(record['resultPath']).is_file()
                and old_contract and new_contract.is_file()
                and old_contract != queue.digest(new_contract)):
            row['workflow']['receiptRepair'] = {'originalTask': record['taskPath'],
                'originalResult': record['resultPath'], 'originalReceipt': job['task']['receiptPath'],
                'oldContractSha256': old_contract, 'newContractSha256': queue.digest(new_contract),
                'rejection': str(exc),
                'instruction': 'Reconcile saved genuine reads/wording under the finalized schema using importReads/legacy evidence. Preserve original bytes, do not repeat valid semantic reading or claim its original completion.'}
            row['status'] = 'queued'
            record['status'] = 'contract-reconciliation'
    finally:
        if job.get('fd') is not None:
            os.close(job['fd'])
        queue.write(run / 'state.json', state)


def task_contract(record, task, run, config):
    if task.get('contractSha256'):
        return task['contractSha256']
    capsule = config.get('bootstrapTaskSnapshotDirectory')
    path = run / capsule / 'acceptance-contract.json' if capsule else None
    return queue.digest(path) if path and path.is_file() and record.get('pipelineRevision') == 2 else None


def finalize_locale(root, run, state, locale):
    row = state['locales'][locale]
    verdict = acceptance().completion(root, locale)
    row['workflow']['delivery'] = verdict
    if packaging_before_review(state):
        required = {'visibleCorpus', 'protectedNativeResources', 'nativeArchiveVerification'}
        gates = verdict.get('gates', {})
        failed = sorted(key for key in required if gates.get(key) is not True)
        if gates.get('ownerScopeBinding') is False:
            failed.append('ownerScopeBinding')
        row['workflow']['batchCandidate'] = {
            'status': 'packaged-awaiting-review' if not failed and not verdict.get('blockers') else 'blocked',
            'decision': state['reviewSchedule']['decision'],
            'technicalRequiredGates': sorted(required), 'remainingTechnicalGates': failed,
            'pendingEditorialGates': [key for key in verdict.get('remainingGates', []) if key not in required],
            'editorialAcceptance': 'deferred-until-all-packages', 'recordedAt': queue.stamp()}
        if not failed and not verdict.get('blockers'):
            row['status'] = 'packaged-awaiting-review'
            row['workflow']['stage'] = 'package'
            row['workflow'].pop('blockers', None)
        else:
            row['status'] = 'blocked'
            row['workflow']['blockers'] = verdict.get('blockers') or failed
    elif verdict.get('ready'):
        row['status'] = 'local-scope-complete'
        row['workflow']['stage'] = 'delivery'
        row['workflow']['completedAt'] = queue.stamp()
    else:
        row['status'] = 'blocked'
        row['workflow']['blockers'] = verdict.get('blockers') or verdict.get('remainingGates') or ['Final delivered-artifact acceptance is incomplete']
    queue.write(run / 'state.json', state)


def package_locale_checkpoint(root, run, state, locale):
    """Package mechanically once, using the accepted source-bound native build."""
    if not acceptance()._owner_checkpoint_reuse(root, locale):return False
    from native_checkpoint import digest, load, package_once, verify_checkpoint
    row = state['locales'][locale]
    accepted = next((a for a in reversed(row['attempts']) if a.get('role') == 'resources'
        and a.get('status') == 'stage-complete' and a.get('validation', {}).get('roleComplete')), None)
    if not accepted:raise ValueError('No accepted native resources checkpoint for ' + locale)
    task = queue.read(accepted['taskPath']);resource = queue.read(task['receiptPath'])
    ref = resource['work']['buildManifest'];manifest = root / ref['path']
    if digest(manifest) != ref['sha256']:raise ValueError('Accepted resources manifest changed')
    existing = []
    for path in sorted((root / 'build/multilingual-delivery' / locale).glob('*.zip.receipt.json')):
        doc = load(path)
        if doc.get('buildManifestSha256') == ref['sha256']:
            existing.append((path, doc))
    if existing:
        verification, doc = existing[0];archive = Path(doc['archive'])
        verify_checkpoint(root, locale, manifest.parent, archive, verification)
    else:
        archive = root / 'build/multilingual-delivery' / locale / ('omori-' + locale + '-' + ref['sha256'][:12] + '.zip')
        doc = package_once(root, locale, manifest.parent, archive);verification = Path(doc['receipt'])
    info = acceptance().inspect_locale(root, locale)
    destination = root / 'dist' / locale / ('OMORI-' + locale + '-8879120.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    archive_hash = digest(archive)
    if destination.exists() and digest(destination) != archive_hash:
        destination = destination.with_name(destination.stem + '-' + archive_hash[:12] + '.zip')
    if not destination.exists():
        with archive.open('rb') as source, destination.open('xb') as target:
            shutil.copyfileobj(source, target)
    if digest(destination) != archive_hash:raise ValueError('Delivered ZIP copy differs')
    row['workflow']['machinePackageCheckpoint'] = {
        'bindings': {k: info[k] for k in ('inventorySha256', 'glossarySha256', 'corpusSha256')},
        'manifest': ref,
        'archive': {'path': str(archive.relative_to(root)), 'sha256': digest(archive)},
        'verification': {'path': str(verification.relative_to(root)), 'sha256': digest(verification)},
        'origin': 'deterministic queue packaging; no model completion or editorial claim',
        'deliveredArchive': str(destination.relative_to(root)),
        'recordedAt': queue.stamp()}
    row['workflow'].update(role='delivery', stage='package')
    queue.write(run / 'state.json', state)
    return True


def tracked_tree(pid, processes):
    found = {pid} if pid in processes else set()
    while True:
        extra = {p for p, row in processes.items() if row['ppid'] in found} - found
        if not extra:
            break
        found.update(extra)
    return {str(p): processes[p] for p in found}


def observed_job_processes(record, processes):
    """Include surviving recorded children and the task's own process group."""
    found = {}
    for raw_pid, old in record.get('processTree', {}).items():
        pid = int(raw_pid)
        current = processes.get(pid)
        if current and current['started'] == old['started'] and not current.get('state', '').startswith('Z'):
            found[str(pid)] = current
    parent = processes.get(record['pid'])
    if parent and record['resultPath'] in parent['command'] and not parent.get('state', '').startswith('Z'):
        found.update(tracked_tree(record['pid'], processes))
    for pid, current in processes.items():
        if current.get('pgid') == record.get('processGroup') and not current.get('state', '').startswith('Z'):
            found[str(pid)] = current
            found.update(tracked_tree(pid, processes))
    return found


def commands_finished(path):
    started, completed = set(), set()
    for line in Path(path).read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get('item', {})
        if item.get('type') != 'command_execution':
            continue
        if event.get('type') == 'item.started':
            started.add(item.get('id'))
        elif event.get('type') == 'item.completed':
            completed.add(item.get('id'))
    return started <= completed


def reconcile_finished_locale(root, run, state, locale, validation_config=None):
    row = state['locales'][locale]
    latest = row['attempts'][-1]
    if not commands_finished(latest['eventsPath']):
        row['status'] = 'needs-attention'
        row['error'] = 'An invoked CLI command has no terminal event; reconcile before continuation'
        return
    task = queue.read(latest['taskPath'])
    fake = type('ExitedUnobserved', (), {'adopted': True, 'returncode': None})()
    job = {'process': fake, 'fd': None, 'record': latest, 'task': task}
    bind_session(job)
    finish_locale(root, run, state, locale, job, validation_config)


def adopt_existing(run, config, state):
    """Unknown jobs never become new requests; preserve process birth and children."""
    manifest = queue.read(run / config['pipelineAdoptionManifest']) if config.get('pipelineAdoptionManifest') else {}
    active = {}
    for locale, row in state['locales'].items():
        if row['status'] != 'running':
            continue
        key = 'locale:' + locale
        record = row['attempts'][-1]
        pinned = manifest.get(key)
        if not pinned or pinned['pid'] != record['pid'] or pinned['resultPath'] != record['resultPath']:
            raise RuntimeError('Unreconciled live locale job: ' + locale)
        if record.get('pipelineRevision') != 2:
            raise RuntimeError('Old generic assignments must be reconciled before role-based continuation')
        active[key] = {'process': queue.AdoptedProcess(pinned['processes']), 'fd': None,
                       'record': record, 'task': queue.read(record['taskPath'])}
    for name, row in state.get('sharedTasks', {}).items():
        if row['status'] != 'running':
            continue
        key = 'shared:' + name
        record = row['attempts'][-1]
        pinned = manifest.get(key)
        if not pinned or pinned['pid'] != record['pid'] or pinned['resultPath'] != record['resultPath']:
            raise RuntimeError('Unreconciled shared engineering job: ' + name)
        active[key] = {'process': queue.AdoptedProcess(pinned['processes']), 'fd': None, 'record': record}
    return active


def finish_shared(root, run, config, state, name, job):
    """Engineering output is preserved for technical acceptance, never a locale pass."""
    row = state['sharedTasks'][name]
    record = job['record']
    record.update(finished=queue.stamp(), usage=queue.usage(record['eventsPath']),
                  exitCode=job['process'].returncode,
                  exitCodeObserved=not getattr(job['process'], 'adopted', False))
    try:
        if job['process'].returncode not in {0, None} or not record['usage'].get('tokens'):
            raise ValueError('Shared engineering result has no verified successful CLI terminal turn')
        response = queue.read(record['resultPath'])
        row['summary'] = response
        if response['status'] != 'local-scope-complete':
            raise ValueError('Shared engineering requires coordinator acceptance: ' + response.get('summary', ''))
        for item in response.get('evidence', []):
            p = (root / item).resolve()
            if not p.is_relative_to(root) or not p.is_file():
                raise ValueError('Missing shared engineering evidence')
        row['status'] = 'awaiting-technical-acceptance'
        record['status'] = response['status']
    except Exception as exc:
        row['status'] = 'needs-attention'
        row['error'] = str(exc)
        record['status'] = 'needs-attention'
    queue.write(run / 'state.json', state)


def upgrade(run):
    """Migrate the same run after verified interruption, preserving all old records."""
    identity = queue.read(run / 'snapshot/identity.json')
    root, master = Path(identity['root']), Path(identity['master'])
    config, state = queue.read(run / 'config.json'), queue.read(run / 'state.json')
    if state['status'] != 'repairing':
        raise RuntimeError('Upgrade requires the reconciled stopped queue; never replace a live observer')
    processes = queue.process_snapshot()
    old_observer = state.get('supervisorPid')
    if old_observer in processes and str(run) in processes[old_observer]['command']:
        raise RuntimeError('Original observer still exists')
    adoption = {}
    for locale, row in state['locales'].items():
        if row.get('attempts'):
            previous = row['attempts'][-1]
            owned = observed_job_processes(previous, processes)
            if owned:
                if previous.get('pipelineRevision') != 2:
                    raise RuntimeError('Original generic locale process still exists: ' + locale)
                adoption['locale:' + locale] = {'pid': previous['pid'], 'resultPath': previous['resultPath'],
                                               'processes': owned}
    contract = root / 'runtime/multilingual/shared-acceptance/CONTRACT.json'
    if not contract.is_file() or queue.read(contract).get('status') not in {'implemented', 'implemented-tested', 'ready', 'passed'}:
        raise RuntimeError('Acceptance adapter implementation/contract must be verified before migration')
    version = 1
    while (run / ('snapshot-pipeline-v%d' % version)).exists():
        version += 1
    snapshot = run / ('snapshot-pipeline-v%d' % version)
    snapshot.mkdir()
    for name in ['localization_pipeline.py', 'localization_cli.py', 'localization_acceptance.py']:
        shutil.copy2(root / 'tools' / name, snapshot / name)
    for name in ['pipeline-worker.md', 'pipeline-result.schema.json']:
        shutil.copy2(root / 'tools/cli-localization' / name, snapshot / name)
    shutil.copy2(contract, snapshot / 'acceptance-contract.json')
    integration = freeze_acceptance_integration(root, snapshot)
    queue.write(snapshot / 'queue-integration.json', integration)
    # Reconciliation below uses the same accepted, frozen implementation as dispatch.
    import importlib.util
    spec = importlib.util.spec_from_file_location('localization_acceptance', snapshot / 'localization_acceptance.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules['localization_acceptance'] = module
    spec.loader.exec_module(module)
    queue.write(run / ('config-before-pipeline-v%d.json' % version), config)
    queue.write(run / ('state-before-pipeline-v%d.json' % version), state)
    for name, row in state.get('sharedTasks', {}).items():
        if row['status'] != 'running':
            continue
        record = row['attempts'][-1]
        tree = tracked_tree(record['pid'], processes)
        if tree:
            if record['resultPath'] not in processes[record['pid']]['command']:
                raise RuntimeError('Shared task PID identity differs: ' + name)
            adoption['shared:' + name] = {'pid': record['pid'], 'resultPath': record['resultPath'], 'processes': tree}
        else:
            # Reconcile the known engineering submission; never submit another copy.
            fake = type('ExitedUnobserved', (), {'adopted': True, 'returncode': None})()
            finish_shared(root, run, config, state, name, {'process': fake, 'record': record})
    adoption_path = 'pipeline-adoption-v%d.json' % version
    queue.write(run / adoption_path, adoption)
    config.update(pipelineRevision=2, pipelineSnapshotDirectory=snapshot.name,
                  pipelineSnapshotHashes=queue.artifacts([snapshot]),
                  pipelineAdoptionManifest=adoption_path, master=str(master),
                  queueLockFile='queue-pipeline-v%d.lock' % version,
                  ownerOverride='One dedicated lane per localization through verified final native package; independent sequential review authorized; next locale starts only after completion.')
    native = run / 'tooling-delivery-v1'
    if (native / 'freeze.json').is_file():
        config['deliveryToolingDirectory'] = native.name
        config['deliveryToolingHashes'] = queue.artifacts([native])
        module.NATIVE_DELIVERY_ENTRY = native / 'tools/multilingual/delivery/native_delivery.py'
    # Validate every started lane before resuming. Unstarted languages initialize lazily.
    for locale, row in state['locales'].items():
        if 'locale:' + locale in adoption:
            continue
        if row.get('attempts') and row['attempts'][-1].get('pipelineRevision') == 2:
            if row['status'] == 'running':
                reconcile_finished_locale(root, run, state, locale, config)
            continue
        if row.get('attempts'):
            initialize_locale(root, locale, row, master)
        else:
            row['status'] = 'queued'
            row['workflow'] = {'revision': 2, 'role': 'author', 'stage': 'translate-edit', 'initialized': False}
    fill_lanes(state, config['jobs'])
    state['status'] = 'pipeline-prepared'
    queue.write(run / 'config.json', config)
    queue.write(run / 'state.json', state)
    return {'run': str(run), 'snapshot': snapshot.name, 'lanes': state['lanes'], 'status': state['status']}


def bootstrap_lanes(run):
    """Start bounded linguistic work while one-time infrastructure tests finish.

    Each task gets its own immutable complete contract/capsule. It never imports the
    engineer's changing checkout. The final supervisor adopts these same exact jobs;
    it validates their receipts using the accepted adapter before advancing stages.
    """
    identity = queue.read(run / 'snapshot/identity.json')
    root, master = Path(identity['root']), Path(identity['master'])
    config, state = queue.read(run / 'config.json'), queue.read(run / 'state.json')
    if state['status'] != 'repairing' or config.get('bootstrapTaskSnapshotDirectory'):
        raise RuntimeError('Reconcile existing bootstrap submission before another launch')
    processes = queue.process_snapshot()
    active_keys = set()
    for name, row in state.get('sharedTasks', {}).items():
        if row['status'] == 'running':
            record = row['attempts'][-1]
            if record['pid'] not in processes or record['resultPath'] not in processes[record['pid']]['command']:
                raise RuntimeError('Reconcile engineering outcome before linguistic dispatch: ' + name)
            active_keys.add('shared:' + name)
    for locale, row in state['locales'].items():
        if row['status'] == 'running':
            raise RuntimeError('Unexpected existing locale writer: ' + locale)
    folder = run / 'snapshot-locale-capsules-v1'
    folder.mkdir()
    for name in ['pipeline-worker.md', 'pipeline-result.schema.json']:
        shutil.copy2(root / 'tools/cli-localization' / name, folder / name)
    shutil.copy2(root / 'runtime/multilingual/shared-acceptance/CONTRACT.json', folder / 'acceptance-contract.json')
    # Freeze the existing implementation used only to prepare input capsules. Workers
    # use the contract and original frozen authoring helpers, not changing canonical code.
    shutil.copy2(root / 'tools/localization_acceptance.py', folder / 'localization_acceptance.py')
    local_config = dict(config, pipelineSnapshotDirectory=folder.name,
                        pipelineSnapshotHashes=queue.artifacts([folder]), master=str(master))
    config.update(bootstrapTaskSnapshotDirectory=folder.name,
                  bootstrapTaskSnapshotHashes=local_config['pipelineSnapshotHashes'])
    queue.write(run / 'config.json', config)
    for row in state['locales'].values():
        if row['status'] != 'local-scope-complete':
            row['status'] = 'queued'
            row.setdefault('workflow', {'revision': 2, 'role': 'author', 'stage': 'translate-edit'})
    fill_lanes(state, config['jobs'])
    fd = queue.acquire(root / 'runtime/cli-localization/queue-bootstrap-v1.lock')
    try:
        # Preserve fixed lane order. Complete existing drafts go straight to their
        # remaining editorial work instead of translating introductory scenes again.
        for lane in state['lanes']:
            if len(active_keys) >= config['jobs']:
                break
            locale = lane['locale']
            ensure_glossary(root, locale, master)
            info = acceptance().inspect_locale(root, locale)
            if info['errors']:
                state['locales'][locale].update(status='needs-attention', error='; '.join(info['errors']))
                continue
            state['locales'][locale]['workflow'].update(
                role='editor' if info['authoredVisible'] == info['totalVisible'] else 'author',
                stage='editorial' if info['authoredVisible'] == info['totalVisible'] else 'translate-edit')
            progress = acceptance()._progress(info, acceptance()._record_state(root, locale, info))
            job = launch_locale(root, run, local_config, state, locale, fd, (info, progress))
            active_keys.add('locale:' + locale)
            print(json.dumps({'locale': locale, 'role': job['record']['role'], 'pid': job['record']['pid'],
                              'task': job['task']['id']}), flush=True)
            # Bind actual identity once available; final supervisor also does this.
            for _ in range(20):
                bind_session(job)
                if job['task'].get('sessionId'):
                    break
                time.sleep(0.1)
        queue.write(run / 'state.json', state)
    finally:
        os.close(fd)


def execute(run):
    identity = queue.read(run / 'snapshot/identity.json')
    root, master = Path(identity['root']), Path(identity['master'])
    config = queue.read(run / 'config.json')
    queue.ROOT, queue.MASTER, queue.CONTROL = root, master, root / 'runtime/cli-localization'
    fd = queue.acquire(queue.CONTROL / config['queueLockFile'])
    try:
        pipeline_snapshot(run, config)
        if config.get('deliveryToolingDirectory'):
            native = run / config['deliveryToolingDirectory']
            if queue.artifacts([native]) != config['deliveryToolingHashes']:
                raise RuntimeError('Pinned native delivery helper closure changed')
            acceptance().NATIVE_DELIVERY_ENTRY = native / 'tools/multilingual/delivery/native_delivery.py'
        state = queue.read(run / 'state.json')
        configure_review_schedule(root, run, config, state)
        active = adopt_existing(run, config, state)
        if len(active) > config['jobs']:
            raise RuntimeError('Existing owned processes exceed authorized concurrency')
        state.update(status='running', supervisorPid=os.getpid(), started=queue.stamp())
        queue.write(run / 'state.json', state)
        while True:
            # A small control file changes scheduling, never executing helper versions.
            control = queue.read(run / 'pipeline-control.json') if (run / 'pipeline-control.json').exists() else {}
            if control.get('pauseDispatch'):
                state['status'] = 'draining'
            for key in list(active):
                job = active[key]
                bind_session(job)
                if job['process'].poll() is None:
                    continue
                del active[key]
                if key.startswith('locale:'):
                    finish_locale(root, run, state, key[7:], job)
                else:
                    finish_shared(root, run, config, state, key[7:], job)
            for locale, row in state['locales'].items():
                if apply_locale_hold(row, control.get('localeHolds', {}).get(locale)):
                    continue
                if row['status'] == 'waiting-rate-limit' and time.time() >= row['retryNotBefore']:
                    row['status'] = 'queued'
                route_review_schedule(state, row)
                if config.get('nativeCheckpointDecision') and packaging_before_review(state) and row['status'] == 'queued' and row.get('workflow', {}).get('role') == 'package':
                    try:
                        package_locale_checkpoint(root, run, state, locale)
                    except Exception as exc:
                        row['status'] = 'needs-attention';row['error'] = str(exc)
                if row['status'] == 'queued' and row.get('workflow', {}).get('role') == 'delivery':
                    finalize_locale(root, run, state, locale)
            advance_review_batch(state)
            fill_lanes(state, config['jobs'])
            shared_ready = bool(config.get('deliveryToolingDirectory'))
            if not control.get('pauseDispatch'):
                while len(active) < config['jobs']:
                    # Creating another locale's bounded workset can take minutes.
                    # Publish already-started sessions before that blocking work.
                    for started_job in active.values():
                        bind_session(started_job)
                    locale = next_candidate(state, set(active), shared_ready)
                    if locale is None:
                        break
                    try:
                        if not (root / 'translation' / locale / 'glossary-snapshot.json').is_file():
                            initialize_locale(root, locale, state['locales'][locale], master)
                        active['locale:' + locale] = launch_locale(root, run, config, state, locale, fd)
                    except Exception as exc:
                        state['locales'][locale]['status'] = 'needs-attention'
                        state['locales'][locale]['error'] = str(exc)
                        queue.write(run / 'state.json', state)
            queue.write(run / 'state.json', state)
            if not active:
                if control.get('pauseDispatch'):
                    state['status'] = 'paused-dispatch'
                elif all(r['status'] == 'local-scope-complete' for r in state['locales'].values()):
                    state['status'] = 'complete'
                else:
                    state['status'] = 'waiting-for-concrete-blockers'
                queue.write(run / 'state.json', state)
                return
            time.sleep(2)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upgrade', action='store_true')
    parser.add_argument('--bootstrap-lanes', action='store_true')
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    if args.bootstrap_lanes:
        bootstrap_lanes(args.run.resolve())
    elif args.upgrade:
        print(json.dumps(upgrade(args.run.resolve()), indent=2))
    else:
        execute(args.run.resolve())


if __name__ == '__main__':
    main()
