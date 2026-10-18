"""Generate exact Unicode16 joining ranges; never author or alter game wording."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/font-reference/Unicode16-DerivedJoiningType.txt'
LICENSE=ROOT/'source/font-reference/Unicode-LICENSE-v19.txt'
DEST=ROOT/'tools/multilingual/delivery/arabic_joining.js'
raw=SOURCE.read_bytes();license_raw=LICENSE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6bd08b97da66b70ccfdab105a352de2984e02625239ec5695422c99b33d854f0'
assert hashlib.sha256(license_raw).hexdigest()=='e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96'
ranges=[]
for line in raw.decode().splitlines():
    match=re.match(r'^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*;\s*([DRLCT])\b',line)
    if match:ranges.append([int(match[1],16),int(match[2] or match[1],16),match[3]])
ranges.sort()
assert all(a[1]<b[0] for a,b in zip(ranges,ranges[1:]))
source='/* Unicode16 DerivedJoiningType; source SHA256 '+hashlib.sha256(raw).hexdigest()+'\n'+'\n'.join(raw.decode().splitlines()[:8])+'\n'+license_raw.decode().replace('*/','* /')+'\n*/\n'
source+="(function(root){'use strict';var ranges="+json.dumps(ranges,separators=(',',':'))+";\n"
source+="function type(character){if(!character)return 'U';var code=character.codePointAt(0),lo=0,hi=ranges.length-1;while(lo<=hi){var mid=(lo+hi)>>1,row=ranges[mid];if(code<row[0])hi=mid-1;else if(code>row[1])lo=mid+1;else return row[2];}return 'U';}\n"
source+="var api={type:type,ranges:ranges,version:'16.0.0'};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OmoriArabicJoining=api;}(typeof globalThis!=='undefined'?globalThis:this));\n"
if '--check' in sys.argv:
    assert DEST.read_text()==source,'Generated Unicode joining table differs'
else:DEST.write_text(source)
print(json.dumps({'status':'checked' if '--check' in sys.argv else 'generated','ranges':len(ranges),'unicodeVersion':'16.0.0'}))
