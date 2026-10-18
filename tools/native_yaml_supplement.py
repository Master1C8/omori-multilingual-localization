"""Bind the shared recovered native YAML inventory to explicitly authored RU text."""
import json,hashlib
from pathlib import Path
from source_prepare import strict_yaml

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_supplement(root):
    folder=root/'source/native-yaml-8879120-01';manifest_path=folder/'manifest.json'
    if not manifest_path.exists():return [],{}
    manifest=json.loads(manifest_path.read_text());base=root/manifest['baseCorpusManifest']['path']
    if digest(base)!=manifest['baseCorpusManifest']['sha256']:raise ValueError('Native YAML base source changed')
    for name,h in manifest['files'].items():
        if digest(folder/name)!=h:raise ValueError('Native YAML source extension changed: '+name)
    units=json.loads((folder/'units.json').read_text());author_path=root/'translation/ru/native-yaml-supplement.json';author=json.loads(author_path.read_text())
    if author['siteLocale']!='ru':raise ValueError('Wrong native YAML target locale')
    entries={e['id']:e for e in author['entries']}
    if len(entries)!=len(author['entries']) or set(entries)!={u['id'] for u in units}:raise ValueError('Native YAML extension coverage mismatch')
    from script_resource_adapter import original_resource,at
    pairs=[]
    for u in units:
        e=entries[u['id']]
        if not isinstance(e['target'],str) or not e['target'].strip() or e['source']!=u['source']:raise ValueError('Invalid native YAML author entry')
        text,parsed=original_resource(root,u['asset'])
        if at(parsed,u['path'])!=u['source']:raise ValueError('Native YAML source scalar changed')
        pairs.append((u,e))
    dependencies={str(p.relative_to(root)):digest(p) for p in [manifest_path,folder/'units.json',author_path,Path(__file__).resolve()]}
    return pairs,dependencies
