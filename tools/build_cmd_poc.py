# -*- coding: utf-8 -*-
"""커맨드 그래픽 PoC — idx=94의 都市 셀 한 칸만 「도시」로 바꿔 심는다.

세션2에 「커맨드 UI = idx=94 스프라이트」라고 렌더로 확인했지만 **쓰기 경로는 한 번도
검증한 적이 없다**. 90칸을 한꺼번에 그리기 전에 한 칸으로 확인한다:
  · 격자 좌표(y=565, byte x=33)가 맞는가
  · 4bpp·저니블=왼쪽 포맷이 맞는가
  · 게임이 정말 이 바이트를 읽어 그리는가 (다른 사본/캐시가 없는가)
  · 인덱스 0~15가 어떤 색으로 나오는가 (팔레트/금색 틴트 경로)

Usage: python build_cmd_poc.py <iso사본> [font.ttc] [ink_h] [weight]
"""
import os
import struct
import sys

import numpy as np
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cmd_graphics import PITCH_B, CELL_H, SS, autofit, make_cell, pack_rows, cell_xy  # noqa: E402
from iso import walk, find                                                            # noqa: E402

S11_SRC = r"C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan)/s11pkres.bin"
ENTRY = 94


def entry_off(s11, idx):
    sec = struct.unpack("<I", s11[8:12])[0]
    o, b = struct.unpack("<II", s11[0x10 + idx * 8: 0x10 + idx * 8 + 8])
    return o * sec, b


def main():
    iso = sys.argv[1]
    fontpath = sys.argv[2] if len(sys.argv) > 2 else "C:/Windows/Fonts/batang.ttc"
    ink = float(sys.argv[3]) if len(sys.argv) > 3 else 19.0
    weight = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5

    f, vol, ents = walk(iso)
    s11_off = find(ents, "S11PKRES.BIN")[1] * 2048
    f.close()
    s11 = open(S11_SRC, "rb").read()
    e_off, e_size = entry_off(s11, ENTRY)
    print("ISO S11PKRES @%#x | entry%d @%#x (%d B)" % (s11_off, ENTRY, e_off, e_size))

    size = autofit(fontpath, ink)
    font = ImageFont.truetype(fontpath, size * SS)
    cell = make_cell("도시", font, weight=weight)
    rows = pack_rows(cell)                       # 23행 × 23바이트
    px, py = cell_xy(0, 0)
    bx = px // 2                                 # 픽셀 → 바이트
    assert px % 2 == 0, "셀이 바이트 경계에 안 맞는다"
    print("셀 (행0,열0) = 픽셀 x=%d y=%d → 바이트 x=%d, entry94 내 오프셋 0x%x"
          % (px, py, bx, py * PITCH_B + bx))

    with open(iso, "r+b") as w:
        for r in range(CELL_H):
            off = s11_off + e_off + (py + r) * PITCH_B + bx
            w.seek(off)
            w.write(rows[r].tobytes())
    # 되읽기
    with open(iso, "rb") as rd:
        for r in range(CELL_H):
            rd.seek(s11_off + e_off + (py + r) * PITCH_B + bx)
            assert rd.read(23) == rows[r].tobytes(), "되읽기 불일치 행 %d" % r
    print("도시 셀 심음 (font=%s em=%d ink=%.0f w=%.1f) — 되읽기 검증 통과"
          % (os.path.basename(fontpath), size, ink, weight))
    print('\n부팅: pcsx2-qt.exe -fastboot -- "%s"  (세이브스테이트 금지)' % iso)


main()
