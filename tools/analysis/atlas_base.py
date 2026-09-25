"""Pin down the master atlas base address in EE RAM using shape cribs.

We know one glyph sits at byte 0xbab830 and glyphs are 200 B each (4bpp 20x20,
10 B/row), stored back to back in slot order. So the atlas base B satisfies
B = 0xbab830 - k*200 for some slot k in [0, 3772] -- 3773 candidates.

Cribs (from the SJIS->slot table): slot 407 = 一 (one horizontal bar), slot 1381
= 三 (three bars), slot 2491 = 日. Only the true base makes all of these look
right, so score each candidate on "number of horizontal ink bands".
"""
import sys
import numpy as np

EE = sys.argv[1]
KNOWN = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xbab830
PER, W, H, RB = 200, 20, 20, 10
G = 3773

ram = np.fromfile(EE, dtype=np.uint8)


def glyph(base, slot):
    o = base + slot * PER
    if o < 0 or o + PER > ram.size:
        return None
    b = ram[o:o + PER].reshape(H, RB)
    lo = b & 0x0f
    hi = b >> 4
    px = np.empty((H, W), np.uint8)
    px[:, 0::2] = lo
    px[:, 1::2] = hi
    return px


def bands(px):
    """count contiguous groups of rows that carry ink"""
    r = (px != 0).any(axis=1)
    n, prev = 0, False
    for v in r:
        if v and not prev:
            n += 1
        prev = v
    return n, int(r.sum())


def score(base):
    g1 = glyph(base, 407)     # 一 : exactly 1 band, thin
    g3 = glyph(base, 1381)    # 三 : exactly 3 bands
    if g1 is None or g3 is None:
        return -1
    b1, h1 = bands(g1)
    b3, h3 = bands(g3)
    s = 0
    if b1 == 1 and 2 <= h1 <= 7:
        s += 2
    if b3 == 3 and 6 <= h3 <= 14:
        s += 3
    # 一 should be wide: ink spanning most columns on its band
    if b1 == 1 and (g1 != 0).any(axis=0).sum() >= 14:
        s += 1
    return s


cands = []
for k in range(G):
    base = KNOWN - k * PER
    if base < 0:
        break
    s = score(base)
    if s >= 4:
        cands.append((s, base, k))

cands.sort(reverse=True)
print('candidates scoring >=4: %d' % len(cands))
for s, base, k in cands[:8]:
    print('\n=== score=%d  base=%#010x  (the known glyph is slot %d) ===' % (s, base, k))
    for name, slot in (('407 ichi', 407), ('1381 san', 1381), ('2491 nichi', 2491), ('61 zero', 61)):
        px = glyph(base, slot)
        print('  -- slot %s' % name)
        for row in px:
            print('     ' + ''.join(' .:-=+*#%@'[min(9, v)] if v else '.' for v in row))
