"""아이템 52벌 사본의 이름 합집합 + 작위 10개를 뽑는다.

★사본 52벌이 **28종으로 내용이 다르다**(시나리오마다 등장 아이템이 다름). 로스터와 같은
구조라 **일괄 주입 금지** — 사본마다 자기 바이트를 읽어 번역해야 한다(docs/06).
번역 사전은 **합집합** 하나로 만들고, 빌드 때 사본별로 조회한다.

필드(전수 열별 통계로 확정, analysis/item_rank_cols.py):
  아이템(57B): +0x00 이름 ≤12B(★+0x0c가 50/50 널) · +0x0d 읽기(★50/50 0x83)
  작위(44B)  : +0x00 이름 ≤10B · +0x0b 읽기(★10/10 0x83)
"""
import io
import os
import re
import struct
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')

I_STRIDE, I_COUNT, I_NAME_CAP, I_READ = 0x39, 50, 0x0c, 0x0d
GRP_A = list(range(6, 22))
GRP_B = list(range(24, 30)) + list(range(32, 62))
A_ANCHOR, B_ANCHOR = 0x253f5, 0x7f40a      # 倚天の剣 = 아이템 idx 8
KATA = re.compile(r'^[ァ-ヶー・]+$')


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
    s11 = open(S11, 'rb').read()
    n, sec = struct.unpack('<II', s11[4:12])
    tab = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]

    def ent(i):
        o, b = tab[i]
        return s11[o * sec: o * sec + b]

    # ---- 아이템 합집합 ----
    seen = {}          # 이름 -> (읽기, 나온 사본 수)
    for grp, anchor, idxs in (('A', A_ANCHOR, GRP_A), ('B', B_ANCHOR, GRP_B)):
        for i in idxs:
            e = ent(i)
            base = anchor - 8 * I_STRIDE
            for k in range(I_COUNT):
                o = base + k * I_STRIDE
                nm = cstr(e, o, I_NAME_CAP)
                if not nm:
                    continue
                rd = cstr(e, o + I_READ, I_STRIDE - I_READ) or ''
                if not KATA.match(rd or 'x'):
                    rd = ''
                cur = seen.get(nm)
                seen[nm] = (rd or (cur[0] if cur else ''), (cur[1] if cur else 0) + 1)

    out.write('===== 아이템 이름 합집합 %d종 (52벌 전체) =====\n' % len(seen))
    out.write('이름\t읽기\t등장사본수\n')
    for nm, (rd, c) in sorted(seen.items(), key=lambda x: -x[1][1]):
        out.write('%s\t%s\t%d\n' % (nm, rd, c))

    # ---- 작위 ----
    e5 = ent(5)
    out.write('\n===== 작위 10개 (entry5 0x41ca stride 0x2c) =====\n')
    for k in range(10):
        o = 0x41ca + k * 0x2c
        nm = cstr(e5, o, 0x0b)
        rd = cstr(e5, o + 0x0b, 0x2c - 0x0b)
        out.write('%2d  0x%04x  %-10s %s\n' % (k, o, nm, rd if rd and KATA.match(rd) else ''))

    # 0x215a 사본 — 다중소스 확인
    out.write('\n===== 0x215a 근처 (大司馬 두 번째 위치 = 사본?) =====\n')
    for o in range(0x2140, 0x2200, 0x10):
        row = e5[o:o + 0x10]
        try:
            t = row.decode('cp932', errors='replace')
        except Exception:
            t = ''
        out.write('0x%04x  %-47s %s\n'
                  % (o, ' '.join('%02x' % b for b in row),
                     ''.join(c if c.isprintable() else '.' for c in t)))
    out.close()


if __name__ == '__main__':
    main()
