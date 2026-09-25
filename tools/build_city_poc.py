"""도시 PoC 빌드: 平原 → 평원 (도시 테이블, 엔트리5).
증명: 도시 마스터 테이블(연속 SJIS)의 이름 바이트를 한글 운반체로 교체하면
맵/정보패널의 도시명이 한글로 렌더된다.

패치(ISO 사본 in-place, 크기 불변):
  1. s11pkres.bin 아틀라스: 평·원 글리프
  2. s11pkres.bin 도시테이블: 平原ヘイゲン 시그니처에서 平原(95bd8cb4)→평원

Usage: python build_city_poc.py <iso사본> [font.ttc]
"""
import os, sys
import numpy as np
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from encoding import Codec
from font_build import render_fixed, autofit_size, SS
from iso import walk, find

ATLAS_IN_S11 = 0x49810
PER, PIX, YBASE = 224, 200, 19
# 平原 00 ヘイゲン = 도시테이블 시그니처 (유일)
SIG = bytes.fromhex('95bd8cb400' + '8377834383518393')
JP, KR = '平原', '평원'


def main():
    iso = sys.argv[1]
    fontpath = sys.argv[2] if len(sys.argv) > 2 else 'C:/Windows/Fonts/batang.ttc'

    f, vol, entries = walk(iso)
    s11_off = find(entries, 'S11PKRES.BIN')[1] * 2048
    elf_off = find(entries, 'SLPM_667.01')[1] * 2048
    f.close()
    print('S11PKRES @%#x  SLPM @%#x' % (s11_off, elf_off))

    with open(iso, 'rb') as r:
        r.seek(elf_off); elf = r.read(5242752)
    tmp = os.path.join(HERE, '_elf.tmp'); open(tmp, 'wb').write(elf)
    codec = Codec(tmp); os.remove(tmp)

    kr_codes = [codec.code_for(ch) for ch in KR]
    kr_slots = [codec.slot_of[c] for c in kr_codes]
    print('운반체: ' + '  '.join('%s->0x%04x slot%d' % (c, cd, s)
          for c, cd, s in zip(KR, kr_codes, kr_slots)))

    # 1. 글리프
    em, _ = autofit_size(fontpath, 18.0)
    font = ImageFont.truetype(fontpath, int(round(em * SS)))
    with open(iso, 'r+b') as w:
        for ch, slot in zip(KR, kr_slots):
            px = render_fixed(ch, font, YBASE, weight=0.7)
            packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()
            w.seek(s11_off + ATLAS_IN_S11 + slot * PER); w.write(packed)
    print('painted %s' % KR)

    # 2. 도시테이블 바이트 교체
    with open(iso, 'rb') as r:
        r.seek(s11_off); s11 = r.read(517752832)
    offs = []; i = s11.find(SIG)
    while i != -1:
        offs.append(i); i = s11.find(SIG, i + 1)
    print('平原ヘイゲン 시그니처 %d회' % len(offs))
    if not offs:
        raise SystemExit('시그니처 못찾음')
    new = b''.join(__import__('struct').pack('>H', c) for c in kr_codes)  # 평원 4B
    assert len(new) == 4
    with open(iso, 'r+b') as w:
        for off in offs:
            w.seek(s11_off + off); w.write(new)
    print('도시명 %d곳 교체: %s -> %s' % (len(offs), JP, KR))
    print('\nboot: pcsx2-qt.exe -fastboot -- "%s"  (세이브스테이트 금지)' % iso)
    print('맵에서 유비 수도 平原이 "평원"으로 보여야 함.')


main()
