"""Build Hangul glyphs that match the game font's metrics.

Measured from the real atlas (tools/analysis/font_metrics.py):
  - cell 20x20, 4bpp, row 0 is blank, ink runs down to row 19 (baseline = cell
    bottom), glyphs use nearly the full 20px width.
  - dense square kanji (国, 編) occupy about 19w x 18h at top≈2.

So: ONE font size and ONE baseline for every syllable -- never "scale each glyph
to fit", which makes 이 huge and 뷁 small.

Usage:
  python font_build.py preview <font.ttf> <s11pkres.bin> <out.png> [size] [ybase]
  python font_build.py atlas   <font.ttf> <out.bin> [size] [ybase]
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W = H = 20
SS = 8                       # supersample factor
ATLAS_OFF = 0x49810
PER, PIX, G = 224, 200, 3773

# KS X 1001 완성형 2350 syllables, in standard order
def ks_syllables():
    import codecs
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try:
                ch = bytes([hi, lo]).decode('euc-kr')
            except Exception:
                continue
            if len(ch) == 1 and 0xAC00 <= ord(ch) <= 0xD7A3:
                out.append(ch)
    return out


PAD = W * SS          # generous margin so a big font never gets clipped by the canvas


def render_fixed(ch, font, ybase, xpad=0, weight=0.0):
    """Render with a fixed size and a fixed baseline -- identical treatment for all.

    Draws onto an oversized canvas and crops the 20x20 cell out of it, so a font
    larger than the cell overflows naturally instead of being silently chopped by
    the canvas edge (which turned 무장 into 부상).

    `weight` synthetically emboldens by `weight` final-pixels of outline. The game's
    own Mincho has much heavier strokes than Batang, and Windows ships no bold
    Korean serif, so this is how we match it.
    """
    canvas = Image.new('L', (W * SS + 2 * PAD, H * SS + 2 * PAD), 0)
    d = ImageDraw.Draw(canvas)
    sw = int(round(weight * SS / 2))
    l, t, r, b = d.textbbox((0, 0), ch, font=font, stroke_width=sw)
    w = r - l
    x = PAD + (W * SS - w) / 2 - l + xpad * SS      # centre in the cell
    y = PAD + ybase * SS - b                        # ink bottom on the baseline
    d.text((x, y), ch, font=font, fill=255, stroke_width=sw, stroke_fill=255)
    cell = canvas.crop((PAD, PAD, PAD + W * SS, PAD + H * SS))
    a = np.array(cell.resize((W, H), Image.BOX), np.float32) / 255.0
    return np.clip(np.rint(a * 15), 0, 15).astype(np.uint8)


# Reference syllables spanning the shape space: no-받침 / 받침 / 복잡한 받침 / 넓은 것
FIT_REF = '가무뭄힘이을왕넓쫓뷁'


def autofit_size(fontpath, target_h):
    """Find the em size whose median ink height over FIT_REF equals target_h px."""
    probe = 400
    f = ImageFont.truetype(fontpath, probe)
    ratios = []
    for ch in FIT_REF:
        img = Image.new('L', (probe * 2, probe * 2), 0)
        d = ImageDraw.Draw(img)
        d.text((probe // 2, probe // 2), ch, font=f, fill=255)
        a = np.array(img)
        rows = np.nonzero((a > 0).any(axis=1))[0]
        if len(rows):
            ratios.append((rows[-1] - rows[0] + 1) / probe)
    med = float(np.median(ratios))
    return target_h / med, med


def game_glyphs(path, slots):
    f = open(path, 'rb')
    out = []
    for s in slots:
        f.seek(ATLAS_OFF + s * PER)
        b = np.frombuffer(f.read(PIX), np.uint8).reshape(20, 10)
        px = np.empty((20, 20), np.uint8)
        px[:, 0::2] = b & 0x0f
        px[:, 1::2] = b >> 4
        out.append(px)
    return out


def strip(cells, scale):
    a = np.concatenate([c * 17 for c in cells], axis=1)
    im = Image.fromarray(a.astype(np.uint8), 'L').convert('RGB')
    return im.resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST)


def cmd_preview():
    fontpath, s11, out = sys.argv[2], sys.argv[3], sys.argv[4]
    # sizes are now target INK HEIGHTS in px (the game's dense kanji use ~18)
    heights = [float(x) for x in (sys.argv[5].split(',') if len(sys.argv) > 5 else ['16', '17', '18', '19'])]
    ybase = int(sys.argv[6]) if len(sys.argv) > 6 else 19
    sizes = []
    for th in heights:
        em, ratio = autofit_size(fontpath, th)
        sizes.append((th, em))
        print('  target ink height %.0fpx -> em %.1fpx (font ink/em = %.3f)' % (th, em, ratio))

    # real game glyphs for reference: 武将登録・編集 / 決戦制覇
    ref_slots = [2761, 1660, 2359, 3276, 4, 2827, 1577]
    ref = game_glyphs(s11, ref_slots)

    SCALE = 6
    rows = []
    rows.append(('GAME (원본)', strip(ref, SCALE)))
    for th, em in sizes:
        f = ImageFont.truetype(fontpath, int(round(em * SS)))
        cells = [render_fixed(c, f, ybase) for c in '무장 등록·편집']
        rows.append(('ink h=%.0f' % th, strip(cells, SCALE)))

    PADL = 130
    maxw = max(r[1].width for r in rows)
    canvas = Image.new('RGB', (PADL + maxw, len(rows) * (H * SCALE + 10) + 60), (18, 18, 18))
    d = ImageDraw.Draw(canvas)
    y = 6
    for label, im in rows:
        canvas.paste(im, (PADL, y))
        d.text((6, y + H * SCALE // 2 - 6), label, fill=(255, 220, 80))
        y += H * SCALE + 10
    # 1:1 comparison
    d.text((6, y + 4), '1:1', fill=(120, 200, 255))
    x = PADL
    canvas.paste(strip(ref, 1), (x, y + 4)); x += 20 * len(ref) + 12
    for th, em in sizes:
        f = ImageFont.truetype(fontpath, int(round(em * SS)))
        cells = [render_fixed(c, f, ybase) for c in '무장 등록·편집']
        canvas.paste(strip(cells, 1), (x, y + 4)); x += 20 * len(cells) + 12
    canvas.save(out)
    print('wrote %s  (sizes=%s ybase=%d)' % (out, sizes, ybase))


def cmd_atlas():
    fontpath, out = sys.argv[2], sys.argv[3]
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 20
    ybase = int(sys.argv[5]) if len(sys.argv) > 5 else 19
    f = ImageFont.truetype(fontpath, size * SS)
    syl = ks_syllables()
    print('KS X 1001 완성형: %d syllables' % len(syl))
    blob = bytearray()
    for ch in syl:
        px = render_fixed(ch, f, ybase, 0)
        packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8)
        blob += packed.tobytes()
    open(out, 'wb').write(bytes(blob))
    print('wrote %s (%d syllables x %d B = %d B)' % (out, len(syl), PIX, len(blob)))


if __name__ == '__main__':
    {'preview': cmd_preview, 'atlas': cmd_atlas}[sys.argv[1]]()
