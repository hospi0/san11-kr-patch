import sys
import numpy as np
from PIL import Image, ImageDraw
OUT=sys.argv[1]
exe=open("SLPM_667.01","rb").read()
def tile_render(d, gw, gh, cols, rows, x0):
    rb=(gw+7)//8; gsz=rb*gh
    arr=np.zeros((rows*gh, cols*gw),np.uint8)
    for gi in range(cols*rows):
        gd=d[x0+gi*gsz : x0+(gi+1)*gsz]
        if len(gd)<gsz: break
        bits=np.unpackbits(np.frombuffer(gd,np.uint8)).reshape(gh,rb*8)[:,:gw]
        r,c=divmod(gi,cols); arr[r*gh:(r+1)*gh,c*gw:(c+1)*gw]=bits*255
    return Image.fromarray(arr,"L")
# data segment 0x2a0000 .. end, render 24x24 tiles 48 cols, in strips
gw=gh=24; cols=48; gsz=(gw//8)*gh  # 72
start=0x2a0000
region=exe[start:]
per=100
strips=[]
off=0; k=0
while off<len(region) and k<10:
    strips.append((start+off, tile_render(region, gw, gh, cols, per, off)))
    off+=cols*per*gsz; k+=1
thumbs=[im for _,im in strips]
tw,th=thumbs[0].size
mont=Image.new("L",(len(thumbs)*(tw+6), th+16),200)
for k,(o,_) in enumerate(strips):
    mont.paste(thumbs[k],(k*(tw+6),16))
    ImageDraw.Draw(mont).text((k*(tw+6)+2,2),f"0x{o:x}",fill=0)
mont.save(OUT+"/exe_data.png")
print("saved, covered", hex(start+off))
