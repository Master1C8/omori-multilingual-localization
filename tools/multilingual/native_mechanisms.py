"""Source-bound native05 geometry repairs, parameterized by authored catalog text."""
import gzip
from pathlib import Path
from source_prepare import sha


def once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Native source anchor missing or ambiguous')
    return source.replace(before, after, 1)


def ui_sources(root):
    base = root / 'source/inventory-8879120-01/original/js/plugins'
    save = gzip.decompress((base / 'Omori Save & Load.OMORI.gz').read_bytes()).decode()
    title = gzip.decompress((base / 'Omori Title Screen.OMORI.gz').read_bytes()).decode()
    anchor = 'Window_OmoriFileCommand.prototype.customCursorRectTextXOffset = function() { return 40; }'
    fixed_save = once(save, anchor, anchor + '\r\n' +
        'Window_OmoriFileCommand.prototype.customCursorRectTextWidthOffset = function() { return -this.customCursorRectTextXOffset(); };')
    hint = '  this._commandHints.bitmap.drawInputIcon("ok", 0, paddingY);'
    layout = '''  let confirmPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_confirm_position;
  let cancelPosition = LanguageManager.getMessageData("XX_BLUE.Scene_OmoriTitleScreen").commandHints_cancel_position;
  let confirmWidth = this._commandHints.bitmap.measureTextWidth(confirm);
  let cancelWidth = this._commandHints.bitmap.measureTextWidth(cancel);
  let hintWidth = Math.ceil(Math.max(eval(confirmPosition[0]) + confirmWidth,
    eval(cancelPosition[0]) + cancelWidth, iconSize + 15 + confirmWidth + iconSize) + 4);
  this._commandHints.bitmap.resize(hintWidth, this._commandHints.bitmap.height);
  this._commandHints.setFrame(0, 0, hintWidth, this._commandHints.bitmap.height);
  this._commandHints.position.set(Graphics.boxWidth - hintWidth, 0);
'''
    return {'save': {'original': save, 'fixed': fixed_save, 'originalSha256': sha(save.encode())},
            'title': {'original': title, 'fixed': once(title, hint, layout + hint), 'originalSha256': sha(title.encode())}}
