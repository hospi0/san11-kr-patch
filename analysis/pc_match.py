"""PS2 풀 ↔ PC판 msg 대응 확인 (2026-07-17 세션7).

## 왜 되나
PC 한글판(도원결의·blogspot)의 `S11MSG0*.s11`은 **LS11 매직만 유지하고 무압축**으로 저장돼 있다
(심볼 테이블 256B가 전부 0 + 블록헤더의 **압축크기 == 원본크기**). 그래서 **지금 바로 읽힌다.**
PC 일본어판은 압축돼 있어 아직 못 읽는다.

## 확인할 것
1. PC KOR msg의 메시지 구조가 PS2 풀과 같은가 (`[u16 count][u32 offs]`, `offs[0]==2+4*count`)
2. 메시지 **개수**가 대응하는가 (PS2 풀 = 749개)
3. PC KOR 텍스트가 어떤 인코딩인가 (EUC-KR 크립이 0개였다 → 운반체 방식일 가능성)
"""
import io
import os
import struct
import sys
from collections import Counter

B = r"E:/hospi/games/Old Games/ROTK/삼국지11pk 에보니 한글판/Origin/Game/Language"
HERE = os.path.dirname(__file__)


def read_ls11(path):
    """LS11 파일 → (압축?, 데이터). 무압축(comp==uncomp)이면 데이터를 그대로 준다."""
    f = open(path, 'rb').read()
    assert f[:4] == b'LS11'
    c, u, p = struct.unpack('>III', f[0x110:0x11c])
    return (c != u), f[p:p + c], c, u


def msgs(data):
    """[u16 count][u32 offs × count] 구조 → 세그먼트 리스트. 아니면 None."""
    if len(data) < 6:
        return None
    n = struct.unpack('<H', data[:2])[0]
    if not (0 < n < 20000) or 2 + 4 * n > len(data):
        return None
    offs = list(struct.unpack('<%dI' % n, data[2:2 + 4 * n]))
    if offs[0] != 2 + 4 * n:
        return None
    b = offs + [len(data)]
    return [data[b[i]:b[i + 1]] for i in range(n)]


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    pool = open(os.path.join(HERE, '..', 'work', 'entry4_pool.bin'), 'rb').read()
    ps2 = msgs(pool)
    out.write('PS2 풀: %d B, 메시지 %d개\n\n' % (len(pool), len(ps2)))

    for tag, d, sub in (('JPN', 'JPN_PK_v1.1.1', 'msg'),
                        ('KOR-도원결의', 'KOR_도원결의_111009', 'msg'),
                        ('KOR-blogspot', 'KOR_san11kor.blogspot_v3.0', 'MSG')):
        out.write('===== %s =====\n' % tag)
        for i in range(4):
            p = os.path.join(B, d, 'Media', sub, 'S11MSG%02d.s11' % i)
            if not os.path.exists(p):
                continue
            comp, data, c, u = read_ls11(p)
            m = msgs(data) if not comp else None
            out.write('  msg%02d %s 압축=%-8s 데이터 %7d B → 메시지 %s%s\n'
                      % (i, os.path.basename(p), '★압축됨(못읽음)' if comp else '무압축✅',
                         len(data), len(m) if m else '읽기실패',
                         '  ★★PS2 풀(749)과 개수 일치!' if m and len(m) == len(ps2) else ''))
    out.close()


if __name__ == '__main__':
    main()
