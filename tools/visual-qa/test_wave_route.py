"""Guard unit controls replace runtime fields; native animation is checked separately."""
import copy,unittest
from wave_route import wave_ready,native_text_changed
class WaveGuard(unittest.TestCase):
 def test_only_complete_active_original_vertical_wave(self):
  positive=dict(complete=True,openness=255,effects=[dict(name='SINV',active=True,amplitude=.2)],sprites=[dict(anchorY=0),dict(anchorY=.05)])
  self.assertTrue(wave_ready(positive))
  for field,value in [('complete',False),('openness',0),('sprites',[{}]),('sprites',[dict(anchorY=.02),dict(anchorY=.02)])]:
   with self.subTest(field=field):
    negative=copy.deepcopy(positive);negative[field]=value;self.assertFalse(wave_ready(negative))
  for field,value in [('name','SINH'),('active',False),('amplitude',0)]:
   with self.subTest(effect=field):
    negative=copy.deepcopy(positive);negative['effects'][0][field]=value;self.assertFalse(wave_ready(negative))
 def test_continue_indicator_cannot_prove_text_motion(self):
  from PIL import Image
  first=Image.new('RGB',(1280,960));second=first.copy()
  second.putpixel((1180,915),(255,255,255))
  self.assertFalse(native_text_changed(first,second))
  second.putpixel((120,810),(255,255,255))
  self.assertTrue(native_text_changed(first,second))
if __name__=='__main__':unittest.main()
