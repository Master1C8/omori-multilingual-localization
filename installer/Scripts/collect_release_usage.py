#!/usr/bin/env python3
"""Collect existing measured, nonoverlapping OMORI usage without model calls.

Read recorded per-attempt CLI telemetry and explicit glossary/Russian receipts.
Optional dedicated project journals are split by the actual model context and
cumulative-counter deltas. Never price tokens or turn unavailable usage into zero.
Private manifests and the coverage audit must remain outside the public repository.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def collect(root, output, journals):
    records, evidence, missing, seen = [], [], [], set()

    def add(identity, tokens, model, task, kind, date, source, locale=None, notes=None):
        if identity in seen:
            raise ValueError('Overlapping usage identity: ' + identity)
        seen.add(identity)
        if not tokens or tokens.get('input_tokens') is None or tokens.get('output_tokens') is None:
            missing.append({'identity': identity, 'source': source, 'reason': 'usage unavailable'})
            return
        row = {'usageDate': date, 'taskType': kind, 'task': task, 'model': model,
               'provider': 'OpenAI Codex', 'usageSource': source,
               'inputTokens': tokens['input_tokens'], 'outputTokens': tokens['output_tokens']}
        for old, new in [('cached_input_tokens', 'cachedInputTokens'), ('reasoning_output_tokens', 'reasoningTokens')]:
            if tokens.get(old) is not None:
                row[new] = tokens[old]
        if locale:
            row['locale'] = locale
        row['notes'] = notes or 'Measured contribution only. Project coverage limitations are recorded in the private usage coverage audit.'
        if any(not isinstance(row[k], int) or row[k] < 0 for k in ['inputTokens', 'outputTokens']):
            raise ValueError('Invalid measured counters')
        if row.get('cachedInputTokens', 0) > row['inputTokens'] or row.get('reasoningTokens', 0) > row['outputTokens']:
            raise ValueError('Invalid subset counters')
        records.append(row)
        evidence.append({'identity': identity, 'record': len(records), 'source': source})

    current = load(root / 'runtime/cli-localization/current.json')
    state_path = Path(current['run']) / 'state.json'
    raw_state = state_path.read_bytes()
    state = json.loads(raw_state)
    jobs = [('bootstrap', None, row) for row in state['bootstrap']['attempts']]
    for locale, data in state['locales'].items():
        jobs += [(row.get('role', 'legacy'), locale, row) for row in data['attempts']]
    for name, data in state['sharedTasks'].items():
        jobs += [(name, None, row) for row in data['attempts']]
    for role, locale, job in jobs:
        usage = job.get('usage') or {}
        value = usage.get('tokens')
        tokens = None if value is None else {
            'input_tokens': value['input'], 'cached_input_tokens': value.get('cached_input'),
            'output_tokens': value['output'], 'reasoning_output_tokens': value.get('reasoning')}
        command = job['command']
        if 'resume' in command:
            raise ValueError('Resumed session needs separate overlap accounting')
        model = command[command.index('-m') + 1]
        identity = usage.get('session') or job['eventsPath']
        kind = {'editor': 'editorial-audit', 'resources': 'fonts', 'package': 'build-packaging',
                'delivery': 'application', 'acceptance': 'editorial-audit', 'bootstrap': 'assets'}.get(role, 'game-translation')
        add(identity, tokens, model, 'OMORI CLI ' + (locale + ' ' if locale else '') + role + ' attempt ' + str(job['number']),
            kind, job.get('finished', job['started']), job['eventsPath'], locale)

    path = root / 'glossary/multilingual-orchestration-usage.json'
    glossary = load(path)
    for worker in glossary['workers']:
        measurement = worker.get('usage') or {}
        task = worker['task']
        # Historical task names use compact aliases; prefix matching would
        # wrongly assign es419 to es and drop ptbr/zhtw from locale accounting.
        aliases = {'es419': 'es-419', 'ptbr': 'pt-BR', 'zhtw': 'zh-TW'}
        name = task.rsplit('/', 1)[-1]
        suffix = name.removeprefix('glossary_').removeprefix('review_').split('_v', 1)[0]
        locale = aliases.get(suffix, suffix)
        if locale not in state['locales']:
            locale = None
        add(worker.get('sessionId') or task, measurement.get('cumulativeUsage'), worker['model'],
            worker['assignment'], 'glossary-localization', measurement.get('cutoffTimestampUtc', '2026-10-13'), str(path), locale)
    add(glossary['coordinatorSessionId'] + ':glossary-delta', glossary['coordinatorMeasuredDelta'],
        'gpt-6.1-sol', 'OMORI glossary coordination measured delta', 'glossary-localization',
        glossary['coordinatorFinalMeasurement']['cutoffTimestampUtc'], str(path))

    path = root / 'glossary/multilingual-resumption-usage-2026-10-13.json'
    data = load(path)
    add(data['sessionId'], data['usage'], data['model'], 'OMORI glossary continuation',
        'glossary-localization', data['cutoffTimestampUtc'], str(path))
    path = root / 'source/ru-continuation-2026-10-14-usage-02.json'
    data = load(path)
    add(data['sessionId'] + ':initial', {'input_tokens': data['inputTokens'],
        'output_tokens': data['outputTokens'], 'cached_input_tokens': data['cachedInputTokensSubset'],
        'reasoning_output_tokens': data['reasoningOutputTokensSubset']}, data['model'],
        'OMORI Russian continuation through measured initial cutoff', 'game-translation', data['cutoffUtc'], str(path), 'ru')
    path = root / 'source/ru-independent-review-2026-10-14-usage-final.json'
    data = load(path)
    coordinator = data['coordinator']
    if coordinator['baseline']['usage']['input_tokens'] < load(root / 'source/ru-continuation-2026-10-14-usage-02.json')['inputTokens']:
        raise ValueError('Russian cumulative and delta overlap')
    add(coordinator['sessionId'] + ':review-delta', coordinator['taskDelta'], coordinator['model'],
        data['task'] + ' (mixed coordinator)', 'editorial-audit', coordinator['cutoff']['timestamp'], str(path), 'ru')
    reviewer = data['reviewer']
    add(reviewer['sessionId'], reviewer['taskUsage'], reviewer['model'], 'OMORI independent Russian review',
        'editorial-audit', reviewer['cutoff']['timestamp'], str(path), 'ru')
    previous_end = coordinator['cutoff']['usage']['input_tokens']
    path = root / 'source/ru-special-scenes-2026-10-14-usage-final-02.json'
    data = load(path)
    if data['baseline']['usage']['input_tokens'] < previous_end:
        raise ValueError('Russian review deltas overlap')
    add(data['sessionId'] + ':special-delta', data['taskDelta'], data['context']['model'],
        data['task'], 'editorial-audit', data['cutoff']['timestamp'], str(path), 'ru')

    for journal in journals:
        # Read metadata/usage only; never export transcript text.
        latest_model, previous, segments, sid, stamp = None, None, defaultdict(lambda: defaultdict(int)), None, None
        with journal.open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                payload = event.get('payload') or {}
                if event.get('type') == 'session_meta':
                    if payload.get('source') != 'vscode' or Path(payload.get('cwd', '')) != root:
                        raise ValueError('Journal must be a dedicated root OMORI session')
                    sid = payload['id']
                if event.get('type') == 'turn_context':
                    latest_model = payload.get('model', latest_model)
                if payload.get('type') != 'token_count':
                    continue
                usage = (payload.get('info') or {}).get('total_token_usage')
                if not usage or usage == previous:
                    continue
                if not latest_model:
                    raise ValueError('Missing model context for measured journal counters')
                for key in ['input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens']:
                    if usage.get(key) is None or (previous and previous.get(key) is None):
                        raise ValueError('Journal breakdown unavailable; needs explicit missing-data handling')
                    delta = usage[key] - (previous[key] if previous else 0)
                    if delta < 0:
                        raise ValueError('Journal cumulative counter reset')
                    segments[latest_model][key] += delta
                previous, stamp = usage, event['timestamp']
        if sid in seen:
            raise ValueError('Journal overlaps recorded worker')
        for model, tokens in segments.items():
            add(sid + ':' + model, tokens, model, 'OMORI dedicated project session measured through cutoff',
                'runtime-visual-qa' if sid == '01a14c47-1ce7-7f72-bc05-2f5a4514f802' else 'site-content',
                stamp, str(journal), notes='Mixed work within this dedicated project session. Final reporting tail and later requests are unmeasured. No per-phase split claimed.')

    # One session/attempt is counted once, with actual telemetry even for failed attempts.
    audit = {'stateSha256': hashlib.sha256(raw_state).hexdigest(), 'measuredRecords': len(records),
             'inputTokens': sum(row['inputTokens'] for row in records),
             'outputTokens': sum(row['outputTokens'] for row in records),
             'missingTelemetry': missing, 'evidence': evidence,
             'coverage': 'Measured subtotal of recorded CLI attempts, glossary receipts, Russian receipts and supplied dedicated project journals. Earlier extraction/source-glossary work, unsupplied continuation sessions, unreported failed requests, gaps between explicit delta receipts, final reporting tail and platform overhead are unknown. This is not an exhaustive project-total claim. Costs are omitted.'}
    output.mkdir(parents=True, exist_ok=False)
    (output / 'model-usage.json').write_text(json.dumps({'schemaVersion': 1, 'records': records}, indent=2) + '\n')
    (output / 'usage-coverage.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps({key: value for key, value in audit.items() if key not in ('evidence', 'missingTelemetry')}, indent=2))
    print('Attempts without telemetry:', len(missing))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--journal', type=Path, action='append', default=[])
    args = parser.parse_args()
    collect(args.root.resolve(), args.output.resolve(), args.journal)
