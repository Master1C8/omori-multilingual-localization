"""Exact, source-bound Base64 display serialization. Does not generate wording."""
import base64
import binascii
import re
from pathlib import Path
from source_prepare import strict_json, sha
from source_text_syntax import compare_text_controls
from unit_text_controls import compare_unit_controls

DISCOVERY = 'source/encoded-dialogue-8879120-01.json'
DISCOVERY_SHA = '25603f0fb56a8fcb08d807a778ca66c9cf4eaf94a2478a0c6ba107cac7d2e864'
CODEC = 'base64-utf8'
BATTLE_CODEC = 'base64-battle-utf8'
BATTLE_DISCOVERY = 'source/encoded-battle-dialogue-8879120-01.json'
BATTLE_DISCOVERY_SHA = '16396c7a5bda560eda98192627b211fa94cdac30fb2cbf9b9323b4f0b4dfd858'


def decode_battle_display(value, label):
    prefix = '\\>' + label + ': \\<'
    if not value.startswith(prefix) or not value.endswith('\n'):
        raise ValueError('Encoded battle prefix/frame changed')
    payload = value[len(prefix):-1]
    if payload.startswith('<br>'):
        prefix += '<br>'
        payload = payload[4:]
    if not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', payload):
        raise ValueError('Malformed battle Base64 payload')
    try:
        raw = base64.b64decode(payload, validate=True)
        decoded = raw.decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ValueError('Malformed battle Base64 UTF-8 payload') from error
    if base64.b64encode(raw).decode('ascii') != payload:
        raise ValueError('Noncanonical battle Base64 payload')
    return decoded, [payload], prefix + '\n'


def decode_frame(row, value, label):
    if row.get('codec', CODEC) == BATTLE_CODEC:
        return decode_battle_display(value, label)
    return decode_display(value, label)


