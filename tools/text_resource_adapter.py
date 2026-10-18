#!/usr/bin/env python3
"""Exact source-span reinsertion primitives for pretranslated resources.

Adapters operate on immutable source snapshots. They never search/replace words
or write to the installed game. Full-resource assembly binds these primitives to
the shared occurrence IDs and compares all other typed original values.
"""
import json
from hashlib import sha256
from source_text_syntax import compare_text_controls


def js_literal(target, original_raw, node_type):
    if node_type == 'Literal':
        encoded = json.dumps(target, ensure_ascii=False).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        # Physical line continuations are invisible to the JS value. Keep the
        # original event-program line cardinality without changing the value.
        prefix = '\\\n' * original_raw.count('\n')
        return encoded[:1] + prefix + encoded[1:]
    if node_type == 'TemplateElement':
        encoded = target.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
        encoded = encoded.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
        return '\\\n' * original_raw.count('\n') + encoded
    raise ValueError('Unsupported editable JS node type: ' + node_type)


def splice(source, edits, *, utf16=False):
    """Apply exact, nonoverlapping source edits and verify every untouched byte."""
    raw = source.encode('utf-16-le') if utf16 else source
    scale = 2 if utf16 else 1
    chunks, cursor = [], 0
    for edit in sorted(edits, key=lambda e: e['span'][0]):
        start, stop = (v * scale for v in edit['span'])
        if start < cursor or stop < start or stop > len(raw):
            raise ValueError('Overlapping or invalid source span: ' + edit['id'])
        expected = edit['original'].encode('utf-16-le') if utf16 else edit['original']
        replacement = edit['replacement'].encode('utf-16-le') if utf16 else edit['replacement']
        if raw[start:stop] != expected:
            raise ValueError('Pinned original span changed: ' + edit['id'])
        chunks.extend([raw[cursor:start], replacement])
        cursor = stop
    chunks.append(raw[cursor:])
    result = (b''.join(chunks).decode('utf-16-le') if utf16 else ''.join(chunks))
    # Construction retains every original inter-span byte. A second pass tests
    # the actual output boundary, with offsets adjusted for replacement lengths.
    output = result.encode('utf-16-le') if utf16 else result
    old_cursor = new_cursor = 0
    for edit in sorted(edits, key=lambda e: e['span'][0]):
        start, stop = (v * scale for v in edit['span'])
        gap = start - old_cursor
        if output[new_cursor:new_cursor + gap] != raw[old_cursor:start]:
            raise ValueError('Protected source outside a visible span changed')
        replacement = edit['replacement'].encode('utf-16-le') if utf16 else edit['replacement']
        new_cursor += gap + len(replacement)
        old_cursor = stop
    if output[new_cursor:] != raw[old_cursor:]:
        raise ValueError('Protected source suffix changed')
    return result


def literal_edit(row, target, macros=()):
    compare_text_controls(row['source'], target, macros)
    return {'id': row['id'], 'span': row['spanUtf16'], 'original': row['rawSource'],
            'replacement': js_literal(target, row['rawSource'], row['nodeType'])}


def exact_span_edit(row, target, macros=()):
    compare_text_controls(row['source'], target, macros)
    return {'id': row['id'], 'span': row.get('spanCodepoints', row.get('span')),
            'original': row['source'], 'replacement': target}


def verify_delivered_spans(original, delivered, edits, macros=()):
    """Verify complete mixed field and return targets at adjusted exact boundaries."""
    for unit, _ in edits:
        if ('parentValueSha256' in unit
                and sha256(original.encode()).hexdigest() != unit['parentValueSha256']):
            raise ValueError('Pinned original mixed field changed')
    parts = [exact_span_edit(unit, entry['target'], macros) for unit, entry in edits]
    expected = splice(original, parts)
    if delivered != expected:
        raise ValueError('Delivered mixed field differs from exact source-span assembly')
    result, adjustment = {}, 0
    for part in sorted(parts, key=lambda p: p['span'][0]):
        start, stop = part['span']
        output_start = start + adjustment
        target = delivered[output_start:output_start + len(part['replacement'])]
        if target != part['replacement']:
            raise ValueError('Delivered target at adjusted source boundary differs')
        result[part['id']] = target
        adjustment += len(target) - (stop - start)
    return result
