"""Render a character into the game's glyph format: 4bpp, 20x20, 200 bytes.

Format (confirmed by pixel-exact match against EE RAM, docs/03):
  - 20 rows x 10 bytes; each byte holds two 4bpp pixels, LOW nibble = LEFT pixel
  - index 0 = transparent, 1..15 = anti-alias ramp (higher = brighter/more solid)
  - the glyph occupies 200 B; the following 24 B of the 224 B pitch are runtime
    scratch and must be left as zero in the archive

Usage: python make_glyph.py <char> <font.ttf> <out.bin> [preview.png]
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CH = sys.argv[1]
FONT = sys.argv[2]
OUT = sys.argv[3]
PREVIEW = sys.argv[4] if len(sys.argv) > 4 else None
W = H = 20


def render(ch, fontpath):
    # oversample then box-filter down: gives a clean 16-level ramp at 20px
    SS = 8
    best = None
    for size in range(H * SS, H * SS // 2, -1):
        f = ImageFont.truetype(fontpath, size)
        img = Image.new('L', (W * SS, H * SS), 0)
        d = ImageDraw.Draw(img)
        l, t, r, b = d.textbbox((0, 0), ch, font=f)
        w, h = r - l, b - t
        if w <= W * SS and h <= H * SS:
            d.text(((W * SS - w) / 2 - l, (H * SS - h) / 2 - t), ch, font=f, fill=255)
            best = img
            break
    if best is None:
        raise SystemExit('could not fit glyph')
    small = best.resize((W, H), Image.BOX)
    a = np.array(small, np.float32) / 255.0
    return np.clip(np.rint(a * 15), 0, 15).astype(np.uint8)


px = render(CH, FONT)
print('glyph %r from %s' % (CH, FONT))
for row in px:
    print('  ' + ''.join(' .:-=+*#%@'[min(9, int(v))] for v in row))
print('ink pixels: %d/400   max level: %d' % (int((px > 0).sum()), int(px.max())))

# pack to 4bpp, low nibble = left pixel
packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8)
assert packed.shape == (H, 10), packed.shape
blob = packed.tobytes()
assert len(blob) == 200
open(OUT, 'wb').write(blob)
print('wrote %d B -> %s' % (len(blob), OUT))

if PREVIEW:
    Image.fromarray((px * 17).astype(np.uint8), 'L').resize((W * 12, H * 12), Image.NEAREST).save(PREVIEW)
    print('preview -> %s' % PREVIEW)
