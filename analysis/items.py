"""아이템 테이블 특정 (2026-07-17 세션7 말).

## 확인된 것
- **52벌 복사본** — 로스터와 같은 구조(그룹A 엔트리 6~21 = 16벌 rel 0x253f5
  / 그룹B 엔트리 24~29·32~61 = 36벌 rel 0x7f40a). 로스터도 52벌 A16/B36이다(docs/06).
- **stride 0x39(57)** — 리터럴 위치가 전부 0x39 배수로 떨어진다:
  赤兎馬 0x2522d / 爪黄飛電 +2 / 七星宝刀 +7 / 倚天の剣 +8 / 青釭の剣 +9 /
  青龍偃月刀 +12 / 手戟 +21,+22 / 孫子の兵法書 +30

⚠️로스터처럼 **사본마다 내용이 다를 수 있다**(docs/06: A엔 水滸伝 보너스 무장, B엔 placeholder).
→ 일괄 주입 금지. **사본마다 자기 바이트를 읽어 번역**할 것.
"""
import io
import os
import re
import struct
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')
STRIDE = 0x39
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
    e6 = s11[tab[6][0] * sec: tab[6][0] * sec + tab[6][1]]

    anchor = e6.find('倚天の剣'.encode('cp932'))
    out.write('# entry6 크기 0x%x, 倚天の剣 @0x%x, stride 0x%x\n\n' % (len(e6), anchor, STRIDE))

    # 앵커에서 양쪽으로 걸으며 '이름\0 + 카타카나읽기\0' 크립이 서는 범위를 찾는다
    lo = anchor
    while lo - STRIDE >= 0:
        o = lo - STRIDE
        nm = cstr(e6, o, 0x18)
        if not nm or len(nm) > 10:
            break
        lo = o
    hi = anchor
    while hi + STRIDE < len(e6):
        o = hi + STRIDE
        nm = cstr(e6, o, 0x18)
        if not nm or len(nm) > 10:
            break
        hi = o

    cnt = (hi - lo) // STRIDE + 1
    out.write('테이블 범위 0x%x ~ 0x%x, %d개\n' % (lo, hi + STRIDE, cnt))
    out.write('검산: (끝-시작)/stride = %.2f\n\n' % ((hi + STRIDE - lo) / STRIDE))
    out.write('idx  off      이름              읽기\n')
    for i in range(cnt):
        o = lo + i * STRIDE
        nm = cstr(e6, o, 0x18)
        rd = cstr(e6, o + len(nm.encode('cp932')) + 1, 0x18) if nm else ''
        out.write('%3d  0x%05x  %-16s %s\n' % (i, o, nm, rd if rd and KATA.match(rd) else ''))
    out.close()


if __name__ == '__main__':
    main()
