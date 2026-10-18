#!/usr/bin/env python3
"""Trace static item-shop configurations without inventing speaker identities.

This supplements namebox extraction. Configuration references and event calls
are evidence of consumers, not proof of runtime reachability or dialogue agency.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import yaml

from research_source import decrypt
from source_prepare import strict_yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    index = project / 'source/research-8879120-02/strings.jsonl'
    plugin_path = args.game_root / 'js/plugins/Omori Item Shop.OMORI'
    plugin, plugin_hash = decrypt(plugin_path)
    system_text, system_hash = decrypt(args.game_root / 'languages/en/System.HERO')
    menu = strict_yaml(system_text)['plugins']['itemShopMenu']
    original_labels = json.loads((index.parent / 'speaker-labels.json').read_text())
    labelled_ids = {key for row in original_labels for key in row['sourceIds']}
    setup_calls = {name: [] for name in menu['shopKeepers']}
    reference_ids = set()
    for settings in menu['shopKeepers'].values():
        for target in settings['texts'].values():
            catalog, message = target.split('.')
            reference_ids.add('languages/en/' + catalog + '.HERO#' +
                              json.dumps([message, 'text'], separators=(',', ':')))
    records = {}
    for line in index.open():
        row = json.loads(line)
        if row['id'] in reference_ids:
            records[row['id']] = row
        for match in re.finditer(r"\b(?:this\.)?setupShop\(\s*(['\"])([^'\"]+)\1\s*,\s*([01])\s*\)", row['source']):
            name = match[2].lower()
            assert name in setup_calls, ('Unknown shop configuration', name, row['id'])
            setup_calls[name].append({'consumerId': row['id'], 'shopType': int(match[3])})
    assert set(records) == reference_ids, 'Shop references missing from pinned index'
    profiles = []
    for name, settings in menu['shopKeepers'].items():
        texts = []
        for field, target in settings['texts'].items():
            catalog, message = target.split('.')
            source_id = 'languages/en/' + catalog + '.HERO#' + json.dumps([message, 'text'], separators=(',', ':'))
            config_id = 'languages/en/System.HERO#' + json.dumps(
                ['plugins', 'itemShopMenu', 'shopKeepers', name, 'texts', field], separators=(',', ':'))
            texts.append({'slot': field, 'configurationId': config_id,
                          'sourceId': source_id,
                          'extractedNamebox': source_id in labelled_ids,
                          'speakerAttribution': 'requires-authored-context-review'})
        profiles.append({'shopKey': name, 'setupCalls': setup_calls[name],
                         'transactionReferences': texts,
                         'headerFields': ['shopName', 'buyHeader', 'sellHeader'],
                         'glossaryId': None})
    boundaries = []
    for number, line in enumerate(plugin.splitlines(), 1):
        if re.search(r'getPluginText\(|showLanguageMessage\(|drawText\(\$gameTemp\._shopData\.transactionHeader', line):
            boundaries.append({'line': number, 'source': line.strip()})
    output = {'schemaVersion': 1, 'steamBuild': '8879120', 'researchOnly': True,
              'researchIndexRawSha256': hashlib.sha256(index.read_bytes()).hexdigest(),
              'plugin': {'asset': 'js/plugins/Omori Item Shop.OMORI', 'encryptedSha256': plugin_hash,
                         'consumerBoundaries': boundaries},
              'systemEncryptedSha256': system_hash,
              'profiles': profiles,
              'limitations': ['Static configuration/event-call inventory, not runtime reachability.',
                              'Headers and unlabelled quantity prompts do not prove a named speaker.',
                              'No inferred identity, gender or owner-policy acceptance.',
                              'Other dynamic consumers, plugin literals and image text remain pending.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'profiles': len(profiles), 'transactionSlots': sum(len(p['transactionReferences']) for p in profiles),
                      'distinctReferencedMessages': len(records),
                      'setupCalls': sum(len(p['setupCalls']) for p in profiles),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
