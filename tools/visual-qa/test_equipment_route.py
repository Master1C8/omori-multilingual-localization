"""Terminal-state controls; fixtures replace engine state, not native rendering."""
import copy,unittest
from equipment_route import equipment_ready,loaded_actor
from mari_route import ack

class EquipmentGuards(unittest.TestCase):
    def setUp(self):
        self.state=dict(scene='Scene_OmoMenuEquip',firstActor={'id':1},
          equipment=dict(actorId=1,actorIndex=0,slotIndex=0,item={'id':2},moving=False),
          windows=[dict(type='Window_OmoMenuActorEquip',active=True,index=0),
                   dict(type='Window_OmoMenuEquipStatus',openness=255),
                   dict(type='Window_OmoMenuActorEquipItem',active=False,width=0),
                   dict(type='Window_OmoMenuHelp',width=465,visible=True,contentsOpacity=255)])
    def test_matching_positive_control(self):self.assertTrue(equipment_ready(self.state))
    def test_replacement_selector_is_not_terminal(self):
        self.state['windows'][2].update(active=True,width=240)
        self.assertFalse(equipment_ready(self.state))
    def test_wrong_actor_is_not_terminal(self):
        self.state['equipment']['actorId']=2
        self.assertFalse(equipment_ready(self.state))
    def test_charm_slot_is_not_weapon(self):
        self.state['equipment']['slotIndex']=1
        self.assertFalse(equipment_ready(self.state))
    def test_loading_help_is_not_presented_description(self):
        self.state['windows'][3]['width']=0
        self.assertFalse(equipment_ready(self.state))
    def test_moving_panel_is_not_ready(self):
        self.state['equipment']['moving']=True
        self.assertFalse(equipment_ready(self.state))
    def test_actual_first_save_weapon_identity(self):
        source=dict(firstActor=dict(id=1,equips=[{'id':2,'name':'SHINY KNIFE'},None]))
        self.assertEqual(loaded_actor(source),source['firstActor'])
        wrong=copy.deepcopy(source);wrong['firstActor']['equips'][0]['id']=1
        with self.assertRaisesRegex(ValueError,'First-save weapon identity mismatch'):
            loaded_actor(wrong)
    def test_background_requires_native_inactive_game(self):
        control=dict(targetPid=123,targetActive=False,frontmostPid=456)
        ack.assert_background_focus(control)
        active=dict(control,targetActive=True)
        with self.assertRaisesRegex(ValueError,'Background capture refuses foreground game input'):
            ack.assert_background_focus(active)
        front=dict(control,frontmostPid=123)
        with self.assertRaisesRegex(ValueError,'Background capture refuses foreground game input'):
            ack.assert_background_focus(front)

if __name__=='__main__':unittest.main()
