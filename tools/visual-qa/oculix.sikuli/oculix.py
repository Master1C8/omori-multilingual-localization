# Oculix/Jython, adapted from the canonical Stardew visual-QA runner.
# Do not import sikuli.Screen: its Java mouse self-test fails on this host.
# Use the canonical native-capture + fresh BufferedImage Finder architecture.
from org.sikuli.script import Finder, Pattern
import sys, os, json, subprocess
from java.io import File
from javax.imageio import ImageIO

root = sys.argv[1]
path = os.path.join(root, 'native-finder-smoke-v2.png')
if os.path.exists(path): raise RuntimeError('Preserve existing smoke evidence')
subprocess.check_call(['/usr/sbin/screencapture', '-x', path])
normalized = os.path.join(root, 'native-finder-smoke-v2-rgb.png')
subprocess.check_call(['/opt/homebrew/bin/magick', path, '-alpha', 'off', '-depth', '8', 'PNG24:' + normalized])
frame = ImageIO.read(File(normalized))
template = frame.getSubimage(100, 100, 150, 100)
finder = Finder(frame)
try:
    finder.find(Pattern(template).similar(0.99))
    if not finder.hasNext(): raise RuntimeError('Native BufferedImage recognition failed')
    print('OCULIX_MATCH ' + str(finder.next()))
finally:
    finder.destroy()
print('NATIVE_DIMENSIONS %sx%s' % (frame.getWidth(), frame.getHeight()))
print('OCULIX_SMOKE_PASS')
