"""Find the master glyph atlas inside a PCSX2 EE RAM dump.

Address model: the PS2 ELF is a single LOAD segment and EE main RAM is flat at
physical 0, so program VA == byte offset into eeMemory.bin. Verified below by
matching the known SJIS->slot table.

Scan method (fast, whole-RAM):
  For a candidate cell stride P and row-bytes rb, build A[j] = "the rb bytes at j
  are all zero". A real CJK atlas has a blank first row in nearly every cell, so
  for the correct phase the strided series A[o::P] is almost all True across the
  3773 cells. A rolling window over that series localises the atlas in one pass
  per phase -- O(len(RAM)) per geometry instead of testing every offset.

  Blank-row alone rewards all-zero memory, so every peak is then re-checked with
  the full test (ink present, cells distinct) before being reported.
"""
import struct
import sys

import numpy as np

G = 3773          # exact glyph count, from the SJIS->slot table
EE = sys.argv[1]
ELF = sys.argv[2] if len(sys.argv) > 2 else None

GEOM = [
    ('1bpp 20x20 packed',   50,  2, 1),
    ('1bpp 20x20 rowalign', 60,  3, 1),
    ('1bpp 20x20 pad4',     80,  4, 1),
    ('1bpp 24x24',          72,  3, 1),
    ('1bpp 32x32',         128,  4, 1),
    ('2bpp 20x20',         100,  5, 2),
    ('2bpp 24x20',         120,  6, 2),
    ('4bpp 20x20',         200, 10, 4),
    ('4bpp 24x20',         240, 12, 4),
    ('4bpp 24x24',         288, 12, 4),
    ('4bpp 32x20',         320, 16, 4),
    ('8bpp 20x20',         400, 20, 8),
    ('8bpp 24x20',         480, 24, 8),
    ('8bpp 32x20',         640, 32, 8),
    ('8bpp 24x24',         576, 24, 8),
]

ram = np.fromfile(EE, dtype=np.uint8)
print('EE RAM: %d B' % ram.size)

# ---- validate the address model against the known table ----
if ELF:
    elf = open(ELF, 'rb').read()
    a = ram[0x5388E0:0x5388E0 + 0x100].tobytes()
    b = elf[0x4389E0:0x4389E0 + 0x100]
    print('address model: RAM[0x5388E0] %s ELF[0x4389E0]'
          % ('== MATCHES' if a == b else '!= DIFFERS'))

z = (ram == 0)


def rolling_all_zero(rb):
    """A[j] = all(ram[j:j+rb] == 0)"""
    a = z.copy()
    for k in range(1, rb):
        a[:a.size - k] &= z[k:]
    return a


def full_check(off, per, rb, bpp):
    if off + G * per > ram.size:
        return None
    a = ram[off:off + G * per].reshape(G, per)
    nz = a != 0
    blank = 1.0 - nz.any(axis=1).mean()
    if blank > 0.05:
        return None
    top = ~nz[:, :rb].any(axis=1)
    bot = ~nz[:, -rb:].any(axis=1)
    margin = float((top & bot).mean())
    if margin < 0.60:
        return None
    ink = float(np.unpackbits(a, axis=1).mean()) if bpp == 1 else float(nz.mean())
    band = (0.06, 0.50) if bpp == 1 else (0.08, 0.75)
    if not (band[0] <= ink <= band[1]):
        return None
    raw = a.tobytes()
    uniq = len({raw[i * per:(i + 1) * per] for i in range(G)}) / G
    if uniq < 0.80:
        return None
    return dict(margin=round(margin, 3), blank=round(float(blank), 4),
                ink=round(ink, 3), uniq=round(uniq, 3))


hits = []
for name, per, rb, bpp in GEOM:
    A = rolling_all_zero(rb)
    found = 0
    for phase in range(per):
        s = A[phase::per].astype(np.int32)
        if s.size < G + 1:
            continue
        c = np.concatenate(([0], np.cumsum(s)))
        win = (c[G:] - c[:-G]) / G          # win[k] = blank-row frac for cells starting at k
        cand = np.nonzero(win >= 0.70)[0]
        for k in cand:
            off = phase + int(k) * per
            r = full_check(off, per, rb, bpp)
            if r:
                hits.append((name, per, rb, bpp, off, r))
                print('  HIT %-20s per=%3d off=%#010x  %s' % (name, per, off, r), flush=True)
                found += 1
                if found > 8:
                    break
        if found > 8:
            break
    print('scanned %-20s (%d phases)' % (name, per), flush=True)

print('\n==== %d hit(s) ====' % len(hits))
for name, per, rb, bpp, off, r in hits:
    print('  %-20s per=%3d rb=%2d off=%#010x  %s' % (name, per, rb, off, r))
