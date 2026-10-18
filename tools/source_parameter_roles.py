#!/usr/bin/env python3
"""Classify pinned enabled-plugin configuration by declared consumer schemas.

Only original source is emitted. This tool never supplies localized wording.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from source_prepare import save_json, sha, strict_json

TEXT_KEYS = {
    'YEP_CoreEngine': {'Gold Overlap'},
    'YEP_BattleEngineCore': {'User Help Text', 'Ally Help Text', 'Allies Help Text', 'Enemy Help Text', 'Enemies Help Text', 'All Help Text', 'Random Help Text'},
    'YEP_X_ActSeqPack3': {'Camera Option'},
    'YEP_EquipCore': {'Finish Command', 'Remove Text', 'Empty Text'},
    'YEP_SkillCore': {'HP Format', 'MP Format', 'TP Format'},
    'YEP_X_CounterControl': {'Counter Name'},
    'YEP_StealSnatch': {'Fail Text', 'Success Text', 'Steal Empty', 'Gold Format', 'Gold Help Text', 'Already Stolen'},
    'Active Chain Skills': {'Title Text', '(↑) Up Skill ON', '(↑) Up Skill OFF', '(↑) Up Skill ACT',
                           '(↓) Down Skill ON', '(↓) Down Skill OFF', '(↓) Down Skill ACT',
                           '(←) Left Skill ON', '(←) Left Skill OFF', '(←) Left Skill ACT',
                           '(→) Right Skill ON', '(→) Right Skill OFF', '(→) Right Skill ACT'},
    'SlotMachine': {'Help Text', 'Won Text', 'Lost Text', 'Replay Text', 'CoinFull Text', 'Bet Text', 'Spin Text', 'Yes Text', 'No Text'},
    'Gacha': {'Help Message Text', 'Button Text', 'Get Message Text'},
    'GachaBook': {'Unknown Data', 'Price Text', 'Equip Text', 'Type Text', 'Rank Text'},
    'FilterController': {'enabledAll-Text'},
    'Olivia_SkipCutscene': {'Skip Text'},
    'Aries001_AnimationScreenEffects': {'Options Text Effect Playback', 'Options Text Effect Power'},
}

# These non-numeric parameters have source contracts in their owning enabled
# plugin. The field schema, not the spelling of its value, establishes the role.
TECH_KEYS = {
    'Aetherflow_PreloadEverything': {'ImageCacheSize', 'AudioCacheSize', 'PreloadGlobal', 'PreloadMaps'},
    'Community_Basic': {'renderingMode', 'alwaysDash'},
    'YEP_CoreEngine': {'Chinese Font', 'Korean Font', 'Default Font', 'Text Align'},
    'YEP_LoadCustomFonts': {'Font Filenames', 'Font Families'},
    'TDDP_AnimationCurves': {'Plugin Command key'}, 'TDDP_MovePictureEx': {'movePictureCommand'},
    'YEP_BattleEngineCore': {'Action Speed', 'Default System', 'Escape Ratio', 'Front Position X', 'Front Position Y', 'Home Position X', 'Home Position Y', 'Critical Popup', 'Command Alignment'},
    'YEP_EquipCore': {'Text Align'}, 'YEP_SkillCore': {'Command Alignment'},
    'YEP_BuffsStatesCore': {'Turn Alignment', 'Buff Formula', 'Counter Alignment'},
    'YEP_X_CriticalControl': {'Critical Rate Formula', 'Critical Multplier Formula', 'Flat Critical Formula'},
    'YEP_StealSnatch': {'Bonus Formula', 'Failure Sound', 'Empty Sound', 'Item Sound', 'Weapon Sound', 'Armor Sound', 'Gold Sound'},
    'Exhydra_FollowerControl': {'Interpreter Commands'},
    'YEP_EventCopier': {'TemplateMaps', 'TemplateNames', 'PreCopyCode', 'PostCopyCode'},
    'YEP_EventMorpher': {'TemplateMaps'}, 'YEP_EventSpawner': {'TemplateMaps', 'TemplateNames'},
    'YEP_EventChasePlayer': {'Alert Sound'},
    'GALV_EventDetectors': {'LOS Blocking Regions', 'Behavior 0', 'Behavior 1', 'Behavior 2', 'Behavior 3'},
    'YEP_EventTimerControl': {'TextAlign', 'Effect Code', 'Expire Code'},
    'Text_Language_Processor': {'Default Language'},
    'YEP_MessageCore': {'Default Width', 'Fast Forward Key', 'Font Name', 'Font Name CH', 'Font Name KR'},
    'YEP_X_ExtMesPack1': {'Sound Name', 'Default X', 'Default Y'},
    'Archeia_MessageCodes': {'Variable Set Code', 'Variable Add Code', 'Variable Sub Code', 'Variable Mul Code', 'Variable Div Code', 'Variable Mod Code', 'Common Event Code'},
    'Liquid_EventIcons': {'Default Sprite Sheet'},
    'GALV_AnimatedSplashScreens': {'Splash Images', 'Splash Background', 'Splash Skip'},
    'Active Chain Skills': {'Active Skill Sound'},
    'TDS Text Effects': {'SINV', 'SINH', 'SHAKE', 'RAINBOW'},
    'Gacha': {'ME'}, 'FilterController': {'displacementImage'},
    'Olivia_SkipCutscene': {'Gauge Color 1', 'Gauge Color 2', 'Gauge Position X', 'Gauge Position Y'},
    'Aries001_AnimationScreenEffects': {'Shake Type', 'Shake SE', 'Blur SE', 'ZoomBlur SE', 'Glow SE', 'Wave SE', 'Distort SE'},
    'Aries003_WeatherControl': {'Thunder Sound', 'Leaf Image', 'Embers Image', 'Shine Image'},
    'Olivia_MapDisplayNameCore': {'Dim Color 1', 'Dim Color 2'},
}


def classify(row):
    plugin, key, value = row['plugin'], str(row['path'][-1]), row['source']
    if not row['enabled'] or 'parameters' not in row['path']:
        return 'preserve-exactly', 'Plugin identity/header/disabled-plugin configuration.'
    if not value.strip() or re.fullmatch(r'[-+]?\d+(?:\.\d+)?|true|false|undefined|null', value.strip(), re.I) or value.strip() in {'[]', '{}'}:
        return 'preserve-exactly', 'Original empty, numeric, boolean, sentinel or empty-collection setting.'
    if key in TEXT_KEYS.get(plugin, set()):
        return 'visible', 'Declared display-format/label parameter in owning plugin.'
    if plugin.startswith('YEP_X_MessageMacros'):
        if re.fullmatch(r'Macro \d+ Name', key):
            return 'preserve-exactly', 'Quick-macro dispatch name; preserve exact spelling and numeric priority.'
        if re.fullmatch(r'Macro \d+ Text', key):
            return 'mixed-display', 'Native macro expansion: visible namebox bodies and protected controls must be segmented.'
    if plugin == 'YEP_X_ExtMesPack2' and key.startswith('TextCode '):
        return 'preserve-exactly-program', 'JSON-encoded native escape callback; nested literals inventoried separately.'
    if plugin == 'YEP_Z_PassiveCases' and key == 'Effect Code':
        return 'preserve-exactly-program', 'JSON-encoded passive-condition interpreter.'
    if plugin == 'YEP_DamageCore' and re.fullmatch(r'Damage Step \d+', key):
        return 'preserve-exactly-program', 'Ordered damage formula program component.'
    if plugin == 'YEP_X_AnimatedSVEnemies' and (key in {'Sprite Width', 'Sprite Height', 'Shadow Scale X', 'Shadow Scale Y', 'Attack Motion', 'Idle Motion', 'Damage Motion', 'Evade Motion', 'Escape Motion', 'Guard Motion', 'Abnormal Motion', 'Sleep Motion', 'Dying Motion', 'Dead Motion'} or re.fullmatch(r'Weapon \d+ Motion', key)):
        return 'preserve-exactly', 'Motion/rendering enum or automatic geometry sentinel.'
    if plugin == 'YEP_RegionBattlebacks':
        return 'preserve-exactly', 'Battleback resource name, including native no-resource sentinel.'
    if key == 'ATTENTION!!!' or key.startswith('---'):
        return 'preserve-exactly', 'Plugin-editor instruction/section header; not game display wording.'
    if key in TECH_KEYS.get(plugin, set()):
        return 'preserve-exactly', 'Declared resource, input, geometry, formula or internal configuration schema.'
    return 'needs-role-review', 'Parameter consumer/schema not yet bound.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new immutable parameter output')
    args.output.mkdir(parents=True)
    rows, counts, callbacks, damage = [], Counter(), [], []
    for original in strict_json(args.input.read_bytes()):
        row = dict(original)
        row['role'], row['reason'] = classify(row)
        rows.append(row)
        counts[row['role']] += 1
        key = str(row['path'][-1])
        encoded_callback = (row['enabled'] and (
            row['plugin'] == 'YEP_X_ExtMesPack2' and key.startswith('TextCode ') or
            row['plugin'] in {'YEP_Z_PassiveCases', 'YEP_EventTimerControl', 'YEP_EventCopier'} and key in {'Effect Code', 'Expire Code', 'PreCopyCode', 'PostCopyCode'}))
        if encoded_callback and row['source'].strip():
            body = strict_json(row['source'])
            if not isinstance(body, str):
                raise ValueError('Expected encoded callback string: ' + row['id'])
            callbacks.append({'asset': row['id'] + '@json-callback', 'source': body, 'rawSha256': sha(body.encode()),
                              'parentId': row['id'], 'encoding': 'JSON-string', 'originalSource': row['source']})
        if row['enabled'] and row['plugin'] == 'YEP_DamageCore' and re.fullmatch(r'Damage Step \d+', key):
            damage.append((int(key.split()[-1]), row))
    body = '\n'.join(row['source'] for _, row in sorted(damage))
    callbacks.append({'asset': 'js/plugins.js@YEP_DamageCore:ordered-damage-steps', 'source': body,
                      'rawSha256': sha(body.encode()), 'components': [row['id'] for _, row in sorted(damage)]})
    save_json(args.output / 'parameters.json', rows)
    save_json(args.output / 'callback-programs.json', callbacks)
    helper = Path(__file__).with_name('source_script_inventory.cjs')
    result = subprocess.run(['node', '--expose-internals', str(helper)], input=json.dumps(callbacks),
                            text=True, capture_output=True, check=True)
    ast = strict_json(result.stdout)
    save_json(args.output / 'callback-ast.json', ast)
    save_json(args.output / 'manifest.json', {'schemaVersion': 1, 'inputRawSha256': sha(args.input.read_bytes()),
                                           'recipeRawSha256': sha(Path(__file__).read_bytes()), 'roles': dict(counts),
                                           'callbackPrograms': len(callbacks), 'callbackParseErrors': ast['errors'],
                                           'callbackStrings': len(ast['strings']), 'runtime': 'not-run', 'sourceGate': 'needs-review'})
    print(json.dumps({'roles': dict(counts), 'pending': [{'plugin': r['plugin'], 'key': r['path'][-1], 'source': r['source'][:120]} for r in rows if r['role']=='needs-role-review'],
                      'callbacks': len(callbacks), 'parseErrors': ast['errors'], 'callbackStrings': len(ast['strings'])}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
