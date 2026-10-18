"""Consumer-bound grammar refinements for literal UI labels, not HTML tags."""
import re
from source_text_syntax import compare_text_controls


def compare_unit_controls(unit, target, macros=()):
    # YEP_EquipCore.drawEmptySlot passes this whole parameter to drawText.
    # The angle-bracket body is visible text; drawText has no HTML parser.
    # Bind to the accepted plugin/field/source, never all angle-bracket words.
    is_angle_label = (unit.get('asset') == 'js/plugins.js'
        and unit.get('plugin') == 'YEP_EquipCore'
        and unit.get('path', [])[-2:] == ['parameters', 'Empty Text']
        and unit.get('role') == 'visible' and unit['source'] == '<Empty>')
    if is_angle_label:
        if not re.fullmatch(r'<[^<>\r\n]+>', target):
            raise ValueError('Literal angle-label wrapper changed')
        compare_text_controls(unit['source'], '<Empty>', macros)
        compare_text_controls('', target[1:-1], macros)
    else:
        compare_text_controls(unit['source'], target, macros)
