# -*- coding: utf-8 -*-
"""가이지 비정 검증: 게임 글리프 ⟷ 비정 한자(시스템 폰트)를 나란히 렌더.

왼쪽 = s11pkres 아틀라스의 실제 글리프, 오른쪽 = GAIJI_MAP이 주장하는 한자.
둘이 같아 보이면 비정이 맞다. 눈으로 대조하기 위한 도구.
"""
import struct, sys
from PIL import Image, ImageDraw, ImageFont

RES = "s11pkres.bin"
ATLAS = 0x49810
PITCH = 224
W = H = 20

sys.path.insert(0, r"C:\claude\project\san11-kr-patch\tools")
from gaiji_map import GAIJI_MAP  # noqa: E402


def load_glyph(data, slot):
    off = ATLAS + slot * PITCH
    px = []
    for y in range(H):
        row = data[off + y * 10: off + y * 10 + 10]
        line = []
        for b in row:
            line.append(b & 0x0F)
            line.append((b >> 4) & 0x0F)
        px.append(line)
    return px


def glyph_img(px, scale):
    im = Image.new("L", (W * scale, H * scale), 255)
    d = im.load()
    for y in range(H):
        for x in range(W):
            v = 255 - px[y][x] * 17
            for dy in range(scale):
                for dx in range(scale):
                    d[x * scale + dx, y * scale + dy] = v
    return im


def main():
    data = open(RES, "rb").read()
    slp = open("SLPM_667.01", "rb").read()
    BASE = 0x4389E0

    def idx(c):
        if 0x8100 <= c <= 0x9fff: return c - 0x8100
        if 0xe000 <= c <= 0xeaff: return c - 0xC100
        if 0xed00 <= c <= 0xeeff: return c - 0xC300
        return c - 0xC400

    def slot_of(c):
        v = struct.unpack("<H", slp[BASE + idx(c) * 2: BASE + idx(c) * 2 + 2])[0]
        return None if v == 0xffff else v

    scale = 5
    gw = W * scale                      # 100
    cell_w, cell_h = gw * 2 + 12, gw + 16
    cols = 6
    items = sorted(GAIJI_MAP.items())
    rows = (len(items) + cols - 1) // cols

    kfont = ImageFont.truetype(r"C:\Windows\Fonts\batang.ttc", gw - 8)
    lfont = ImageFont.load_default()

    img = Image.new("L", (cols * cell_w, rows * cell_h), 255)
    dr = ImageDraw.Draw(img)
    for n, (code, ch) in enumerate(items):
        r, c = divmod(n, cols)
        x0, y0 = c * cell_w, r * cell_h
        s = slot_of(code)
        if s is None:
            dr.text((x0 + 2, y0 + 2), "%04x NO SLOT" % code, fill=0)
            continue
        img.paste(glyph_img(load_glyph(data, s), scale), (x0, y0))
        dr.text((x0 + gw + 6, y0), ch, font=kfont, fill=0)
        dr.line([(x0 + gw + 3, y0), (x0 + gw + 3, y0 + gw)], fill=160)
        dr.text((x0 + 2, y0 + gw + 2), "%04x s%d" % (code, s), font=lfont, fill=0)
    out = r"C:\claude\project\san11-kr-patch\work\gaiji_verify.png"
    img.save(out)
    print("%s 저장: %d쌍 (왼쪽=게임글리프, 오른쪽=비정한자)" % (out, len(items)))


main()