def decode_display(value, label):
    suffix = '\\n<' + label + '>'
    if not value.endswith(suffix):
        raise ValueError('Encoded native namebox changed')
    blocks = value[:-len(suffix)].split('<br>')
    if not all(re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', b) for b in blocks):
        raise ValueError('Malformed Base64 payload')
    flat = ''.join(blocks)
    try:
        raw = base64.b64decode(flat, validate=True)
        decoded = raw.decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ValueError('Malformed Base64 UTF-8 payload') from error
    if base64.b64encode(raw).decode('ascii') != flat:
        raise ValueError('Noncanonical Base64 payload')
    return decoded, blocks, '<br>'.join([''] * len(blocks)) + suffix


def load_registry(root, units):
    path = root / DISCOVERY
    if sha(path.read_bytes()) != DISCOVERY_SHA:
        raise ValueError('Encoded source discovery changed')
    rows = strict_json(path.read_bytes())['entries']
    registry = {}
    for row in rows:
        unit = units.get(row['id'])
        if (not unit or unit['source'] != row['source'] or unit['asset'] != row['asset']
                or unit['role'] != 'visible' or unit.get('path', [])[-1:] != ['text']
                or row['id'] in registry):
            raise ValueError('Encoded source binding changed')
        decoded, blocks, _ = decode_display(row['source'], 'ROBOHEART')
        if decoded != row['decodedEnglish'] or len(blocks) - 1 != row['lineBreakCount']:
            raise ValueError('Encoded source meaning/layout changed')
        registry[row['id']] = row
    if len(registry) != 5:
        raise ValueError('Encoded discovery count changed')
    path = root / BATTLE_DISCOVERY
    if sha(path.read_bytes()) != BATTLE_DISCOVERY_SHA:
        raise ValueError('Encoded battle discovery changed')
    document = strict_json(path.read_bytes())
    if (document['codec'] != BATTLE_CODEC or document['steamBuild'] != '8879120'
            or document['corpusUnitsRawSha256'] != sha((root / 'source/text-corpus-8879120-02/units.json').read_bytes())):
        raise ValueError('Encoded battle corpus binding changed')
    rows = document['entries']
    if len(rows) != 4:
        raise ValueError('Encoded battle discovery count changed')
    for row in rows:
        unit = units.get(row['id'])
        if (not unit or unit['source'] != row['source'] or unit['asset'] != row['asset']
                or unit['role'] != 'visible' or unit.get('path', [])[-1:] != ['text']
                or row['id'] in registry):
            raise ValueError('Encoded battle source binding changed')
        decoded, _, skeleton = decode_battle_display(row['source'], 'ROBOHEART')
        if decoded != row['decodedEnglish'] or skeleton.count('<br>') != row['lineBreakCount']:
            raise ValueError('Encoded battle source meaning/layout changed')
        registry[row['id']] = dict(row, codec=BATTLE_CODEC)
    return registry


def encode_display(row, decoded_target, target_label):
    if not isinstance(decoded_target, str) or not decoded_target.strip():
        raise ValueError('Empty decoded author target')
    if row.get('codec', CODEC) == BATTLE_CODEC:
        original, _, skeleton = decode_battle_display(row['source'], 'ROBOHEART')
        if (decoded_target.count('\n') != original.count('\n')
                or decoded_target.endswith('\n') != original.endswith('\n')):
            raise ValueError('Decoded battle line breaks changed')
        prefix = '\\>' + target_label + ': \\<'
        if skeleton.count('<br>'):
            prefix += '<br>'
        return prefix + base64.b64encode(decoded_target.encode('utf-8')).decode('ascii') + '\n'
    _, original_blocks, _ = decode_display(row['source'], 'ROBOHEART')
    encoded = base64.b64encode(decoded_target.encode('utf-8')).decode('ascii')
    quanta = len(encoded) // 4
    if quanta < len(original_blocks):
        raise ValueError('Encoded target too short for original line count')
    # Retain original line count and relative layout, with complete Base64 quanta.
    total, cumulative, previous = sum(map(len, original_blocks)), 0, 0
    blocks = []
    for index, block in enumerate(original_blocks[:-1]):
        cumulative += len(block)
        boundary = round(quanta * cumulative / total)
        boundary = max(previous + 1, min(boundary, quanta - (len(original_blocks) - index - 1)))
        blocks.append(encoded[previous * 4:boundary * 4])
        previous = boundary
    blocks.append(encoded[previous * 4:])
    return '<br>'.join(blocks) + '\\n<' + target_label + '>'


def authored_encoding(unit, decoded_target, target_label, registry):
    if unit['id'] not in registry:
        raise ValueError('Encoded codec not authorized for this source ID')
    row = registry[unit['id']]
    codec = row.get('codec', CODEC)
    return encode_display(row, decoded_target, target_label), {
        'codec': codec, 'sourceDiscoveryRawSha256': BATTLE_DISCOVERY_SHA if codec == BATTLE_CODEC else DISCOVERY_SHA,
        'decodedSource': row['decodedEnglish'], 'decodedTarget': decoded_target,
        'lineBreakCount': row['lineBreakCount'], 'targetNamebox': target_label}


def validate_entry(unit, entry, macros, registry, target_label):
    metadata = entry.get('encodedPayload')
    if unit['id'] not in registry:
        if metadata is not None:
            raise ValueError('Encoded codec not authorized for this source ID')
        compare_unit_controls(unit, entry['target'], macros)
        return
    row = registry[unit['id']]
    if unit['source'] != row['source']:
        raise ValueError('Encoded source binding changed')
    codec = row.get('codec', CODEC)
    discovery_sha = BATTLE_DISCOVERY_SHA if codec == BATTLE_CODEC else DISCOVERY_SHA
    if not isinstance(metadata, dict) or metadata.get('codec') != codec:
        raise ValueError('Encoded author metadata required')
    if (metadata.get('sourceDiscoveryRawSha256') != discovery_sha
            or metadata.get('decodedSource') != row['decodedEnglish']
            or metadata.get('lineBreakCount') != row['lineBreakCount']
            or metadata.get('targetNamebox') != target_label):
        raise ValueError('Encoded author source/layout binding changed')
    decoded, _, target_skeleton = decode_frame(row, entry['target'], target_label)
    if decoded != metadata.get('decodedTarget'):
        raise ValueError('Decoded delivered target differs from author data')
    _, _, source_skeleton = decode_frame(row, row['source'], 'ROBOHEART')
    compare_text_controls(source_skeleton, target_skeleton, macros)
    if entry['target'] != encode_display(row, metadata['decodedTarget'], target_label):
        raise ValueError('Encoded delivered layout differs from exact recipe')
