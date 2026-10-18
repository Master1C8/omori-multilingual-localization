"""Shared typed source primitives. No locale defaults or wording generation."""
import hashlib
import json
import re
import yaml


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n')


def strict_yaml(text):
    class Loader(yaml.SafeLoader):
        pass
    Loader.yaml_implicit_resolvers = {
        key: [(tag, pattern) for tag, pattern in rows if tag != 'tag:yaml.org,2002:bool']
        for key, rows in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    Loader.add_implicit_resolver('tag:yaml.org,2002:bool',
        re.compile(r'^(?:true|True|TRUE|false|False|FALSE)$'), list('tTfF'))
    def mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            identity = (type(key), key)
            if identity in seen:
                raise ValueError('Duplicate YAML key')
            seen.add(identity)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml.load(text, Loader=Loader)


def encoded(value):
    if isinstance(value, dict):
        return ['dict', [[encoded(k), encoded(v)] for k, v in value.items()]]
    if isinstance(value, list):
        return ['list', [encoded(v) for v in value]]
    return [type(value).__name__, value]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def protected_tree(value, editable, path=()):
    if path in editable:
        return ['visible-hole', editable[path]]
    if isinstance(value, dict):
        return ['dict', [[encoded(k), protected_tree(v, editable, path + (k,))] for k, v in value.items()]]
    if isinstance(value, list):
        return ['list', [protected_tree(v, editable, path + (i,)) for i, v in enumerate(value)]]
    return encoded(value)
