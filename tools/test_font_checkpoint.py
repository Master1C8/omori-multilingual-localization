"""Real checkpoint positive control and targeted stale-input rejection boundaries."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools/multilingual/delivery'),str(ROOT/'tools/multilingual'),str(ROOT/'tools')]
from font_checkpoint import checkpoint,reuse
parent=ROOT/'build/multilingual-delivery/vi/native-visual-repair-20261017-02'
old=json.loads((parent/'manifest.json').read_text());ctx=SimpleNamespace(root=ROOT,locale='vi');receipt=checkpoint(ROOT,parent)
payload,probes,evidence=reuse(ctx,old['inputs'],old['config'],receipt)
assert evidence==old['fonts'] and len(probes)==len(evidence['faces']) and payload
def rejects(inputs,config,proof,reason):
    try:reuse(ctx,inputs,config,proof)
    except ValueError as error:assert reason in str(error),str(error)
    else:raise AssertionError('Expected specific rejection: '+reason)
bad=copy.deepcopy(old['inputs']);bad['mappingSha256']='0'*64
rejects(bad,old['config'],receipt,'authored/source inputs changed')
bad=copy.deepcopy(old['config']);bad['keyboardExtra']+='!'
rejects(old['inputs'],bad,receipt,'locale configuration changed')
bad=dict(receipt,manifestSha256='0'*64)
rejects(old['inputs'],old['config'],bad,'evidence changed')
print('PASS real font payload/probe reuse; stale authors, changed locale configuration and altered parent evidence reject at their intended boundaries. Native shaping is verified separately.')
