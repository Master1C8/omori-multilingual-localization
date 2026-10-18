"""Run one immutable Mari batch and restore the accepted Russian level repair.

Catalogs with the repaired Russian row keep that baseline directly. Historical
catalogs use guarded three-file upgrades; the original receipt is never rewritten.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from runtime import resource_baseline
import runtime as capture_runtime
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--route',choices=['mari','equipment','wave','shop'],default='mari');p.add_argument('locales',nargs='+');a=p.parse_args()
root=Path(__file__).resolve().parents[2];run=a.run.resolve();catalog=a.catalog.resolve()
assert run.is_relative_to(root/'runtime/visual-qa') and catalog.is_relative_to(root/'build/installer')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fix=json.loads((root/'runtime/visual-qa/20261017-ru-level-proof-01/ru-level-fix.json').read_text())
game=Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
assert fix['status']=='verified' and not (run/'adoption.json').exists()
assert all(sha(run/n)==h for n,h in json.loads((run/'recipe-manifest.json').read_text()).items())
capture_runtime.RUN=run;capture_runtime.CATALOG=catalog
capture_runtime.check_desktop();capture_runtime.check_saves()
assert not any(v['command'].startswith(str(capture_runtime.APP)+'/') and not v['state'].startswith('Z') for v in capture_runtime.processes().values()),'Existing game or surviving helper blocks resource changes'
assert all((sha(game/k) if (game/k).exists() else None)==h for k,h in fix['finalRussianAssets'].items())
_,profile=resource_baseline(json.loads((catalog/'catalog.json').read_text()))
def upgrade(previous,build,directory):
 cmd=[sys.executable,'-B',str(root/'tools/upgrade_ru_direct.py'),'--previous',str(root/previous),'--build',str(root/build),'--output',str(directory)]
 plan=json.loads(subprocess.check_output(cmd,text=True));assert len(plan['changedFiles'])==3
 subprocess.check_call(cmd+['--apply',plan['fingerprint']])
env=dict(os.environ,OMORI_QA_PROJECT=str(root),OMORI_QA_RUN=str(run),OMORI_QA_CATALOG=str(catalog),OMORI_QA_BACKGROUND='1',OMORI_QA_INPUT_MODE='bridge' if a.route in ('equipment','wave','shop') else 'native')
if profile=='historical-russian':upgrade(fix['newNativeBuild'],fix['oldNativeBuild'],run/'ru-baseline-entry')
try:
 subprocess.check_call([sys.executable,'-B',str(run/'snapshot/adopt-verified-ru.py')],cwd=root,env=env)
 subprocess.check_call([sys.executable,'-B',str(run/('snapshot/'+a.route+'-batch.py')),*a.locales],cwd=root,env=env)
finally:
 restored=run/'restoration.json'
 if restored.exists() and json.loads(restored.read_text())['status']=='verified':
  if profile=='historical-russian':upgrade(fix['oldNativeBuild'],fix['newNativeBuild'],run/'ru-repair-exit')
  assert all((sha(game/k) if (game/k).exists() else None)==h for k,h in fix['finalRussianAssets'].items())
  baseline=json.loads((root/'runtime/visual-qa/20261017-native/baseline.json').read_text())
  assert {str(q.relative_to(game/'save')):sha(q) for q in (game/'save').rglob('*') if q.is_file()}==baseline['saves']
  (run/'russian-level-restoration.json').write_text(json.dumps({'status':'verified','resourcePaths':363,'protectedFiles':8,'locale':'ru','levelRepairRestored':True,'resourceProfile':profile},indent=2)+'\n')
 else:
  raise RuntimeError('Capture cleanup unverified; preserve live-process identity and reconcile before restoring Russian resources')
