#!/usr/bin/env python3
"""Native RPG text protection, with quick-macro precedence over word tokens."""
import re

NAMEBOX = re.compile(r'\\(?:N[1-5]?|NC|NR)<', re.I)
ANGLE_CONTROL = re.compile(r'\\(?:FN|FNA|FSN)<[^>]*>', re.I)
BRACKET_CONTROL = re.compile(r'\\[A-Za-z]+\[[^\]\r\n]*\]')
WORD_CONTROL = re.compile(r'\\[A-Za-z]+')
HTML = re.compile(r'</?[A-Za-z][^>]*>')
PLACEHOLDER = re.compile(r'%\d+')
NUMBER = re.compile(r'\d+(?:[.,]\d+)*')
LOCALIZED_NUMBER = re.compile(r'\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)*')
MARKER = re.compile(r'\[(?:S|BOOK|TOY|TRASH)\]')
NATIVE_SYMBOLS = set('$ .|^!><{}\\'.replace(' ', ''))


def quick_macro_names(parameters):
    """Build the native numeric-priority table, including literal sentinels."""
    mapping = {}
    for row in parameters:
        match = re.fullmatch(r'Macro (\d+) Name', str(row['path'][-1]))
        if row['enabled'] and row['plugin'].startswith('YEP_X_MessageMacros') and match:
            plugin_number = int(row['plugin'].removeprefix('YEP_X_MessageMacros'))
            index = int(match[1])
            if (plugin_number - 1) * 100 < index <= plugin_number * 100:
                name = row['source']
                if not re.fullmatch(r'[A-Za-z0-9_]+', name):
                    raise ValueError('Quick macro name requires a regex-specific binding: ' + repr(name))
                mapping[index] = name
    return [(index, name) for index, name in sorted(mapping.items())]


def protected_parts(source, macros=(), start=0, stop=None, number_pattern=NUMBER):
    """Return exact technical spans; remaining text is eligible for authoring.

    Coordinates are Unicode codepoints. JS program adapters separately handle
    UTF-16 offsets, so astral characters cannot shift original literal spans.
    Literal apostrophe/quote escapes are text encodings, not RPG instructions.
    Native unknown alphabetic commands remain protected, matching obtainEscapeCode.
    """
    stop = len(source) if stop is None else stop
    result, index = [], start
    def retain(end, kind):
        nonlocal index
        if end > stop:
            raise ValueError('Native text syntax crosses its enclosing field')
        result.append({'spanCodepoints': [index, end], 'source': source[index:end], 'kind': kind})
        index = end
    while index < stop:
        if source[index] == '\\':
            if index + 1 < stop and source[index + 1] == '\\':
                retain(index + 2, 'native-double-backslash'); continue
            macro = next((name for _, name in macros if source[index + 1:index + 1 + len(name)].lower() == name.lower()), None)
            if macro:
                retain(index + 1 + len(macro), 'quick-macro-prefix'); continue
            angle = ANGLE_CONTROL.match(source, index)
            if angle:
                retain(angle.end(), 'font-resource-angle-control'); continue
            box = NAMEBOX.match(source, index)
            if box:
                close = source.find('>', box.end(), stop)
                if close < 0:
                    # The original converter only consumes a complete <...>
                    # namebox. Keep a malformed opener exact as an accounted
                    # original anomaly; never silently insert its missing >.
                    retain(box.end(), 'native-unclosed-namebox-open'); continue
                retain(box.end(), 'native-namebox-open')
                result.extend(protected_parts(source, macros, index, close, number_pattern))
                index = close
                retain(close + 1, 'native-namebox-close'); continue
            bracket = BRACKET_CONTROL.match(source, index)
            if bracket:
                retain(bracket.end(), 'native-command-argument'); continue
            word = WORD_CONTROL.match(source, index)
            if word:
                retain(word.end(), 'native-command-code'); continue
            if index + 1 < stop and source[index + 1] in NATIVE_SYMBOLS:
                retain(index + 2, 'native-symbol-command'); continue
            # Escaped literal quotes/apostrophes/hash/space are not code words.
            # Their encoding is reconstructed by each owning JSON/YAML/JS codec.
            index += 2 if index + 1 < stop else 1
            continue
        token = HTML.match(source, index) or MARKER.match(source, index) or PLACEHOLDER.match(source, index) or number_pattern.match(source, index)
        if token:
            kind = 'html-control' if token.re is HTML else 'native-minigame-marker' if token.re is MARKER else 'format-placeholder' if token.re is PLACEHOLDER else 'original-number'
            retain(token.end(), kind); continue
        index += 1
    return result


def signature(source, macros=(), number_pattern=NUMBER):
    return [(p['kind'], p['source']) for p in protected_parts(source, macros, number_pattern=number_pattern)]


def russian_number_presentations(original):
    """Permit only exact English-to-Russian formatting, never value conversion.

    Dates, versions, IDs and control arguments have no presentation exception.
    Fraction digits and precision remain exact. An English grouped integer must
    become a grouped integer, not a Russian decimal with the same punctuation.
    """
    variants = {original}
    if re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?', original):
        integer, dot, fraction = original.partition('.')
        for space in (' ', '\u00a0', '\u202f'):
            variants.add(integer.replace(',', space) + (',' + fraction if dot else ''))
    elif re.fullmatch(r'\d+\.\d+', original):
        variants.add(original.replace('.', ','))
    return variants


def compare_text_controls(original, target, macros=()):
    expected, observed = signature(original, macros), signature(target, macros)
    if expected == observed:
        return
    localized = signature(target, macros, LOCALIZED_NUMBER)
    if len(expected) == len(localized) and all(
            ek == ok and (ov in russian_number_presentations(ev) if ek == 'original-number' else ev == ov)
            for (ek, ev), (ok, ov) in zip(expected, localized)):
        return
    raise ValueError('Exact native text controls/numbers changed: ' + repr((expected, observed)))
