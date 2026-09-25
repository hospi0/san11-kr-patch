"""Write one glyph into the font atlas, in place, inside an ISO.

The atlas lives inside S11PKRES.BIN which sits contiguously in the ISO, so a
glyph can be overwritten without touching file sizes, LBAs or directory records.

Layout (docs/03):
  ISO offset of glyph = <S11PKRES.BIN ISO offset> + 0x49810 + slot*224
  200 B of 4bpp pixels, then 24 B of runtime scratch that stays zero on disc.

Refuses to run unless the bytes currently there look like a glyph slot (pad is
zero), so a wrong offset fails loudly instead of corrupting the image.

Usage: python poke_glyph.py <iso> <slot> <glyph200.bin> [--force]
"""
import sys

ATLAS_IN_S11 = 0x49810
PER = 224
PIX = 200

iso_path, slot, glyph_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
force = '--force' in sys.argv

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from iso import walk, find                                   # noqa: E402

f, vol, entries = walk(iso_path)
hit = find(entries, 'S11PKRES.BIN')
if not hit:
    raise SystemExit('S11PKRES.BIN not in this ISO')
_, lba, size = hit
s11_off = lba * 2048
off = s11_off + ATLAS_IN_S11 + slot * PER
print('S11PKRES.BIN at ISO %#x (lba %d)' % (s11_off, lba))
print('slot %d -> ISO offset %#x' % (slot, off))

f.seek(off)
cur = f.read(PER)
f.close()
if len(cur) != PER:
    raise SystemExit('offset past end of image')
if any(cur[PIX:]) and not force:
    raise SystemExit('REFUSED: pad bytes at +200..224 are not zero (%s) -- offset '
                     'is probably wrong. Use --force only if you are sure.'
                     % cur[PIX:].hex(' '))

glyph = open(glyph_path, 'rb').read()
if len(glyph) != PIX:
    raise SystemExit('glyph must be exactly %d B, got %d' % (PIX, len(glyph)))

with open(iso_path, 'r+b') as w:
    w.seek(off)
    w.write(glyph)
print('wrote %d B at %#x (pad left untouched)' % (PIX, off))

# read back
with open(iso_path, 'rb') as r:
    r.seek(off)
    back = r.read(PIX)
print('verify: %s' % ('OK' if back == glyph else 'MISMATCH'))
