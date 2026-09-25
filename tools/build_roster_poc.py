"""로스터 PoC 빌드: 于禁 → 우금 (한 명만).

증명 목표: 무장 로스터의 이름 바이트를 한글 운반체 코드로 in-place 교체하면
武将情報 화면에 한글 이름이 렌더된다.

패치(전부 ISO 사본 in-place, 크기 불변):
  1. s11pkres.bin 아틀라스: 우(slot1816)·금(slot485) 글리프 그리기
  2. s11pkres.bin 로스터: 于禁文則 시그니처 52벌에서 于(98b0)→우(908b), 禁(8bd6)→금(897b)

Usage: python build_roster_poc.py <iso사본> [font.ttc] [ink_h] [weight]
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

# 于禁文則 (于 000000 禁 000000 文則) 시그니처
SIG = bytes.fromhex('98b00000008bd600000095b691a5')
# 교체: 于禁 → 우금
JP_NAME = '于禁'
KR_NAME = '우금'


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

    # ELF 읽어 codec
    with open(iso_path, 'rb') as r:
        r.seek(elf_off); elf = r.read(5242752)
    tmp = os.path.join(HERE, '_elf.tmp')
    open(tmp, 'wb').write(elf)
    codec = Codec(tmp)
    os.remove(tmp)

    # 운반체 코드/슬롯
    kr_codes = [codec.code_for(ch) for ch in KR_NAME]
    kr_slots = [codec.slot_of[c] for c in kr_codes]
    print('한글 운반체: ' + '  '.join('%s->0x%04x slot%d' % (ch, c, s)
          for ch, c, s in zip(KR_NAME, kr_codes, kr_slots)))

    # --- 1. 글리프 그리기 (우, 금) ---
    em, ratio = autofit_size(fontpath, ink_h)
    font = ImageFont.truetype(fontpath, int(round(em * SS)))
    with open(iso_path, 'r+b') as w:
        for ch, slot in zip(KR_NAME, kr_slots):
            px = render_fixed(ch, font, YBASE, weight=weight)
            packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()
            assert len(packed) == PIX
            w.seek(s11_off + ATLAS_IN_S11 + slot * PER)
            w.write(packed)
    print('painted %d Hangul glyphs (%s)' % (len(KR_NAME), KR_NAME))

    # --- 2. 로스터 이름 바이트 교체 (52벌) ---
    # s11pkres.bin 전체를 ISO에서 읽어 시그니처 위치 찾기
    with open(iso_path, 'rb') as r:
        r.seek(s11_off)
        # s11pkres 크기 = 517,752,832
        s11 = r.read(517752832)
    offs = []
    i = s11.find(SIG)
    while i != -1:
        offs.append(i); i = s11.find(SIG, i + 1)
    print('于禁文則 시그니처 %d벌 발견' % len(offs))

    new_sei = codec.encode(KR_NAME[0], halfwidth_space=False)  # 우 = 90 8b
    new_mei = codec.encode(KR_NAME[1], halfwidth_space=False)  # 금 = 89 7b
    assert len(new_sei) == 2 and len(new_mei) == 2
    with open(iso_path, 'r+b') as w:
        for off in offs:
            # 于(off+0) → 우, 禁(off+5) → 금  (姓/名 필드 첫 2바이트)
            w.seek(s11_off + off);     w.write(new_sei)
            w.seek(s11_off + off + 5); w.write(new_mei)
    print('로스터 이름 %d벌 교체: %s -> %s (于 0x98b0->0x%04x, 禁 0x8bd6->0x%04x)'
          % (len(offs), JP_NAME, KR_NAME, kr_codes[0], kr_codes[1]))

    print('\ndone -- boot with:  pcsx2-qt.exe -fastboot -- "%s"' % iso_path)
    print('(세이브스테이트 로드 금지 - 옛 폰트/데이터가 RAM에 남음. 새로 부팅.)')
    print('武将情報에서 于禁을 찾으면 "우금"으로 보여야 함 (읽기 정렬상 ウ 근처).')


main()
