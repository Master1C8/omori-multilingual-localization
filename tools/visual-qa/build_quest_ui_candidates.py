"""Apply the positively controlled shared UI repair to pending locale packages."""
import json
from pathlib import Path
from ui_derivative import ROOT,create,relative
folder=ROOT/'diagnostics/native-artifacts-20261017';parents=json.loads((folder/'repaired-packages-02.json').read_text())
rtl=json.loads((folder/'repaired-packages-03.json').read_text());fa=json.loads((folder/'repaired-packages-04.json').read_text())
for code in ['ar','he']:parents[code]=rtl[code]
parents['fa']=fa['fa']
base=json.loads((ROOT/'runtime/visual-qa/20261017-native/baseline.json').read_text())
selected=[c for c in base['requiredLocales'] if c not in {'ru','hi','th','zh-TW','vi'}];assert len(selected)==22
mapping_path=folder/'quest-ui-packages-07.json';assert not mapping_path.exists();mapping={}
for code in selected:
    parent=parents[code];name='build/multilingual-delivery/'+code+'/'
    mapping[code]=create(code,parent['build'],parent['archive'],'diagnostics/native-artifacts-20261017/quest-ui-positive-control-07.json',name+'native-quest-ui-20261017-07',name+'OMORI-'+code+'-quest-ui-20261017-07.zip')
    mapping_path.write_text(json.dumps(mapping,indent=2)+'\n');print('DERIVED',code,flush=True)
print('COMPLETE22; mandatory locale list remains27',flush=True)
