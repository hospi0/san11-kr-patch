"""아이템·작위 번역본 검증 (커버리지 전수 + 예산 + 화면 폭).

★예산 계산은 **실제 인코더**(Codec.encode)로. 손으로 세지 말 것.
★화면 폭도 같이 본다 — 바이트를 통과해도 열에서 잘린다([[feedback_kr_patch_verification]]).
  아이템일람 아이템 열: 원본 「雌雄一対の剣」 6전각이 안 잘리고 보였다 → 안전선 최소 6.0.
  세력일람 작위 열: 원본 최대 「五官中郎将」 5전각 → 안전선 5.0(원본 최대 = 확실한 선).
"""
import io
import os
import re
import struct
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from encoding import Codec          # noqa: E402
from item_names import ITEMS, RANKS  # noqa: E402

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')
ELF = os.path.join(ROM, 'SLPM_667.01')

I_STRIDE, I_COUNT, I_NAME_CAP = 0x39, 50, 12      # 이름 텍스트 최대 12B (+0x0c가 널)
R_BASE, R_STRIDE, R_COUNT, R_NAME_CAP = 0x41ca, 0x2c, 10, 10
GRP_A = list(range(6, 22))
GRP_B = list(range(24, 30)) + list(range(32, 62))
A_ANCHOR, B_ANCHOR = 0x253f5, 0x7f40a

# 화면 폭 안전선 = 원본이 실제로 그 열에 그려낸 최대(실기 스크린샷 확인)
DISP_ITEM, DISP_RANK = 6.0, 5.0


def width(s):
    return sum(0.5 if 0x20 <= ord(c) <= 0x7E else 1.0 for c in s)


def cstr(b, off, cap):
    e = b.find(b'\x00', off, off + cap)
    if e < 0:
        e = off + cap
    try:
        return b[off:e].decode('cp932')
    except UnicodeDecodeError:
        return None


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    codec = Codec(ELF)
    s11 = open(S11, 'rb').read()
    n, sec = struct.unpack('<II', s11[4:12])
    tab = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]

    def ent(i):
        o, b = tab[i]
        return s11[o * sec: o * sec + b]

    bad = 0

    # ---- 아이템: 52벌 × 50슬롯 전수 ----
    miss, over, wide = set(), [], []
    slots = 0
    for anchor, idxs in ((A_ANCHOR, GRP_A), (B_ANCHOR, GRP_B)):
        for i in idxs:
            e = ent(i)
            base = anchor - 8 * I_STRIDE
            for k in range(I_COUNT):
                nm = cstr(e, base + k * I_STRIDE, I_NAME_CAP)
                slots += 1
                if not nm:
                    continue
                kr = ITEMS.get(nm)
                if kr is None:
                    miss.add(nm)
                    continue
                b = codec.encode(kr, halfwidth_space=False)
                if len(b) > I_NAME_CAP:
                    over.append((nm, kr, len(b)))
                if width(kr) > DISP_ITEM:
                    wide.append((nm, kr, width(kr)))
    out.write('===== 아이템 (52벌 × %d슬롯 = %d칸 전수) =====\n' % (I_COUNT, slots))
    out.write('번역 없는 이름 : %d %s\n' % (len(miss), sorted(miss) or ''))
    out.write('예산 초과      : %d %s\n' % (len(set(over)), sorted(set(over)) or ''))
    out.write('화면 폭 초과   : %d %s\n' % (len(set(wide)), sorted(set(wide)) or ''))
    bad += len(miss) + len(set(over)) + len(set(wide))

    # ---- 작위 ----
    e5 = ent(5)
    out.write('\n===== 작위 (entry5 0x%x × %d) =====\n' % (R_BASE, R_COUNT))
    for k in range(R_COUNT):
        o = R_BASE + k * R_STRIDE
        nm = cstr(e5, o, R_NAME_CAP + 1)
        kr = RANKS.get(nm)
        if kr is None:
            out.write('  ❌ 번역 없음: %r\n' % nm); bad += 1; continue
        b = len(codec.encode(kr, halfwidth_space=False))
        w = width(kr)
        flag = ''
        if b > R_NAME_CAP:
            flag = ' ❌ 예산초과'; bad += 1
        elif w > DISP_RANK:
            flag = ' ❌ 폭초과'; bad += 1
        out.write('  %-10s → %-6s %2dB / cap %d, 폭 %.1f / %.1f%s\n'
                  % (nm, kr, b, R_NAME_CAP, w, DISP_RANK, flag))

    out.write('\n%s\n' % ('✅ 전부 통과' if bad == 0 else '❌ 문제 %d건' % bad))
    out.close()


if __name__ == '__main__':
    main()
