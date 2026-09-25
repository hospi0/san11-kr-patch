"""Measure the master atlas pitch and base without guessing.

Every glyph in the VRAM cache also exists in the master buffer. Find a batch of
them in EE RAM by exact ink-mask match, then: if glyphs sit at base + slot*pitch,
every pairwise address difference is a multiple of pitch, so gcd(diffs) == pitch
(up to a common factor). No need to identify which character each cell is.

Usage: python pitch_gcd.py <cache.png> <eeMemory.bin> [max_cells]
"""
import sys
from math import gcd
from functools import reduce

import numpy as np
from PIL import Image

CACHE, EE = sys.argv[1], sys.argv[2]
MAXC = int(sys.argv[3]) if len(sys.argv) > 3 else 40
CELL = 20

im = Image.open(CACHE).convert('RGBA')
a = np.array(im)
H, W = a.shape[:2]
flat = a.reshape(-1, 4)
uniq = np.unique(flat, axis=0)
key = [(int(c[3]), int(c[:3].mean())) for c in uniq]
order = sorted(range(len(uniq)), key=lambda i: key[i])
pal = {tuple(uniq[i]): rank for rank, i in enumerate(order)}
idx = np.array([pal[tuple(p)] for p in flat], np.uint8).reshape(H, W)

ram = np.fromfile(EE, dtype=np.uint8)
nib = np.empty(ram.size * 2, bool)
nib[0::2] = (ram & 0x0f) != 0
nib[1::2] = (ram >> 4) != 0
buf = nib.view(np.uint8).tobytes()

found = []
for r in range(H // CELL):
    for c in range(W // CELL):
        if len(found) >= MAXC:
            break
        cell = idx[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL]
        mask = cell != 0
        if mask.sum() < 120:                      # need a busy glyph to be unique
            continue
        if not (mask[:, :2].any() and mask[:, -2:].any()):
            continue                              # want full-width, not half
        rowink = mask.sum(axis=1)
        seed = int(np.argmax(rowink))
        pat = mask[seed].view(np.uint8).tobytes()
        # collect candidate positions for the seed row, then verify all 20 rows
        hit = None
        p = buf.find(pat)
        while p != -1:
            base = p - seed * CELL
            if base >= 0 and base + 20 * CELL <= len(buf):
                ok = all(buf[base + i * CELL: base + i * CELL + CELL]
                         == mask[i].view(np.uint8).tobytes() for i in range(CELL))
                if ok:
                    if hit is not None and hit != base:
                        hit = -1                  # ambiguous, skip this glyph
                        break
                    hit = base
            p = buf.find(pat, p + 1)
        if hit is not None and hit != -1:
            found.append((r, c, hit // 2))
            print('  cell(%2d,%2d) ink=%3d -> RAM %#010x' % (r, c, mask.sum(), hit // 2))

print('\nunique glyph locations: %d' % len(found))
if len(found) < 2:
    raise SystemExit('not enough')

addrs = sorted(a for _, _, a in found)
print('addr range: %#x .. %#x  (span %d B)' % (addrs[0], addrs[-1], addrs[-1] - addrs[0]))
diffs = [addrs[i + 1] - addrs[i] for i in range(len(addrs) - 1)]
print('consecutive diffs:', diffs)
g = reduce(gcd, diffs)
print('\ngcd of consecutive diffs = %d' % g)
allg = reduce(gcd, [addrs[i] - addrs[0] for i in range(1, len(addrs))])
print('gcd of diffs from first  = %d' % allg)
if allg:
    print('=> pitch is %d B/glyph  (=%d rows of 10 B)' % (allg, allg // 10)
          if allg % 10 == 0 else '=> pitch %d B (not a multiple of 10!)' % allg)
    print('=> base candidates: %#x mod %d' % (addrs[0] % allg, allg))
