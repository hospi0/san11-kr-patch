"""Milestone build: Korean main menu.

Patches, all in place inside a copy of the ISO (no file sizes change, so LBAs and
directory records stay valid -- see docs/03):
  1. s11pkres.bin  : paint 2,350 Hangul glyphs over the kanji slots the codec
                     reassigned (tools/encoding.py)
  2. SLPM_667.01   : rewrite the main-menu strings as Korean, NUL-padded to the
                     original 16 B slot stride

Deliberately mixes ideographic and half-width spaces across menu items so one
boot tells us whether the single-byte space works -- that decides the text budget
for the whole project.

Usage: python build_menu.py <iso> <font.ttc> [ink_h] [weight]
"""
import os
import sys

import numpy as np
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from encoding import Codec                                   # noqa: E402
from font_build import render_fixed, autofit_size, SS        # noqa: E402
from iso import walk, find                                   # noqa: E402

ATLAS_IN_S11 = 0x49810
PER, PIX = 224, 200
YBASE = 19

# (file offset in SLPM_667.01, slot bytes, original, Korean, half-width space?)
MENU = [
    (0x4498e8, 16, 'つづきから',     '이어서 하기',   True),
    (0x4498f8, 16, 'はじめから',     '새로 시작',     True),
    (0x449908, 16, 'チュートリアル', '튜토리얼',      False),
    (0x449918, 16, '武将登録・編集', '무장 등록·편집', True),   # 15 B only with half-width space
    (0x449928, 16, 'オプション',     '옵션',          False),
    (0x4a1ec8, 16, '決戦制覇モード', '결전 제패 모드', True),   # 14 B with half-width spaces
]


def main():
    iso_path = sys.argv[1]
    fontpath = sys.argv[2] if len(sys.argv) > 2 else 'C:/Windows/Fonts/batang.ttc'
    ink_h = float(sys.argv[3]) if len(sys.argv) > 3 else 18.0
    weight = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7

    f, vol, entries = walk(iso_path)
    s11_off = find(entries, 'S11PKRES.BIN')[1] * 2048
    elf_off = find(entries, 'SLPM_667.01')[1] * 2048
    f.close()
    print('ISO: S11PKRES.BIN @%#x   SLPM_667.01 @%#x' % (s11_off, elf_off))

    # --- read the ELF out of the ISO so the codec sees the real table ---
    with open(iso_path, 'rb') as r:
        r.seek(elf_off)
        elf = r.read(5242752)
    tmp = os.path.join(HERE, '_elf.tmp')
    open(tmp, 'wb').write(elf)
    codec = Codec(tmp)
    os.remove(tmp)
    print('codec: %d syllables over %d kanji carriers (%d spare)'
          % (len(codec.syllables), len(codec.kanji_pool),
             len(codec.kanji_pool) - len(codec.syllables)))

    # --- 1. paint the Hangul font ---
    em, ratio = autofit_size(fontpath, ink_h)
    font = ImageFont.truetype(fontpath, int(round(em * SS)))
    print('font: %s  ink_h=%.0f -> em=%.1f  weight=%.1f' % (fontpath, ink_h, em, weight))

    slots = codec.glyph_slots()
    with open(iso_path, 'r+b') as w:
        for slot, ch in slots:
            px = render_fixed(ch, font, YBASE, weight=weight)
            packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()
            assert len(packed) == PIX
            w.seek(s11_off + ATLAS_IN_S11 + slot * PER)
            w.write(packed)
    print('painted %d Hangul glyphs into the atlas' % len(slots))

    # --- 2. rewrite the menu strings ---
    with open(iso_path, 'r+b') as w:
        for off, cap, jp, kr, hw in MENU:
            b, ok = codec.fit(kr, cap, halfwidth_space=hw)
            if not ok:
                raise SystemExit('%r needs %d B, slot is %d B' % (kr, len(b) + 1, cap))
            w.seek(elf_off + off)
            cur = w.read(cap)
            expect = jp.encode('cp932')
            if not cur.startswith(expect):
                raise SystemExit('REFUSED: %#x does not hold %r (found %r)'
                                 % (off, jp, cur[:len(expect)]))
            w.seek(elf_off + off)
            w.write(b + b'\x00' * (cap - len(b)))
            print('  %#08x  %-16s -> %-14s %2d/%d B  space=%s'
                  % (off, jp, kr, len(b), cap, 'half' if hw else 'ideo'))

    print('\ndone -- boot with:  pcsx2-qt.exe -fastboot -- "%s"' % iso_path)
    print('(do NOT load a savestate: the old font would still be in RAM)')


main()
