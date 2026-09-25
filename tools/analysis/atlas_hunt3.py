"""Font-atlas hunt, v3 — drops the unsafe slot0-blank assumption.

Why v2 was still holed: the renderer special-cases SJIS 0x8140 (ideographic
space), so slot 0's cell is never fetched and need NOT be blank. v2 used
"slot0 blank" as a cheap precheck and would have rejected a real atlas.

v3 relies only on properties a CJK atlas must have regardless:
  - <5% of cells entirely blank (a real font is nearly all inked)
  - >=70% of cells have blank first AND last row (vertical margin)
  - ink density in a plausible band
  - additionally: reject degenerate periodic junk by requiring the cells to be
    DISTINCT (a real font has ~no duplicate glyphs; noise repeats).
"""
import struct, sys
import numpy as np

G = 3773
PRE = 400  # cells used for the cheap prefilter

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
HEADERS = [0, 0x08, 0x10, 0x20, 0x30, 0x40, 0x60, 0x80, 0xc0, 0x100, 0x200, 0x400, 0x800, 0x1000]


def check(a, rb, bpp, want_distinct):
    """a: (n, per) uint8"""
    nz = a != 0
    has_ink = nz.any(axis=1)
    blank = 1.0 - has_ink.mean()
    if blank > 0.05:
        return None
    top = ~nz[:, :rb].any(axis=1)
    bot = ~nz[:, -rb:].any(axis=1)
    margin = float((top & bot).mean())
    if margin < 0.70:
        return None
    if bpp == 1:
        ink = float(np.unpackbits(a, axis=1).mean())
        band = (0.08, 0.45)
    else:
        ink = float(nz.mean())
        band = (0.10, 0.70)
    if not (band[0] <= ink <= band[1]):
        return None
    if want_distinct:
        # a real font has almost no duplicate cells; periodic noise is nearly all dupes
        uniq = len(set(a.tobytes()[i * a.shape[1]:(i + 1) * a.shape[1]] for i in range(a.shape[0])))
        frac_uniq = uniq / a.shape[0]
        if frac_uniq < 0.80:
            return None
        return dict(margin=margin, blank=float(blank), ink=ink, uniq=frac_uniq)
    return dict(margin=margin, blank=float(blank), ink=ink)


def hunt(label, buf, out):
    for gname, per, rb, bpp in GEOM:
        need = G * per
        if len(buf) < need:
            continue
        for hdr in HEADERS:
            if hdr + need > len(buf):
                continue
            pre = np.frombuffer(buf[hdr:hdr + PRE * per], np.uint8).reshape(PRE, per)
            if check(pre, rb, bpp, False) is None:
                continue
            full = np.frombuffer(buf[hdr:hdr + G * per], np.uint8).reshape(G, per)
            r = check(full, rb, bpp, True)
            if r:
                out.append((r['margin'], label, gname, per, hdr, r))
                print('  HIT %-14s %-20s per=%d hdr=%#x %s' % (label, gname, per, hdr, r), flush=True)


def main():
    res = []
    for fn in ('SLPM_667.01', 'Overlay1.bin', 'Overlay2.bin'):
        buf = open(fn, 'rb').read()
        if fn == 'SLPM_667.01':
            # atlas could sit anywhere in the ELF: slide a window
            for base in range(0, len(buf) - G * 50, 0x400):
                hunt('%s@%#x' % (fn, base), buf[base:base + G * 640 + 0x2000], res)
        else:
            hunt(fn, buf, res)
        print('scanned', fn, flush=True)

    f = open('s11pkres.bin', 'rb')
    f.seek(4)
    n = struct.unpack('<I', f.read(4))[0]
    f.seek(0x10)
    tbl = [struct.unpack('<II', f.read(8)) for _ in range(n)]
    ents = [('idx%d' % i, a * 0x800, b) for i, (a, b) in enumerate(tbl)]
    for i, (a, b) in enumerate(tbl):
        if b < 0x10:
            continue
        f.seek(a * 0x800)
        h = f.read(0x10)
        if h[:4] != b'LINK':
            continue
        cnt = struct.unpack('<I', h[4:8])[0]
        if not (0 < cnt <= 20000):
            continue
        f.seek(a * 0x800 + 0x10)
        sub = f.read(cnt * 8)
        if len(sub) < cnt * 8:
            continue
        for j in range(cnt):
            sa, sb = struct.unpack('<II', sub[j * 8:j * 8 + 8])
            if sb:
                ents.append(('idx%d/%d' % (i, j), a * 0x800 + sa * 0x800, sb))

    big = [e for e in ents if e[2] >= G * 50]
    print('archive candidates:', len(big), flush=True)
    for k, (lbl, off, sz) in enumerate(big):
        f.seek(off)
        hunt(lbl, f.read(min(sz, G * 640 + 0x2000)), res)
        if k % 300 == 0:
            print('  ..%d/%d' % (k, len(big)), flush=True)

    print('\n==== SURVIVORS (%d) ====' % len(res))
    for m, lbl, gname, per, hdr, r in sorted(res, key=lambda x: -x[0])[:25]:
        print('  %-22s %-20s per=%3d hdr=%#06x  %s' % (lbl, gname, per, hdr, r))
    if not res:
        print('  (none) — no raw atlas at any tested geometry, slot0 assumption removed')


main()
