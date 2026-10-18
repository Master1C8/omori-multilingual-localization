"""Role-bound fallback faces; scale OpenType positioning with the outlines."""
import io
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen


def normalized_face(raw, base, codes, identity):
    font = TTFont(io.BytesIO(raw), recalcTimestamp=False)
    cmap = font.getBestCmap()
    if not set(codes) <= set(cmap):
        raise ValueError('Normalized font is missing requested glyphs')
    native = base.getGlyphSet()
    pen = BoundsPen(native)
    native[base.getBestCmap()[ord('A')]].draw(pen)
    target_cap = pen.bounds[3]
    donor = font.getGlyphSet()
    if ord('A') in cmap:
        pen = BoundsPen(donor)
        donor[cmap[ord('A')]].draw(pen)
        donor_cap = pen.bounds[3]
    else:
        donor_cap = getattr(font['OS/2'], 'sCapHeight', 0)
    if not donor_cap:
        raise ValueError('A measured or declared donor cap height is required')
    old_upem = font['head'].unitsPerEm
    intermediate_upem = round(old_upem * target_cap / donor_cap)
    if not 16 <= intermediate_upem <= 16384:
        raise ValueError('Invalid role-bound font scale')
    options = subset.Options()
    options.recalc_timestamp = False
    options.hinting = False
    selection = subset.Subsetter(options=options)
    selection.populate(unicodes=set(codes) | {32})
    selection.subset(font)
    if 'fvar' in font:
        axes = {a.axisTag: a.defaultValue for a in font['fvar'].axes}
        if 'wght' in axes:
            axes['wght'] = 400
        font = instantiateVariableFont(font, axes, inplace=True)
    # This visitor also scales GPOS anchors/advances and related positioning.
    # Scaling only glyf/hmtx would break Thai, Arabic and Devanagari marks.
    scale_upem(font, intermediate_upem)
    font['head'].unitsPerEm = base['head'].unitsPerEm
    for field in ('ascent', 'descent', 'lineGap'):
        setattr(font['hhea'], field, getattr(base['hhea'], field))
    for field in ('sTypoAscender', 'sTypoDescender', 'sTypoLineGap',
                  'usWinAscent', 'usWinDescent'):
        setattr(font['OS/2'], field, getattr(base['OS/2'], field))
    font['OS/2'].fsType = 0
    for nid, text in ((1, identity), (2, 'Regular'), (3, identity + ' 2026-10-17'),
                      (4, identity), (6, identity.replace(' ', '')),
                      (16, identity), (17, 'Regular')):
        font['name'].removeNames(nameID=nid)
        font['name'].setName(text, nid, 3, 1, 0x409)
        font['name'].setName(text, nid, 1, 0, 0)
    font['head'].created = font['head'].modified = 3406620153
    font.recalcTimestamp = False
    out = io.BytesIO()
    font.save(out)
    result = out.getvalue()
    reopened = TTFont(io.BytesIO(result), recalcTimestamp=False)
    if not set(codes) <= set(reopened.getBestCmap()):
        raise ValueError('Normalized cmap readback mismatch')
    space = reopened.getBestCmap().get(32)
    if not space or reopened['hmtx'][space][0] <= 0:
        raise ValueError('Normalized font has invalid space advance')
    proof = {'sourceUnitsPerEm': old_upem, 'unitsPerEm': reopened['head'].unitsPerEm,
             'sourceCapHeight': donor_cap, 'targetCapHeight': target_cap,
             'outlineAndPositioningScale': intermediate_upem / old_upem,
             'ascender': reopened['hhea'].ascent, 'descender': reopened['hhea'].descent,
             'spaceAdvance': reopened['hmtx'][space][0],
             'variableAxes': 'instantiated-defaults-regular400',
             'boundary': 'OpenType outlines and positioning scaled together; runtime readability pending'}
    reopened.close()
    font.close()
    return result, proof
