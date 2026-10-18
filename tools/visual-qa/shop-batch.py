"""Sixth-screen native capture; protect all 135 accepted frames and save bytes."""
import json,os,sys,shutil,time
from pathlib import Path
from runtime import ROOT,RUN,GAME,sha,save,processes,check_saves,check_desktop,launch,stop,resource_baseline
from batch import apply,restore
from shop_route import ShopRoute
OUTPUT=ROOT/'dist/screenshots/20261017-native'

def main():
    assert os.environ.get('OMORI_QA_BACKGROUND')=='1'
    selected=sys.argv[1:];assert selected and len(selected)==len(set(selected))
    diagnostic=os.environ.get('OMORI_QA_DIAGNOSTIC')=='shop-draw'
    protected=json.loads((RUN/'protected-135.json').read_text());assert len(protected)==135
    verified=[]
    try:
        for code in selected:
            dest=RUN/code/'diagnostic-shop.png' if diagnostic else OUTPUT/(code+'-06-mailbox-jacks.png');assert not dest.exists()
            assert all(sha(OUTPUT/n)==h for n,h in protected.items())
            check_desktop();check_saves();apply(code);pid=launch(code);route=None
            try:
                route=ShopRoute(pid,RUN/code);receipt=route.run()
                shutil.copyfile(receipt['frame'],dest)
                receipt.update(locale=code,runtimeChannel='en',file=dest.name,sha256=sha(dest),dimensions=[1280,960],
                               automatedResult='pass',visualReview='pending',captureMethod='Oculix 4.0.0 Finder and unchanged native macOS window content')
                save(RUN/code/'shop-capture.json',receipt);verified.append(code)
                print('SHOP_CAPTURED',code,flush=True)
            except BaseException as error:
                if route:
                    try:
                        frame,_,_=route.frame('failure');save(RUN/code/'shop-failure.json',dict(error=repr(error),frame=str(frame)))
                    except Exception:pass
                raise
            finally:
                if route:route.close()
                stop()
            if diagnostic:continue
            gate=RUN/code/'visual-review.json';end=time.monotonic()+1800
            print('AWAITING_SHOP_REVIEW',code,flush=True)
            while not gate.exists():
                assert time.monotonic()<end,'Shop review gate timeout'
                time.sleep(1)
            review=json.loads(gate.read_text())
            assert review['status']=='pass' and review['file']==receipt['file'] and review['sha256']==receipt['sha256'],'Shop review rejected or mismatched'
        save(RUN/'shop-status.json',dict(status='diagnostic-complete' if diagnostic else 'complete',locales=selected,allVisualReviewsPassed=not diagnostic))
    except BaseException as error:
        save(RUN/'shop-status.json',dict(status='stopped',error=repr(error)));raise
    finally:
        if (RUN/'owned-game.json').exists():
            # stop() also reconciles recorded surviving children after root exit.
            stop()
        restore()
        r=json.loads((RUN/'restoration.json').read_text())
        loaded=[];unknown=[]
        for code in selected:
            proof=RUN/code/'load-first-save-semantic-result.json'
            if proof.exists():
                s=json.loads(proof.read_text())
                if s.get('scene')=='Scene_Map' and s.get('map',{}).get('id')==92:loaded.append(code)
                else:unknown.append(code)
            elif (RUN/code/'load-first-save-before.json').exists():unknown.append(code)
        r.update(saveSlotsLoaded=True if loaded else (None if unknown else False),saveSlotLoadedPerLocale=1 if len(loaded)==len(selected) else None,
                 verifiedLoadedLocales=loaded,loadEvidenceUnknownLocales=unknown,saveSlotsWritten=False,resourceProfile=resource_baseline()[1])
        save(RUN/'restoration.json',r)
        assert all(sha(OUTPUT/n)==h for n,h in protected.items())
        for p in RUN.glob('*/package-before.json'):assert (GAME/'package.json').read_bytes()==p.read_bytes()

if __name__=='__main__':main()
