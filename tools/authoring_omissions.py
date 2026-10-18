"""Explicit source-bound omission of grammatical AST fragments after paired edit."""
from source_prepare import sha


def validate_target_presence(unit, entry):
    target = entry.get('target')
    if not isinstance(target, str):
        raise ValueError('Invalid authored target type')
    omission = entry.get('syntacticOmission')
    if target.strip():
        if omission is not None:
            raise ValueError('Omission metadata on nonempty target')
        return
    if (unit.get('role') != 'visible' or 'spanUtf16' not in unit
            or not isinstance(omission, dict)
            or omission.get('kind') != 'grammatical-fragment'
            or not isinstance(omission.get('reason'), str) or not omission['reason'].strip()
            or omission.get('sourceValueSha256') != sha(unit['source'].encode())):
        raise ValueError('Blank target requires an exact authored grammatical-fragment omission')


def validate_source_disposition(unit, entry):
    disposition = entry.get('sourceRoleDisposition')
    if disposition is None:
        return
    pizza = unit.get('asset')=='languages/en/XX_BLUE.HERO' and unit.get('path') in [
        ['Yin_Pizza_Delivery','theNo',0],['Yin_Pizza_Delivery','theNo',1]]
    if pizza:
        index=unit['path'][-1]
        pizza=(unit.get('id')=='languages/en/XX_BLUE.HERO#["Yin_Pizza_Delivery","theNo",'+str(index)+']'
            and unit.get('source')==['The No','No'][index]
            and isinstance(disposition,dict)
            and disposition.get('consumerSourceSha256')=='21235ca242ec6854f23b53dd256c7f5491eb3621caf30049ea2a8c922e9c474a')
    if (not isinstance(disposition, dict) or unit.get('role') != 'visible' or not ('spanUtf16' in unit or pizza)
            or disposition.get('role') != 'preserve-exactly'
            or not isinstance(disposition.get('reason'), str) or not disposition['reason'].strip()
            or disposition.get('sourceValueSha256') != sha(unit['source'].encode())):
        raise ValueError('Technical disposition is not bound to the exact visible AST source')
    if entry['target'] != unit['source']:
        raise ValueError('Retained technical source value changed')
