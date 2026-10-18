"""Typed equality at the plaintext boundary, independent of game installation."""
from pathlib import Path
from source_prepare import strict_json, strict_yaml, protected_tree


def parse(asset, raw):
    return strict_json(raw) if Path(asset).suffix in {'.KEL', '.AUBREY'} else strict_yaml(raw.decode())


def compare_protected(original, result, editable):
    if protected_tree(original, editable) != protected_tree(result, editable):
        raise ValueError('Exact protected value/structure/type/order mismatch')
