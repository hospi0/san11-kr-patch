# -*- coding: utf-8 -*-
"""가이지 111자(슬롯 3773~3883, SJIS 0xf040~0xf162) 글리프를 격자 PNG로 렌더.

아틀라스: s11pkres.bin 엔트리 idx=2, 4bpp 20x20, 행당 10B, 피치 224B/글리프.
저니블 = 왼쪽 픽셀, 인덱스0 = 투명, 1~15 = AA 램프.

컨트롤 크립(slot 407=一, 1258=国, 1381=三, 2491=日)을 함께 렌더해
렌더 경로 자체가 옳은지 먼저 확인한다.
"""
import struct, sys
from PIL import Image, ImageDraw

RES = "s11pkres.bin"
ENTRY_OFF = 0x49810      # 엔트리 idx=2 시작
PITCH = 224
W = H = 20

# 크립: (슬롯, 기대문자)
CRIBS = [(407, "一"), (1258, "国"), (1381, "三"), (2491, "日"), (61, "０")]


def load_glyph(data, base, slot):
    """4bpp 20x20 글리프 → 0..15 픽셀 2차원 리스트."""
    off = base + slot * PITCH
    px = []
    for y in range(H):
        row = data[off + y * 10: off + y * 10 + 10]
        line = []
        for b in row:
            line.append(b & 0x0F)        # 저니블 = 왼쪽
            line.append((b >> 4) & 0x0F)
        px.append(line)
    return px


def to_img(px, scale):
    im = Image.new("L", (W * scale, H * scale), 255)
    d = im.load()
    for y in range(H):
        for x in range(W):
            v = 255 - px[y][x] * 17      # 0=흰 배경, 15=검정 잉크
            for dy in range(scale):
                for dx in range(scale):
                    d[x * scale + dx, y * scale + dy] = v
    return im


def main():
    atlas_delta = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x10
    out = sys.argv[2] if len(sys.argv) > 2 else "work/gaiji_grid.png"
    data = open(RES, "rb").read()
    base = ENTRY_OFF + atlas_delta

    scale = 4
    cell_w, cell_h = W * scale, H * scale + 14
    cols = 12

    items = [("crib " + ch, s) for s, ch in CRIBS]
    items += [("%04x" % (0xf040 + 0), 3773)]  # placeholder replaced below
    items.pop()
    # 가이지: 슬롯 3773..3883 ↔ SJIS 코드 순차 매핑을 테이블에서 역산
    slp = open("SLPM_667.01", "rb").read()
    BASE = 0x4389E0

    def idx(c):
        if 0x8100 <= c <= 0x9fff: return c - 0x8100
        if 0xe000 <= c <= 0xeaff: return c - 0xC100
        if 0xed00 <= c <= 0xeeff: return c - 0xC300
        return c - 0xC400

    for c in range(0xf040, 0xf163):
        lo = c & 0xff
        if lo < 0x40 or lo == 0x7f or lo > 0xfc:
            continue
        off = BASE + idx(c) * 2
        v = struct.unpack("<H", slp[off:off + 2])[0]
        if v == 0xffff:
            continue
        items.append(("%04x" % c, v))

    rows = (len(items) + cols - 1) // cols
    img = Image.new("L", (cols * cell_w, rows * cell_h), 255)
    dr = ImageDraw.Draw(img)
    for n, (label, slot) in enumerate(items):
        r, c = divmod(n, cols)
        g = to_img(load_glyph(data, base, slot), scale)
        img.paste(g, (c * cell_w, r * cell_h))
        dr.text((c * cell_w + 2, r * cell_h + H * scale + 1), label, fill=0)
    img.save(out)
    print("%s 저장: %d칸 (크립 %d + 가이지 %d), atlas base=0x%x"
          % (out, len(items), len(CRIBS), len(items) - len(CRIBS), base))


main()
