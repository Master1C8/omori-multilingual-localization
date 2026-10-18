"""First save -> X -> Equip -> OMORI -> selected weapon, with no equip confirmation."""
import copy,json,subprocess,os
from mari_route import MariRoute, win
from runtime import state,RUN


def loaded_actor(s):
    first=copy.deepcopy(s.get('firstActor') or {})
    equips=first.get('equips') or []
    if first.get('id')!=1 or not equips or not equips[0] or equips[0].get('id')!=2:
        raise ValueError('First-save weapon identity mismatch: expected actor1 weapon2')
    return first


def equipment_ready(s):
    if not s or s.get('scene')!='Scene_OmoMenuEquip':
        return False
    equip=s.get('equipment') or {}
    first=s.get('firstActor') or {}
    slots=win(s,'Window_OmoMenuActorEquip')
    status=win(s,'Window_OmoMenuEquipStatus')
    selector=win(s,'Window_OmoMenuActorEquipItem')
    help_window=win(s,'Window_OmoMenuHelp')
    # Selecting the displayed weapon again opens the replacement selector.
    # That state must never be credited as this route's terminal screen.
    return (equip.get('actorId')==first.get('id') and bool(first.get('id'))
            and equip.get('actorIndex')==0 and equip.get('slotIndex')==0
            and bool(equip.get('item')) and not equip.get('moving')
            and slots.get('active') and slots.get('index')==0
            and status.get('openness')==255 and not selector.get('active')
            and not selector.get('width',0) and help_window.get('width',0)>=400
            and help_window.get('visible') and help_window.get('contentsOpacity')==255)


class EquipmentRoute(MariRoute):
    def run(self):
        loaded=self.load_first_save()
        first=loaded_actor(loaded)
        def assets_ready(s):
            assets=state().get('equipmentAssets') or {}
            if assets.get('phase')=='error':raise RuntimeError(assets['error'])
            return self.map_at(s,11,15) and assets.get('phase')=='ready'
        self.wait(assets_ready,90)
        self.act('open-character-menu-x',7,
                 lambda s:self.map_at(s,11,15),
                 lambda s:s['scene']=='Scene_Menu' and win(s,'Window_MenuCommand').get('active'),
                 'mari-picnic')
        s=self.read();commands=win(s,'Window_MenuCommand')
        indices=[i for i,c in enumerate(commands['list']) if c['symbol']=='equip' and c['enabled']]
        assert len(indices)==1
        target=indices[0]
        for _ in range(len(commands['list'])):
            s=self.read();current=win(s,'Window_MenuCommand')['index']
            if current==target:break
            expected=(current+1)%len(commands['list'])
            self.act('choose-equip-'+str(current),124,
                     lambda s,i=current:s['scene']=='Scene_Menu' and win(s,'Window_MenuCommand').get('active') and win(s,'Window_MenuCommand')['index']==i,
                     lambda s,i=expected:s['scene']=='Scene_Menu' and win(s,'Window_MenuCommand')['index']==i,
                     'character-menu-frame')
        else:raise RuntimeError('Equip command not reached within menu bound')
        self.act('select-equip-command',6,
                 lambda s:s['scene']=='Scene_Menu' and win(s,'Window_MenuCommand').get('active') and win(s,'Window_MenuCommand')['index']==target,
                 lambda s:s['scene']=='Scene_Menu' and win(s,'Window_OmoMainMenuPartyStatus').get('active') and win(s,'Window_OmoMainMenuPartyStatus')['index']==0,
                 'character-menu-frame')
        self.act('select-omori',6,
                 lambda s:s['scene']=='Scene_Menu' and win(s,'Window_OmoMainMenuPartyStatus').get('active') and win(s,'Window_OmoMainMenuPartyStatus')['index']==0,
                 equipment_ready,'character-menu-frame',timeout=180)
        s=self.wait(equipment_ready)
        assert s['firstActor']==first,'Actor/equipment changed during view-only navigation'
        assert s['equipment']['item']==first['equips'][0]
        path,marker,window=self.frame('final-equipment','equipment-knife')
        s=self.read();assert equipment_ready(s) and s['firstActor']==first
        native_focus=json.loads(subprocess.check_output([str(RUN/'native-control'),str(self.pid),'state']))
        return dict(frame=str(path),marker=marker,window=window,state=state(),gameplay=s,
                    inputMethod='game-thread-dom-bridge' if os.environ.get('OMORI_QA_INPUT_MODE')=='bridge' else 'native-pid-targeted-keyboard',
                    nativeFocusAtCapture=native_focus,
                    actions=len(self.steps),saveSlotLoaded=1,saveSlotsWritten=False,
                    equipmentChanged=False,menuOpeningKey='X',reference='20261018-fourth-reference',
                    backgroundMode='Temporary native focus-pause adapter and launch flags; no activation')
