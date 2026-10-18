import unittest
from pathlib import Path
import json
from classify_plugin_literals import classify

class NativeLiteralRoles(unittest.TestCase):
    def test_native_arguments_inside_display_functions(self):
        root=Path(__file__).resolve().parent.parent
        units={u['id']:u for u in json.loads((root/'source/text-corpus-8879120-02/units.json').read_text())}
        keys=['js/plugins/GTP_OmoriFixes.OMORI@js:94412:94420',
              'js/plugins/GTP_CoreUpdates.OMORI@js:5541:5551',
              'js/rpg_core.js@js:66518:66523','js/rpg_core.js@js:66580:66590']
        for key in keys:
            self.assertEqual(classify(units[key])[0],'preserve-exactly',key)
        # Same owning UI function, genuinely displayed mode caption remains visible.
        caption=next(u for u in units.values() if u['asset']=='js/rpg_core.js' and u['source']=='WebGL mode')
        self.assertEqual(classify(caption)[0],'visible')

if __name__=='__main__':unittest.main()
