import struct, sys
from PIL import Image
OUT=sys.argv[1]
f=open("s11pkres.bin","rb")
f.seek(4); n=struct.unpack("<I",f.read(4))[0]
f.seek(0x10); tbl=[struct.unpack("<II",f.read(8)) for _ in range(n)]
def get(i):
    a,b=tbl[i]; f.seek(a*0x800); return f.read(b)

d=get(675)
print("idx675 GCOL size",len(d),"head",d[:16].hex())
body=d  # include header; we'll offset

def render_1bpp(data, width_px, height_px, x0=0, invert=False):
    rowbytes=(width_px+7)//8
    img=Image.new("L",(width_px,height_px),0)
    px=img.load()
    for y in range(height_px):
        for xb in range(rowbytes):
            off=x0+y*rowbytes+xb
            if off>=len(data): break
            byte=data[off]
            for bit in range(8):
                x=xb*8+bit
                if x<width_px:
                    v=(byte>>(7-bit))&1
                    if invert: v^=1
                    px[x,y]=255*v
    return img

# render as a wide 1bpp sheet, width 512, from several start offsets
for x0 in [0, 0x10, 0x20, 0x40]:
    img=render_1bpp(body, 512, 512, x0)
    img.save(f"{OUT}/gcol675_1bpp_w512_x{x0:x}.png")
print("saved 1bpp sheets")

# also render idx=88 big entry as 4bpp/8bpp thumbnail to identify
d88=get(88)
def render_8bpp(data, w, h, x0=0):
    img=Image.new("L",(w,h),0); px=img.load()
    for y in range(h):
        for x in range(w):
            off=x0+y*w+x
            px[x,y]=data[off] if off<len(data) else 0
    return img
render_8bpp(d88, 1024, 1024, 0x40).save(f"{OUT}/idx88_8bpp_1024.png")
print("saved idx88")
