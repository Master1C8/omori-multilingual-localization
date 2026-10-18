"""Source-bound display labels; original database/map identities stay untouched."""
from source_prepare import sha


def mapping_row(unit, target):
    if unit['role'] == 'visible-display-mapping' and 'spanUtf16' in unit:
        if (unit.get('nodeType') not in {'Literal', 'TemplateElement'}
                or not isinstance(unit.get('rawSource'), str)
                or len(unit['spanUtf16']) != 2 or unit['spanUtf16'][0] >= unit['spanUtf16'][1]):
            raise ValueError('AST display mapping requires its exact source literal binding')
        return {'id': unit['id'], 'asset': unit['asset'], 'spanUtf16': unit['spanUtf16'],
                'nodeType': unit['nodeType'], 'rawSource': unit['rawSource'],
                'source': unit['source'], 'sourceValueSha256': unit['sourceValueSha256'], 'target': target}
    if (unit['role'] != 'visible-display-mapping' or not unit.get('path')
            or any(k in unit for k in ('spanUtf16', 'span', 'spanCodepoints'))):
        raise ValueError('Scalar display mapping requires its exact typed path')
    return {'id': unit['id'], 'asset': unit['asset'], 'path': unit['path'],
            'source': unit['source'], 'sourceValueSha256': unit['sourceValueSha256'],
            'target': target}


def validate_mapping_document(document, expected, corpus_sha):
    if (document.get('schemaVersion') != 1 or document.get('siteLocale') != 'ru'
            or document.get('steamBuild') != '8879120'
            or document.get('corpusManifestRawSha256') != corpus_sha):
        raise ValueError('Display mapping input binding changed')
    rows = document.get('entries', [])
    if len(rows) != len(expected) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Display mapping ID coverage changed')
    observed = {r['id']: r for r in rows}
    for unit, entry in expected:
        if observed.get(unit['id']) != mapping_row(unit, entry['target']):
            raise ValueError('Display mapping differs from exact source/author data: ' + unit['id'])
        if sha(unit['source'].encode()) != unit['sourceValueSha256']:
            raise ValueError('Display mapping original value digest changed')
    return observed
