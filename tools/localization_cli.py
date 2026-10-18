#!/usr/bin/env python3
"""Durable local Codex queue. Schedules work; never generates translation wording."""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
CONTROL = ROOT / 'runtime/cli-localization'
TEMPLATES = ROOT / 'tools/cli-localization'
MASTER = Path('/Users/antonkrutov/Desktop/SiteForMods')
LOCALES = ['es', 'es-419', 'pt-BR', 'de', 'fr', 'tr', 'zh-TW', 'pl', 'it',
           'th', 'vi', 'id', 'uk', 'ar', 'cs', 'hu', 'nl', 'fa', 'ro', 'hi',
           'fil', 'el', 'bg', 'sr', 'sw', 'he']
STAGES = ['scope', 'probe', 'source', 'glossary', 'translate-edit', 'editorial',
          'resources', 'package', 'runtime', 'delivery']


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def acquire(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise RuntimeError('Matching queue/worker is still live; reconcile status, do not duplicate it.')
    return fd


def artifacts(paths):
    found = {}
    for path in paths:
        path = Path(path)
        if path.is_file():
            found[str(path)] = digest(path)
        elif path.is_dir():
            for p in sorted(path.rglob('*')):
                if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts:
                    found[str(p)] = digest(p)
    return found


def usage(log):
    total = {'input': 0, 'cached_input': 0, 'output': 0, 'reasoning': 0, 'total': 0, 'completed_turns': 0}
    session = None
    if not Path(log).exists():
        return {'session': None, 'tokens': None}
    for line in Path(log).read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            session = event.get('thread_id')
        if event.get('type') != 'turn.completed' or not isinstance(event.get('usage'), dict):
            continue
        u = event['usage']
        if 'input_tokens' not in u or 'output_tokens' not in u:
            continue
        total['completed_turns'] += 1
        total['input'] += u['input_tokens']
        total['cached_input'] += u.get('cached_input_tokens', 0)
        total['output'] += u['output_tokens']
        if 'reasoning_output_tokens' in u and total['reasoning'] is not None:
            total['reasoning'] += u['reasoning_output_tokens']
        elif 'reasoning_output_tokens' not in u:
            total['reasoning'] = None
        total['total'] += u['input_tokens'] + u['output_tokens']
    return {'session': session, 'tokens': total if total['completed_turns'] else None}


def glossary_available(locale):
    # Structural precheck only. Actual editorial/source-version acceptance belongs to the worker.
    source = read(MASTER / 'data/games/omori/glossary.json')
    entries = source if isinstance(source, list) else source['entries']
    layer = read(MASTER / 'data/games/omori/glossary-translations.json').get(locale, {})
    return bool(layer) and len(layer) == len(entries) and set(layer) == {e['id'] for e in entries}


def terminal_provider_failure(log):
    """Classify only terminal429 or the exact provider capacity rejection."""
    failed = None
    succeeded = False
    if not Path(log).is_file():
        return None
    for line in Path(log).read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'turn.completed':
            succeeded = True
        if event.get('type') == 'turn.failed':
            message = event.get('error', {}).get('message', '')
            failed = ('terminal-429' if '429' in message and 'Too Many Requests' in message
                      else 'terminal-model-capacity' if message.strip() == 'Selected model is at capacity. Please try a different model.' else None)
    return failed if not succeeded else None


def rate_limit_failure(log):
    return terminal_provider_failure(log) is not None


def schedule_rate_limit(row, record):
    failures = row.get('consecutiveRateLimitFailures', 0) + 1
    row['consecutiveRateLimitFailures'] = failures
    capacity = terminal_provider_failure(record['eventsPath']) == 'terminal-model-capacity'
    label = 'Model capacity' if capacity else 'Provider429'
    record['providerFailure'] = 'terminal-model-capacity' if capacity else 'terminal-429'
    record['usage'] = usage(record['eventsPath'])
    if failures >= 3:
        row['status'] = 'needs-attention'
        row['error'] = label + ' recurred across three cooldown attempts; no further automatic retry.'
        return
    try:
        previous = datetime.fromisoformat(record['finished'].replace('Z', '+00:00')).timestamp()
    except (KeyError, ValueError):
        previous = time.time()
    row['status'] = 'waiting-rate-limit'
    row['retryNotBefore'] = previous + (600 if failures == 1 else 1800)
    row['error'] = ('Terminal model capacity' if capacity else 'Terminal provider429') + '; preserved checkpoint, cooldown before one fresh continuation on the same model.'
    record['status'] = 'waiting-rate-limit'


def command(binary, cwd, output, schema, writable):
    args = [binary, 'exec', '--skip-git-repo-check', '--json', '--color', 'never',
            '--approve-for-me', '-m', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="high"',
            '-c', 'model_provider="omori_https"',
            '-c', 'model_providers.omori_https={name="OpenAI HTTPS",wire_api="responses",requires_openai_auth=true,supports_websockets=false}',
            '-C', str(cwd), '--output-schema', str(schema), '-o', str(output)]
    for path in writable:
        args.extend(['--add-dir', str(path)])
    args.append('-')
    return args


def validate_result(result, root, kind):
    root = root.resolve()
    if result.get('status') not in {'continue', 'blocked', 'prepared', 'local-scope-complete'}:
        raise ValueError('Unknown worker disposition')
    paths = result.get('evidence', [])
    for relative in paths:
        path = (root / relative).resolve()
        continuation_directory = (result['status'] == 'continue' and path.is_dir()
                                  and any(p.is_file() and not p.is_symlink() for p in path.rglob('*')))
        if not path.is_relative_to(root.resolve()) or not (path.is_file() or continuation_directory):
            raise ValueError('Evidence missing or outside project: ' + relative)
        if kind != 'bootstrap' and not (any(path.is_relative_to(root / area / kind)
                                          for area in ['translation', 'build', 'dist']) or
                                          path.is_relative_to(root / 'runtime/multilingual/locales' / kind)):
            raise ValueError('Evidence belongs to another locale: ' + relative)
    if result['status'] in {'prepared', 'local-scope-complete'} and not paths:
        raise ValueError('Terminal result requires actual evidence files')
    if kind == 'bootstrap' and result['status'] == 'local-scope-complete':
        raise ValueError('Bootstrap must return prepared, not a locale completion')
    if kind != 'bootstrap' and result['status'] == 'prepared':
        raise ValueError('Locale worker cannot replace the shared preparation gate')
    return result


def validate_preparation(root):
    root = root.resolve()
    receipt = read(root / 'source/multilingual/acceptance.json')
    if receipt.get('source') != 'passed' or receipt.get('adapters') != 'passed':
        raise ValueError('Shared source/adapter gate did not pass')
    inventory = (root / receipt['inventoryPath']).resolve()
    if not inventory.is_relative_to(root / 'source/multilingual'):
        raise ValueError('Shared inventory must belong to source/multilingual')
    if digest(inventory) != receipt['inventorySha256']:
        raise ValueError('Shared inventory fingerprint differs')
    rows = read(inventory)
    if not isinstance(rows, list):
        raise ValueError('Shared inventory must contain the ordered unit array')
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('Duplicate shared source IDs')
    base = read(root / 'source/text-corpus-8879120-02/units.json')
    supplement = read(root / 'source/native-yaml-8879120-01/units.json')
    expected = base + supplement
    if len({r['id'] for r in expected}) != len(expected) or set(by_id) != {r['id'] for r in expected}:
        raise ValueError('Shared inventory must preserve the base and every native-YAML supplemental ID')
    for row in expected:
        if any(by_id[row['id']].get(key) != value for key, value in row.items()):
            raise ValueError('Original source record changed: ' + row['id'])
    evidence = receipt.get('evidence', [])
    if not evidence:
        raise ValueError('Preparation needs hashed source/adapter validation evidence')
    for item in evidence:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or digest(path) != item['sha256']:
            raise ValueError('Preparation evidence changed or missing')
    return receipt


def worker_result(record, root, locale):
    """Preserve raw output; separate the one known telemetry note from path evidence."""
    path = Path(record['resultPath'])
    original = read(path)
    note = 'Token usage telemetry unavailable.'
    if original.get('status') != 'continue' or note not in original.get('evidence', []):
        return validate_result(original, root, locale)
    cleaned = dict(original, evidence=[item for item in original['evidence'] if item != note])
    if not cleaned['evidence']:
        raise ValueError('Telemetry normalization cannot replace missing real evidence')
    validate_result(cleaned, root, locale)
    normalized = path.with_name('result-metadata-normalized.json')
    if normalized.exists():
        if read(normalized) != cleaned:
            raise ValueError('Preserve conflicting prior metadata normalization')
    else:
        write(normalized, cleaned)
    record['metadataNormalization'] = {'originalPath': str(path), 'originalSha256': digest(path),
        'normalizedPath': str(normalized), 'normalizedSha256': digest(normalized),
        'removedEvidenceNotes': [note], 'boundary': 'Only the telemetry sentence is separated; actual path evidence is validated and all other fields/translation artifacts are unchanged.'}
    return cleaned


def reconcile_metadata(run, state, config):
    applied = state.setdefault('appliedMetadataRepairs', [])
    for request in config.get('metadataReconciliations', []):
        key = '%s:%s:%s' % (request['locale'], request['attempt'], request['resultSha256'])
        if key in applied:
            continue
        locale = request['locale']; row = state['locales'][locale]
        record = row['attempts'][-1]
        if row['status'] != 'needs-attention' or record['number'] != request['attempt'] or record.get('exitCode') != 0:
            raise ValueError('Metadata repair does not match a completed stopped attempt')
        if digest(record['resultPath']) != request['resultSha256'] or not usage(record['eventsPath'])['tokens']:
            raise ValueError('Metadata repair input or terminal turn differs')
        live = process_snapshot().get(record['pid'])
        if live and record['resultPath'] in live['command']:
            raise ValueError('Metadata repair cannot restart a live writer')
        result = worker_result(record, ROOT, locale)
        if not record.get('metadataNormalization'):
            raise ValueError('No recognized metadata-only correction')
        record['observerError'] = row.pop('error', None)
        record['status'] = result['status']
        record['metadataReconciled'] = stamp()
        row['summary'] = result; row['status'] = 'queued'
        applied.append(key)
        write(run / 'state.json', state)


def prepare(locales, jobs, risk):
    if not locales or len(set(locales)) != len(locales) or set(locales) - set(LOCALES):
        raise ValueError('Choose distinct locales from the established nonofficial target set; ru is protected.')
    if jobs < 1 or jobs > 26:
        raise ValueError('Parallelism must be 1..26')
    fd = acquire(CONTROL / 'queue.lock')
    try:
        if (CONTROL / 'current.json').exists():
            raise RuntimeError('Queue already exists. Use status/start; preserve its identity.')
        run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
        run = CONTROL / 'runs' / run_id
        snapshot = run / 'snapshot'
        snapshot.mkdir(parents=True)
        shutil.copy2(__file__, snapshot / 'localization_cli.py')
        for p in TEMPLATES.iterdir():
            if p.is_file():
                shutil.copy2(p, snapshot / p.name)
        write(snapshot / 'identity.json', {'root': str(ROOT), 'master': str(MASTER), 'runId': run_id})
        reference = snapshot / 'reference-tools'
        reference.mkdir()
        # Pin helpers possibly read later, without copying the game or creating a checkout/worktree.
        for p in (ROOT / 'tools').iterdir():
            if p.is_file() and p.suffix in {'.py', '.cjs', '.js', '.sh'}:
                shutil.copy2(p, reference / p.name)
        config = {'runId': run_id, 'created': stamp(), 'jobs': jobs, 'locales': locales,
                  'model': 'gpt-6.1-sol', 'reasoning': 'high', 'rendererRisk': risk,
                  'codex': shutil.which('codex'), 'snapshotHashes': artifacts([snapshot])}
        if not config['codex']:
            raise RuntimeError('Codex CLI is not installed')
        write(run / 'config.json', config)
        write(run / 'state.json', {'runId': run_id, 'status': 'prepared', 'bootstrap': {'status': 'queued', 'attempts': []},
              'locales': {locale: {'status': 'queued', 'attempts': []} for locale in locales}})
        write(CONTROL / 'current.json', {'runId': run_id, 'run': str(run)})
        return run
    finally:
        os.close(fd)


def current():
    return Path(read(CONTROL / 'current.json')['run'])


def launch_attempt(run, config, state, kind, lock_fd):
    row = state['bootstrap'] if kind == 'bootstrap' else state['locales'][kind]
    number = len(row['attempts']) + 1
    attempt = run / 'jobs' / kind / ('attempt-%04d' % number)
    attempt.mkdir(parents=True)
    if kind == 'bootstrap':
        cwd = ROOT / 'tools/multilingual'
        writable = [ROOT / 'source/multilingual', ROOT / 'runtime/multilingual', attempt]
        progress_paths = writable[:-1] + [cwd]
    else:
        cwd = ROOT / 'translation' / kind
        writable = [ROOT / 'build' / kind, ROOT / 'dist' / kind, attempt]
        progress_paths = writable[:-1] + [cwd]
    for path in [cwd] + writable:
        path.mkdir(parents=True, exist_ok=True)
    before = artifacts(progress_paths)
    worker_fd = acquire(run / 'locks' / (kind + '.lock'))
    snapshot = run / config.get('snapshotDirectory', 'snapshot')
    template = (snapshot / ('bootstrap.md' if kind == 'bootstrap' else 'locale.md')).read_text()
    prompt = template.replace('{{ROOT}}', str(ROOT)).replace('{{MASTER}}', str(MASTER))
    prompt = prompt.replace('{{RUN}}', str(run)).replace('{{LOCALE}}', kind)
    prompt = prompt.replace('{{RISK}}', config['rendererRisk'])
    prompt += '\nAttempt: %s. Read your existing checkpoint and continue verified work. This is a new session with no inherited chat history.\n' % number
    if row['attempts']:
        prompt += 'Previous structured result: %s\n' % row['attempts'][-1]['resultPath']
    prompt_path = attempt / 'prompt.md'
    prompt_path.write_text(prompt)
    result_path = attempt / 'result.json'
    if config.get('directTranslation'):
        locale_runtime = ROOT / 'runtime/multilingual/locales' / kind
        locale_runtime.mkdir(parents=True, exist_ok=True)
        writable.append(locale_runtime)
        progress_paths.append(locale_runtime)
        glossary_snapshot = cwd / 'glossary-snapshot.json'
        if not glossary_snapshot.exists():
            source_path = MASTER / 'data/games/omori/glossary.json'
            source = read(source_path)
            target = read(source_path.with_name('glossary-translations.json'))[kind]
            write(glossary_snapshot, {'siteLocale': kind, 'sourceLocale': 'en', 'source': source,
                  'target': target, 'sourcePath': str(source_path), 'sourceRawSha256': digest(source_path),
                  'targetLayerSha256': hashlib.sha256(json.dumps(target, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')).encode()).hexdigest(),
                  'provenance': 'Existing canonical glossary reused for direct authoring; no new acceptance claimed.'})
    args = command(config['codex'], cwd, result_path, snapshot / 'result.schema.json', writable)
    stdout = (attempt / 'events.jsonl').open('w')
    stderr = (attempt / 'stderr.log').open('w')
    stdin = prompt_path.open()
    try:
        proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                                pass_fds=(lock_fd, worker_fd), start_new_session=True)
    except Exception:
        os.close(worker_fd)
        raise
    finally:
        stdin.close(); stdout.close(); stderr.close()
    record = {'number': number, 'started': stamp(), 'pid': proc.pid, 'processGroup': proc.pid, 'command': args,
              'resultPath': str(result_path), 'eventsPath': str(attempt / 'events.jsonl'), 'status': 'running'}
    row['attempts'].append(record)
    row['status'] = 'running'
    write(run / 'state.json', state)
    return proc, worker_fd, before, progress_paths, record


def finish(run, state, kind, active):
    proc, fd, before, paths, record = active
    row = state['bootstrap'] if kind == 'bootstrap' else state['locales'][kind]
    if getattr(proc, 'adopted', False):
        finish_adopted(run, state, kind, record)
        return
    record.update({'exitCode': proc.returncode, 'finished': stamp(), 'usage': usage(record['eventsPath'])})
    try:
        if proc.returncode != 0:
            if rate_limit_failure(record['eventsPath']):
                schedule_rate_limit(row, record)
                return
            raise RuntimeError('CLI exited nonzero. Preserve logs and side effects; no automatic resubmission.')
        result = worker_result(record, ROOT, kind)
        changed = artifacts(paths) != before
        if result['status'] == 'continue' and not changed:
            raise RuntimeError('No material artifact change; do not loop on unchanged reports.')
        row['status'] = 'queued' if result['status'] == 'continue' else result['status']
        row['summary'] = result
        row['consecutiveRateLimitFailures'] = 0
        record['status'] = result['status']
        if kind == 'bootstrap' and result['status'] == 'prepared':
            gate = ROOT / 'source/multilingual/acceptance.json'
            if not gate.is_file():
                raise RuntimeError('Shared preparation has no acceptance receipt')
            validate_preparation(ROOT)
            frozen = run / 'tooling'
            shutil.copytree(ROOT / 'tools/multilingual', frozen)
            row['toolingHashes'] = artifacts([frozen])
    except Exception as exc:
        row['status'] = 'needs-attention'
        row['error'] = str(exc)
        record['status'] = 'needs-attention'
    finally:
        os.close(fd)
        write(run / 'state.json', state)


def process_snapshot():
    rows = {}
    raw = subprocess.check_output(['ps', '-axo', 'pid,ppid,pgid,stat,lstart,command'], text=True)
    for line in raw.splitlines()[1:]:
        p = line.strip().split(None, 9)
        if len(p) == 10:
            rows[int(p[0])] = {'ppid': int(p[1]), 'pgid': int(p[2]), 'state': p[3],
                              'started': ' '.join(p[4:9]), 'command': p[9]}
    return rows


class AdoptedProcess:
    """Observe an existing task tree without pretending its exit code is known."""
    adopted = True
    returncode = None

    def __init__(self, processes):
        self.tracked = {int(pid): info for pid, info in processes.items()}

    def poll(self):
        rows = process_snapshot()
        live = {pid for pid, info in self.tracked.items()
                if pid in rows and rows[pid]['started'] == info['started']
                and not rows[pid].get('state', '').startswith('Z')}
        while True:
            extra = {pid for pid, info in rows.items() if info['ppid'] in live} - live
            if not extra:
                break
            live.update(extra)
        for pid in live:
            self.tracked[pid] = rows[pid]
        return None if live else 'identified-task-tree-exited'


def finish_adopted(run, state, locale, record):
    row = state['locales'][locale]
    record['observerAdoptionCompleted'] = stamp()
    record['usage'] = usage(record['eventsPath'])
    record['exitCode'] = None
    record['exitCodeObserved'] = False
    try:
        if not record['usage']['tokens']:
            if rate_limit_failure(record['eventsPath']):
                record['finished'] = stamp()
                schedule_rate_limit(row, record)
                return
            raise ValueError('Adopted task exited without a successful terminal turn; unknown outcome preserved')
        result = worker_result(record, ROOT, locale)
        row['summary'] = result
        row['status'] = 'queued' if result['status'] == 'continue' else result['status']
        row['consecutiveRateLimitFailures'] = 0
        row.pop('error', None)
        record['status'] = result['status']
        record['reconciliationBoundary'] = 'Identified task tree exited; successful terminal model turn and valid saved result/evidence. OS exit code and original before-artifact snapshot were not observed by this replacement coordinator.'
    except Exception as exc:
        row['status'] = 'needs-attention'
        row['error'] = str(exc)
        record['status'] = 'needs-attention'
    finally:
        write(run / 'state.json', state)


def execute(run):
    if read(run / 'config.json').get('pipelineRevision') == 2:
        import localization_pipeline
        return localization_pipeline.execute(run)
    identity = read(run / 'snapshot/identity.json')
    global ROOT, MASTER, CONTROL
    ROOT = Path(identity['root']); MASTER = Path(identity['master'])
    CONTROL = ROOT / 'runtime/cli-localization'
    config = read(run / 'config.json')
    lock_fd = acquire(CONTROL / config.get('queueLockFile', 'queue.lock'))
    try:
        config = read(run / 'config.json')
        snapshot = run / config.get('snapshotDirectory', 'snapshot')
        if artifacts([snapshot]) != config['snapshotHashes']:
            raise RuntimeError('Execution snapshot changed; refusing an unpinned launch')
        state = read(run / 'state.json')
        adoption = read(run / config['adoptionManifest']) if config.get('adoptionManifest') else {}
        reconcile_metadata(run, state, config)
        existing = {loc for loc, row in state['locales'].items() if row['status'] == 'running'}
        if existing - set(adoption.get('locales', {})) or state['bootstrap']['status'] == 'running':
            raise RuntimeError('Previous observer interrupted. Reconcile its exact attempts/children before restart.')
        state.update({'status': 'running', 'supervisorPid': os.getpid(), 'started': stamp()})
        write(run / 'state.json', state)
        active = {}
        for locale in existing:
            record = state['locales'][locale]['attempts'][-1]
            pinned = adoption['locales'][locale]
            if record['pid'] != pinned['pid'] or record['resultPath'] != pinned['resultPath']:
                raise RuntimeError('Adopted writer identity differs from the handoff')
            record['adoptedByObserver'] = os.getpid()
            active[locale] = (AdoptedProcess(pinned['processes']), None, None, None, record)
        write(run / 'state.json', state)
        while True:
            for kind in list(active):
                if active[kind][0].poll() is not None:
                    finish(run, state, kind, active.pop(kind))
            if state['bootstrap']['status'] == 'queued' and 'bootstrap' not in active:
                active['bootstrap'] = launch_attempt(run, config, state, 'bootstrap', lock_fd)
            if state['bootstrap']['status'] in {'prepared', 'superseded-by-owner'}:
                tooling = run / config.get('toolingDirectory', 'tooling')
                if artifacts([tooling]) != state['bootstrap']['toolingHashes']:
                    raise RuntimeError('Frozen shared tooling changed during execution')
                for locale, row in state['locales'].items():
                    if len(active) >= config['jobs']:
                        break
                    if row['status'] == 'waiting-rate-limit' and time.time() >= row['retryNotBefore']:
                        row['status'] = 'queued'
                    if row['status'] not in {'queued', 'waiting-glossary', 'waiting-renderer-decision'}:
                        continue
                    if config['rendererRisk'] != 'accepted-static':
                        row['status'] = 'waiting-renderer-decision'
                    elif not glossary_available(locale):
                        row['status'] = 'waiting-glossary'
                    else:
                        active[locale] = launch_attempt(run, config, state, locale, lock_fd)
                write(run / 'state.json', state)
            if not active and state['bootstrap']['status'] in {'prepared', 'superseded-by-owner'} and any(
                    r['status'] in {'waiting-glossary', 'waiting-rate-limit'} for r in state['locales'].values()):
                state['status'] = 'waiting-prerequisite-or-cooldown'
                write(run / 'state.json', state)
                # Passive prerequisite observation makes no model request.
                time.sleep(30)
                continue
            if not active:
                state['status'] = 'needs-attention' if state['bootstrap']['status'] not in {'prepared', 'superseded-by-owner'} else 'waiting-or-finished'
                write(run / 'state.json', state)
                return
            time.sleep(2)
    finally:
        os.close(lock_fd)


def start(run):
    # Gate duplicate launch before creating a detached observer. The observer owns the same lock.
    config = read(run / 'config.json')
    fd = acquire(CONTROL / config.get('queueLockFile', 'queue.lock'))
    os.close(fd)
    log = (run / 'supervisor.log').open('a')
    if config.get('pipelineRevision') == 2:
        snapshot = run / config['pipelineSnapshotDirectory']
        args = [sys.executable, str(snapshot / 'localization_pipeline.py'), str(run)]
    else:
        snapshot = run / config.get('snapshotDirectory', 'snapshot')
        args = [sys.executable, str(snapshot / 'localization_cli.py'), '_run', str(run)]
    proc = subprocess.Popen(args,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    log.close()
    print(json.dumps({'run': str(run), 'supervisorPid': proc.pid, 'status': 'submitted'}, indent=2))


def recover_observer(run):
    """Reconcile accepted results after observer handoff; never restart live writers."""
    identity = read(run / 'snapshot/identity.json')
    global ROOT, MASTER, CONTROL
    ROOT = Path(identity['root']); MASTER = Path(identity['master'])
    CONTROL = ROOT / 'runtime/cli-localization'
    guard = acquire(CONTROL / 'recovery.lock')
    try:
        handoff = read(run / read(run / 'config.json').get('recoveryHandoff', 'observer-handoff-v3.json'))
        state = read(run / 'state.json')
        state['status'] = 'recovering-observer'
        state['recoveryPid'] = os.getpid()
        write(run / 'state.json', state)
        tracked = {int(k): v for k, v in handoff['writers'].items()}
        while True:
            raw = subprocess.check_output(['ps', '-axo', 'pid,ppid,lstart,command'], text=True)
            processes = {}
            for line in raw.splitlines()[1:]:
                parts = line.strip().split(None, 7)
                if len(parts) == 8:
                    processes[int(parts[0])] = {'ppid': int(parts[1]), 'started': ' '.join(parts[2:7]), 'command': parts[7]}
            known = {pid for pid, info in tracked.items() if pid in processes and processes[pid]['started'] == info['started']}
            while True:
                extra = {pid for pid, info in processes.items() if info['ppid'] in known} - known
                if not extra:
                    break
                known.update(extra)
            for pid in known:
                if pid not in tracked and pid in processes:
                    tracked[pid] = processes[pid]
            live = [pid for pid, info in tracked.items() if pid in processes and processes[pid]['started'] == info['started']]
            write(run / 'observer-recovery-progress.json', {'liveWriterPids': live, 'checked': stamp()})
            if not live:
                break
            time.sleep(10)
        for locale, row in state['locales'].items():
            if row['status'] not in {'running', 'needs-attention'} or not row['attempts']:
                continue
            attempt = row['attempts'][-1]
            try:
                measured = usage(attempt['eventsPath'])
                if not measured['tokens']:
                    if rate_limit_failure(attempt['eventsPath']):
                        schedule_rate_limit(row, attempt)
                        continue
                    raise ValueError('No successful terminal model turn; preserve unknown outcome')
                result = validate_result(read(attempt['resultPath']), ROOT, locale)
                attempt['observerError'] = row.pop('error', None)
                attempt['status'] = result['status']
                attempt['usage'] = measured
                attempt['reconciled'] = stamp()
                attempt['reconciliationBoundary'] = 'No surviving identified writers; successful terminal turn and existing valid result/evidence. Original process exit code remains unknown if not observed.'
                row['summary'] = result
                row['status'] = 'queued' if result['status'] == 'continue' else result['status']
            except Exception as exc:
                row['status'] = 'needs-attention'
                row['error'] = str(exc)
        state['status'] = 'reconciled-for-continuation'
        write(run / 'state.json', state)
    finally:
        os.close(guard)
    execute(run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--locales', nargs='+', default=LOCALES)
    prep.add_argument('--jobs', type=int, default=3)
    prep.add_argument('--renderer-risk', choices=['pending', 'accepted-static'], default='pending')
    sub.add_parser('start'); sub.add_parser('status')
    run_parser = sub.add_parser('_run'); run_parser.add_argument('run', type=Path)
    recovery_parser = sub.add_parser('_recover'); recovery_parser.add_argument('run', type=Path)
    args = parser.parse_args()
    if args.cmd == 'prepare':
        print(prepare(args.locales, args.jobs, args.renderer_risk))
    elif args.cmd == 'start':
        start(current())
    elif args.cmd == '_run':
        execute(args.run)
    elif args.cmd == '_recover':
        recover_observer(args.run)
    else:
        run = current(); state = read(run / 'state.json')
        state['run'] = str(run)
        for row in [state['bootstrap']] + list(state['locales'].values()):
            for attempt in row['attempts']:
                attempt['usage'] = usage(attempt['eventsPath'])
        print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
