#!/usr/bin/env python3
"""Capture one completed worker phase and nonoverlapping shared coordinator usage.

This is accounting only. It does not translate, review, accept or publish content.
The coordinator must deliver the printed measurements in its next user update.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'glossary/multilingual-orchestration-usage.json'
parser = argparse.ArgumentParser()
parser.add_argument('--task', required=True)
parser.add_argument('--phase', required=True)
parser.add_argument('--outcome', required=True)
args = parser.parse_args()
subprocess.run([sys.executable, str(ROOT / 'tools/glossary_agent_usage.py'), '--capture'],
               cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
d = json.loads(LEDGER.read_text())
w = next(row for row in d['workers'] if row['task'] == args.task)
u = w.get('usage')
if not u or not w.get('sessionId'):
    raise SystemExit('Worker telemetry unknown; report unknown without changing counters.')
if any(row['task'] == args.task and row['phase'] == args.phase
       for row in d['reportedOutcomes']):
    raise SystemExit('Phase already captured; reconcile its existing receipt before retrying.')
c = u['cumulativeUsage']
b = w.get('lastReportedCumulativeUsage', {key: 0 for key in c})
if any(c[key] is None or b[key] is None or c[key] < b[key] for key in c):
    raise SystemExit('Unknown or decreasing worker counters; manual reconciliation required.')
delta = {key: c[key] - b[key] for key in c}
assert delta['total_tokens'] == delta['input_tokens'] + delta['output_tokens']
record = {'task': args.task, 'sessionId': w['sessionId'], 'phase': args.phase,
          'model': w['model'], 'reasoning': w['reasoning'], 'outcome': args.outcome,
          'baselineCumulativeUsage': b, 'cutoffTimestampUtc': u['cutoffTimestampUtc'],
          'measuredDelta': delta, 'userReported': False}
d['reportedOutcomes'].append(record)
w['lastReportedCumulativeUsage'] = c
w['lastReportedCutoffTimestampUtc'] = u['cutoffTimestampUtc']
w['outcome'] = args.outcome
prior = {key: 0 for key in c}
for r in d['coordinatorUserReports']:
    value = r.get('nonoverlappingDelta', r.get('deltaFromTaskBaseline'))
    for key in prior:
        prior[key] += value[key]
current = d['coordinatorMeasuredDelta']
root_delta = {key: current[key] - prior[key] for key in prior}
assert all(value >= 0 for value in root_delta.values())
assert root_delta['total_tokens'] == root_delta['input_tokens'] + root_delta['output_tokens']
root_record = {'fromCutoffTimestampUtc': d['coordinatorUserReports'][-1]['cutoffTimestampUtc'],
               'cutoffTimestampUtc': d['coordinatorFinalMeasurement']['cutoffTimestampUtc'],
               'nonoverlappingDelta': root_delta, 'userReported': False}
root_record['scope'] = d.pop('coordinatorNextIntervalScope', 'shared orchestration')
d['coordinatorUserReports'].append(root_record)
LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'worker': record, 'coordinator': root_record,
                  'limitations': d['measurementLimitations']}, ensure_ascii=False))
