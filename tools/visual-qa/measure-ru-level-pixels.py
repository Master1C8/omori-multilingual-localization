"""Measure visible RU label/value gaps in the actual native1280x960 PNG.
Bands deliberately exclude separator rules. This is not an all-locale shaper test.
"""
import argparse,json
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('image');a=p.parse_args();im=Image.open(a.image).convert('RGB');assert im.size==(1280,960);rows=[]
for top in [140,428,716]:
 spans=[]
 for x in range(970,1180):
  if any(max(im.getpixel((x,y)))>50 for y in range(top,top+28)):
   if not spans or x>spans[-1][1]+1:spans.append([x,x])
   else:spans[-1][1]=x
 assert len(spans)>=2;gap=spans[-1][0]-spans[-2][1]-1;assert gap>=8,(top,spans,gap)
 rows.append({'band':[970,top,1180,top+28],'inkSpans':spans,'labelNumberVisibleGapPixels':gap})
print(json.dumps({'boundary':'Actual captured native pixels, separator rules excluded','rows':rows},indent=2))
