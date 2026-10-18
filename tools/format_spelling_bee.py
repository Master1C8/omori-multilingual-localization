#!/usr/bin/env python3
"""Encode model-authored Cyrillic phrases into four original letter/pause frames.

This is a layout assembler, not a translator. Every phrase and deliberate stretched
sound is supplied in the authored draft. Unexpected frame/letter counts fail before
the single atomic draft replacement. No source or installation file is written.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from source_text_syntax import compare_text_controls

ASSET = 'languages/en/dreamworld_npc_dialogue_pinwheel.HERO'
MANIFEST_HASH = 'a55c246992fc1ea672aba77ae0cbdc3ba67aa8ac8d84dd6b78a673addbb1c144'
FRAMES = {'message_1': [11, 26], 'message_40': [26, 37],
          'message_50': [24, 25], 'message_60': [23]}
EN_BOX = '\\n<SPELLING BEE>'
RU_BOX = '\\n<ПЧЕЛА-ПРАВОПИСЧИК>'


def letter_atoms(phrase):
    indices = [i for i, c in enumerate(phrase) if c.isalpha()]
    if not indices or indices[0] != 0:
        raise ValueError('A spelled block must start with its first authored letter')
    if any(not ('А' <= phrase[i] <= 'Я' or phrase[i] == 'Ё') for i in indices):
        raise ValueError('Spelled letters must be authored uppercase Cyrillic')
    if any(c.isdigit() or c in '\\<>' for c in phrase):
        raise ValueError('The plain phrase must not supply controls or numeric data')
    result = []
    for n, i in enumerate(indices):
        end = indices[n + 1] if n + 1 < len(indices) else len(phrase)
        tail = phrase[i + 1:end]
        separator = '-' if not tail and end < len(phrase) else ''
        result.append(phrase[i] + (tail if tail else separator))
    return result


def compile_blocks(source, phrases, expected_counts):
    if not source.startswith(EN_BOX):
        raise ValueError('Unexpected original speaker frame')
    blocks = source[len(EN_BOX):].split('<br>')
    if len(blocks) != len(phrases) or len(blocks) != len(expected_counts):
        raise ValueError('Original line/block count changed')
    rendered = []
    inspected = []
    for block, phrase, expected in zip(blocks, phrases, expected_counts):
        if block.count('\\!') != expected or '\\' in block.replace('\\!', ''):
            raise ValueError('Unexpected original pause/control frame')
        atoms = letter_atoms(phrase)
        final_pause = block.endswith('\\!')
        slots = expected if final_pause else expected + 1
        if len(atoms) != slots:
            raise ValueError(f'Authored phrase has {len(atoms)} letters; frame needs {slots}: {phrase!r}')
        text = '\\!'.join(atoms) + ('\\!' if final_pause else '')
        if text.replace('\\!', '').replace('-', '') != phrase.replace('-', ''):
            raise ValueError('Letter encoding did not retain the authored phrase')
        rendered.append(text)
        inspected.append({'authoredPhrase': phrase, 'letters': len(atoms),
                          'nativePauses': expected, 'finalPause': final_pause})
    target = RU_BOX + '<br>'.join(rendered)
    compare_text_controls(source, target)
    return target, inspected


def main():
    root = Path(__file__).resolve().parents[1]
    path = Path(sys.argv[1]).resolve()
    if not path.is_relative_to(root / 'translation/ru/drafts'):
        raise ValueError('Only a canonical ru authored draft may be rewritten')
    corpus = root / 'source/text-corpus-8879120-02'
    if hashlib.sha256((corpus / 'manifest.json').read_bytes()).hexdigest() != MANIFEST_HASH:
        raise ValueError('Accepted corpus manifest changed')
    draft = json.loads(path.read_text())
    if draft['asset'] != ASSET or set(draft['letterDeliveryBlocks']) != set(FRAMES):
        raise ValueError('This assembler is scoped to exactly four bee occurrences')
    units = {u['path'][0]: u for u in json.loads((corpus / 'units.json').read_text())
             if u['asset'] == ASSET and u['path'][-1] == 'text'}
    report = {}
    for key, counts in FRAMES.items():
        unit = units[key]
        if unit['role'] != 'visible' or hashlib.sha256(unit['source'].encode()).hexdigest() != unit['sourceValueSha256']:
            raise ValueError('Unexpected original role/source binding')
        target, report[key] = compile_blocks(unit['source'], draft['letterDeliveryBlocks'][key], counts)
        draft['targets'][key] = target
    draft['letterDeliveryInspection'] = report
    raw = json.dumps(draft, ensure_ascii=False, indent=2) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.bee-layout-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print(json.dumps({'status': 'passed', 'draft': str(path.relative_to(root)),
                      'occurrences': len(report), 'inspection': report}, ensure_ascii=False))


if __name__ == '__main__':
    main()
