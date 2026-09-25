"""Locate the master glyph buffer in EE RAM by matching real glyph pixels.

Input crib: the VRAM glyph-cache texture dumped by PCSX2 (256x512, 4bpp/PSMT4,
20x20 cells). We take one glyph's ink mask from it and look for the same mask in
EE RAM. Matching on "nibble != 0" avoids having to guess the CLUT order -- index
0 is transparent in this font, which is all the mask needs.

Unknown: how the master stores a glyph row (per-glyph linear = 10 bytes/row, or
as part of a wide atlas image = width/2 bytes/row). So seed the search with the
glyph's densest single row, then test candidate row strides against it.

Usage: python find_master.py <cache.png> <eeMemory.bin>
"""
import sys
import numpy as np
from PIL import Image

CACHE, EE = sys.argv[1], sys.argv[2]
CELL = 20

# ---- 1. rebuild 4bpp indices from the dumped texture -------------------------
im = Image.open(CACHE).convert('RGBA')
a = np.array(im)
H, W = a.shape[:2]
flat = a.reshape(-1, 4)
uniq = np.unique(flat, axis=0)
# order the palette: transparent first, then by (alpha, luma) -- an AA ramp
key = [(int(c[3]), int(c[:3].mean())) for c in uniq]
order = sorted(range(len(uniq)), key=lambda i: key[i])
pal = {tuple(uniq[i]): rank for rank, i in enumerate(order)}
idx = np.array([pal[tuple(p)] for p in flat], np.uint8).reshape(H, W)
print('palette entries: %d (index 0 = %s)' % (len(uniq), tuple(uniq[order[0]])))

# ---- 2. pick a dense glyph cell as the crib ---------------------------------
best = None
for r in range(H // CELL):
    for c in range(W // CELL):
        cell = idx[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL]
        ink = (cell != 0).sum()
        # want a busy, full-width glyph: lots of ink, and ink reaching both edges
        if ink > 150 and (cell[:, :2] != 0).any() and (cell[:, -2:] != 0).any():
            if best is None or ink > best[0]:
                best = (ink, r, c, cell.copy())
if best is None:
    raise SystemExit('no dense cell found')
ink, gr, gc, cell = best
print('crib cell: row=%d col=%d ink=%d/400' % (gr, gc, ink))
for row in (cell != 0):
    print('   ' + ''.join('#' if v else '.' for v in row))

mask = (cell != 0)                       # 20x20 bool, one bool per pixel=nibble

# ---- 3. nibble-level ink mask over all of EE RAM ----------------------------
ram = np.fromfile(EE, dtype=np.uint8)
lo = (ram & 0x0f) != 0
hi = (ram >> 4) != 0
nib = np.empty(ram.size * 2, bool)
nib[0::2] = lo                            # PSMT4: low nibble is the left pixel
nib[1::2] = hi
buf = nib.view(np.uint8).tobytes()        # 1 byte per nibble, 0 or 1
print('RAM nibbles: %d' % len(buf))

# ---- 4. seed on the densest row, then test strides --------------------------
rowink = mask.sum(axis=1)
seed = int(np.argmax(rowink))
seedpat = mask[seed].view(np.uint8).tobytes()
print('seed row %d (ink=%d): %s' % (seed, rowink[seed],
                                    ''.join('#' if v else '.' for v in mask[seed])))

hits = []
p = buf.find(seedpat)
while p != -1:
    hits.append(p)
    p = buf.find(seedpat, p + 1)
print('seed-row occurrences in RAM: %d' % len(hits))

STRIDES = [20, 40, 24, 32, 64, 128, 256, 512, 1024, 2048]   # nibbles per glyph row
found = []
for p in hits:
    for S in STRIDES:
        base = p - seed * S
        if base < 0 or base + 19 * S + CELL > len(buf):
            continue
        ok = True
        for r in range(CELL):
            o = base + r * S
            if buf[o:o + CELL] != mask[r].view(np.uint8).tobytes():
                ok = False
                break
        if ok:
            found.append((base, S))
            print('  MATCH  base_nibble=%#x  byte=%#x  row_stride=%d nibbles (%d B)'
                  % (base, base // 2, S, S // 2))

print('\n==== %d full-glyph match(es) ====' % len(found))
for base, S in found:
    print('  glyph at byte %#010x, row stride %d B -> %s'
          % (base // 2, S // 2,
             'per-glyph linear (200 B/glyph)' if S == 20 else 'atlas image %d px wide' % S))
