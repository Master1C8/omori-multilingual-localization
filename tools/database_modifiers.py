"""Verify typed stat/amount/sign relations in authored database descriptions."""
import re

STAT_NAMES = {
    'HEART': 'HEART', 'СЕРДЦА': 'HEART',
    'JUICE': 'JUICE', 'СОК': 'JUICE',
    'ATK': 'ATTACK', 'ATTACK': 'ATTACK', 'АТАКА': 'ATTACK',
    'DEF': 'DEFENSE', 'DEFENSE': 'DEFENSE', 'ЗАЩИТА': 'DEFENSE',
    'SPD': 'SPEED', 'SPEED': 'SPEED', 'СКОРОСТЬ': 'SPEED',
    'LUCK': 'LUCK', 'УДАЧА': 'LUCK',
    'ALL STATS': 'ALL', 'ВСЕ ХАРАКТЕРИСТИКИ': 'ALL',
}
MODIFIER = re.compile(r'(?<![\w])(' + '|'.join(re.escape(k) for k in sorted(STAT_NAMES, key=len, reverse=True))
                      + r')\s*([+-])\s*(\d+(?:[.,]\d+)?)(%?)', re.I)
DATABASES = {'data/Armors.KEL', 'data/Weapons.KEL', 'data/Items.KEL', 'data/Skills.KEL', 'data/States.KEL'}


def modifiers(value):
    return [(STAT_NAMES[m.group(1).upper()], m.group(2), m.group(3), m.group(4))
            for m in MODIFIER.finditer(value)]


def validate_description_modifiers(unit, target):
    if (unit['asset'] in DATABASES and unit.get('path', [None])[-1] == 'description'
            and not any(k in unit for k in ('span', 'spanCodepoints', 'spanUtf16'))):
        if modifiers(unit['source']) != modifiers(target):
            raise ValueError('Database stat/amount/sign relation changed: ' + unit['id'])
