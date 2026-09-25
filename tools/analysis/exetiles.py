import sys
import numpy as np
from PIL import Image, ImageDraw
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
print("exe size", len(exe))
def tile_render(d, gw, gh, cols, rows, x0):
    rb=(gw+7)//8; gsz=rb*gh
    arr=np.zeros((rows*gh, cols*gw),np.uint8)
    for gi in range(cols*rows):
        gd=d[x0+gi*gsz : x0+(gi+1)*gsz]
        if len(gd)<gsz: break
        bits=np.unpackbits(np.frombuffer(gd,np.uint8)).reshape(gh,rb*8)[:,:gw]
        r,c=divmod(gi,cols); arr[r*gh:(r+1)*gh,c*gw:(c+1)*gw]=bits*255
    return Image.fromarray(arr,"L")
# render whole exe as 16x16 tiles, 96 cols, in vertical strips downscaled
gw=gh=16; cols=96; gsz=(gw//8)*gh  # 32
per_img_rows=120
total_glyphs=len(exe)//gsz
strips=[]
off=0; idx=0
while off < len(exe):
    img=tile_render(exe, gw, gh, cols, per_img_rows, off)
    strips.append((off,img)); off+=cols*per_img_rows*gsz; idx+=1
    if idx>=8: break
# stack first 8 strips side by side, downscaled
thumbs=[im.resize((cols*4, per_img_rows*4)) for _,im in strips]
tw,th=thumbs[0].size
mont=Image.new("L",(len(thumbs)*(tw+6), th+16),200)
for k,(off,_) in enumerate(strips):
    mont.paste(thumbs[k],(k*(tw+6),16))
    ImageDraw.Draw(mont).text((k*(tw+6)+2,2),f"0x{off:x}",fill=0)
mont.save(OUT+"/exe_overview.png")
print("saved exe overview, strips cover to", hex(off))
