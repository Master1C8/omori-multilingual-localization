"""Exact source-path keys for direct model authoring; never generates wording."""
import json


def target_key(unit, mode='catalog-text'):
    if mode == 'source-id':
        if unit.get('role') not in {'visible', 'visible-display-mapping'} or not isinstance(unit.get('id'), str):
            raise ValueError('Source-ID mode requires an accepted visible occurrence')
        return unit['id']
    path = unit.get('path', [])
    roles = {'visible', 'visible-display-mapping'} if mode == 'display-path' else {'visible'}
    if (unit.get('role') not in roles or not path
            or any(name in unit for name in ('span', 'spanCodepoints', 'spanUtf16'))):
        raise ValueError('Requires a different exact authoring adapter: ' + unit['id'])
    if mode == 'catalog-text':
        if len(path) != 2 or path[-1] != 'text' or not isinstance(path[0], str):
            raise ValueError('Catalog requires full source-path keys: ' + unit['id'])
        return path[0]
    if mode in {'json-path', 'display-path'}:
        if any(type(part) not in (str, int) for part in path):
            raise ValueError('Unsupported source-path component: ' + unit['id'])
        return json.dumps(path, ensure_ascii=False, separators=(',', ':'))
    raise ValueError('Unknown authoring target-key mode: ' + str(mode))
