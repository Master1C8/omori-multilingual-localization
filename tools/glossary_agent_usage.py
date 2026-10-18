#!/usr/bin/env python3
"""Capture bounded session telemetry for explicitly assigned glossary agents only."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'glossary/multilingual-orchestration-usage.json'
SESSIONS = Path('/Users/antonkrutov/.codex/sessions')
FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens',
          'reasoning_output_tokens', 'total_tokens')

def latest_usage(path):
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 1048576))
        tail = stream.read().decode('utf-8', errors='replace').splitlines()
    for line in reversed(tail):
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        payload = row.get('payload', {})
        if payload.get('type') == 'token_count':
            usage = (payload.get('info') or {}).get('total_token_usage')
            if usage is not None:
                return {'cutoffTimestampUtc': row.get('timestamp'),
                        'cumulativeUsage': {key: usage.get(key) for key in FIELDS}}
    return None

parser = argparse.ArgumentParser()
parser.add_argument('--capture', action='store_true')
args = parser.parse_args()
receipt = json.loads(RECEIPT.read_text())
workers = {row['task']: row for row in receipt['workers']}
coordinator = receipt['coordinatorSessionId']
for path in SESSIONS.glob('2026/10/*/*.jsonl'):
    with path.open() as stream:
        try:
            meta = json.loads(stream.readline()).get('payload', {})
        except (ValueError, TypeError):
            continue
    source = meta.get('source')
    spawn = (source.get('subagent', {}).get('thread_spawn', {})
             if isinstance(source, dict) else {})
    task = spawn.get('agent_path')
    if spawn.get('parent_thread_id') == coordinator and task in workers:
        worker = workers[task]
        worker['sessionId'] = meta.get('id')
        worker['sessionPath'] = str(path)
        worker['usage'] = latest_usage(path)
        worker['measurementScope'] = ('Fresh no-history assignment session; cumulative '
                                      'counters count this worker once, with no inherited counters.')
    elif meta.get('id') == coordinator:
        usage = latest_usage(path)
        receipt['coordinatorFinalMeasurement'] = usage
        if usage:
            base = receipt['baselineCumulativeUsage']
            current = usage['cumulativeUsage']
            receipt['coordinatorMeasuredDelta'] = {
                key: current[key] - base[key]
                if current[key] is not None and base.get(key) is not None else None
                for key in FIELDS
            }
receipt['measurementLimitations'] = (
    'The capture does not include requests logged after its cutoff, its own reporting '
    'tail, or unmeasured platform overhead. Pre-baseline preparation is unmeasured. '
    'Coordinator deltas are a shared group subtotal, never allocated to each worker. '
    'Token counts are not monetary charges.'
)
if args.capture:
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
for worker in receipt['workers']:
    print(json.dumps({key: worker.get(key) for key in
                      ('task', 'model', 'reasoning', 'sessionId', 'usage')}, ensure_ascii=False))
print(json.dumps({'coordinatorSharedDelta': receipt.get('coordinatorMeasuredDelta'),
                  'cutoff': (receipt.get('coordinatorFinalMeasurement') or {}).get('cutoffTimestampUtc')},
                 ensure_ascii=False))
