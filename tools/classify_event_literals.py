#!/usr/bin/env python3
"""Classify original event AST strings with typed consumer boundaries."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from source_prepare import save_json, sha, strict_json

TECHNICAL_CALLS = {
    'unlockAchievement', 'loadAtlas', 'addRequiredAtlas', 'addRequireAtlas', 'addExtraFollower',
    'setMovementGraphics', 'setMovementGraphicData', 'loadCharacter', 'getFollowerById',
    'createMapFog', 'removeMapFog', 'addQuest', 'removeQuest', 'setQuestCompleteState',
    'setQuestMessageIndex', 'hasCategory', 'addCategory', 'setValueExt', 'setValue',
    'setWaitMode', 'loadVideo', 'newVideo', 'releaseVideo', 'setPictureDisplayLayer',
    'setupShop', 'showPicture', 'setupAmbience', 'startStopTheArrowQTE',
    'createHorrorEffect', 'removeHorrorEffect', 'setHorrorEffectToValue', 'getMessageData',
    'getTextData', 'addCutscene', 'SpawnEventTemplateInRegion', 'setPictureInAlbum',
    'clearPictureInAlbum', 'addPictureToAlbum', 'setBattleIntro', 'playBgm', 'playBgs',
    'writeToFile', 'readFromFile', 'waitForInput', 'log', 'Number', 'commandShowLanguageMessage',
}


def role(row):
    source, ctx = row['source'], row['context']
    call, statement = ctx.get('call') or '', ctx.get('statement') or ''
    if row['role'] == 'preserve-exactly':
        return 'preserve-exactly', row['reason']
    if re.match(r'\$gameVariables\.setValue\(23\s*,', call):
        return 'visible-display-mapping', 'Legacy chapter display label and save-language conversion identity. Save & Load displays it; GTP convertNameToLanguage compares it with chapterNamesPerLanguage. Preserve variable23 assignment and map the display separately.'
    if source == 'SUNNY' and ('showNameInputWindows' in call or re.match(r'name\s*=', statement)):
        return 'visible', 'Original default name in name-entry program; Name Input lines 249–251 and 310–316.'
    if ctx.get('callMethod') == 'completeQuest':
        return 'preserve-exactly', 'Legacy quest-control operand. No definition was found in pinned enabled scripts; retain original call and record source finding, not translated wording.'
    if call:
        method = ctx.get('callMethod')
        if method in TECHNICAL_CALLS:
            return 'preserve-exactly', 'Consumer ' + method + ': resource/ID/enum/reference/control/storage argument; chapter/name-entry display exceptions handled first.'
    if re.match(r'(?:\$|\[SF\]|DW_|FA_|DEV_|BASIL_|objects_|\[BATTLEONLY\])', source):
        return 'preserve-exactly', 'Movement/resource identifier in original event program.'
    if ctx['parentType'] in {'Property', 'ArrayExpression'} and (
            len(source) == 1 and source in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' or 'name:' in statement or 'name :' in statement):
        return 'preserve-exactly', 'Self-switch alphabet or movement resource property.'
    if re.fullmatch(r'fog\.name\s*=\s*[\'\"]fog[\'\"]', statement):
        return 'preserve-exactly', 'Map-fog resource assignment.'
    if re.search(r'(?:var\s+)?img\s*=|(?:var\s+)?bgs\s*=', statement):
        return 'preserve-exactly', 'Deferred movement/audio resource assignment.'
    return 'needs-role-review', 'Consumer or deferred assignment remains unbound; preserve original until reviewed.'


def note_role(row):
    if row['role'] == 'preserve-exactly':
        return 'preserve-exactly', row['reason']
    source, ctx = row['source'], row['context']
    method = ctx.get('callMethod')
    if method == 'addText':
        return 'visible', 'Battle-log display fragment in a parsed notetag program.'
    if method == 'push':
        if source in {'addText', 'waitForNewLine'}:
            return 'preserve-exactly', 'Battle-log dispatch method symbol, not wording.'
        if re.search(r'push\([\'\"]addText[\'\"]', ctx.get('call') or ''):
            return 'visible', 'Visible addText argument; exact dispatch symbol and dynamic expressions stay protected.'
    if method in {'parseNoStateChange', 'parseNoEffectEmotion'}:
        if method == 'parseNoEffectEmotion' and ctx.get('callArgumentIndex') == 1 and 'afraid' in source.lower():
            return 'visible-display-mapping', 'Emotion feedback discriminator also selects the afraid branch; original argument stays exact and its display is mapped separately.'
        if re.fullmatch(r'\\n\[\d+\]', source):
            return 'preserve-exactly', 'Exact dynamic actor-name escape.'
        return 'visible', 'Display component assembled by GTP_OmoriFixes lines 2604–2633; keep enclosing calls and branch/comparison syntax.'
    if method in {'isEmotionAddable', 'removeStateCategoryAll', 'playSe', 'showPicture', 'unlockAchievement', 'requestEffect', 'queueForceScriptCall'}:
        return 'preserve-exactly', 'Notetag mechanics/resource/control/eval argument.'
    if ctx['parentType'] == 'Property' and source == 'item':
        return 'preserve-exactly', 'Stealable item type enum.'
    if re.match(r'(?:text|msg)\s*=', ctx.get('statement') or ''):
        return 'visible', 'Authored battle message variable; inspect complete assembled message and later log consumer during translation.'
    return 'needs-role-review', 'Notetag consumer remains unbound.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('classification', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kind', choices=['event', 'note'], default='event')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new immutable role-evidence output')
    ast_path = args.classification / ('ast.json' if args.kind == 'note' else 'event-program-ast.json')
    ast = strict_json(ast_path.read_bytes())
    rows, counts = [], Counter()
    for original in ast['strings']:
        r = dict(original)
        r['role'], r['reason'] = (note_role if args.kind == 'note' else role)(original)
        counts[r['role']] += 1
        rows.append(r)
    report = {'schemaVersion': 1, 'eventAstRawSha256': sha(ast_path.read_bytes()),
              'recipeRawSha256': sha(Path(__file__).read_bytes()), 'roles': dict(counts), 'strings': rows,
              'kind': args.kind, 'sourceGate': 'needs-review', 'runtime': 'not-run',
              'limits': ['This classifies event literals only, not plugin literals, note scripts or all source text.',
                        'Visible AST slots still need an exact-span reinsertion/protected-syntax adapter before translation.',
                        'Original parse-error programs remain exact original protected source findings.']}
    save_json(args.output, report)
    pending = [r for r in rows if r['role'] == 'needs-role-review']
    print(json.dumps({'roles': dict(counts), 'pendingExamples': [{'id': r['id'], 'source': r['source'], 'context': r['context']} for r in pending[:8]]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
