"""아이템·작위 테이블 특정 (전수 — 히트 캡 없음).

⚠️find_three.py는 히트를 6개로 잘라서 아이템 복사본이 "6벌"로 보였다. 캡을 걸어놓고
개수를 결론내면 안 된다 — [[feedback_scan_coverage_and_detectors]].
"""
import io
import os
import struct
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')


def find_all(buf, b):
    out, i = [], buf.find(b)
    while i >= 0:
        out.append(i)
        i = buf.find(b, i + 1)
    return out


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    s11 = open(S11, 'rb').read()
    n, sec = struct.unpack('<II', s11[4:12])
    table = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]
    starts = sorted((o * sec, i, b) for i, (o, b) in enumerate(table))

    def owner(off):
        lo, hi = 0, len(starts)
        while lo < hi:
            mid = (lo + hi) // 2
            if starts[mid][0] <= off:
                lo = mid + 1
            else:
                hi = mid
        if lo == 0:
            return None, None
        s, idx, size = starts[lo - 1]
        return (idx, off - s) if off < s + size else (None, None)

    out.write('===== 아이템: 「倚天の剣」 전 복사본 =====\n')
    hits = find_all(s11, '倚天の剣'.encode('cp932'))
    ent = []
    for h in hits:
        i, rel = owner(h)
        ent.append((i, rel))
    out.write('총 %d벌\n' % len(hits))
    for i, rel in ent:
        out.write('  엔트리 %s  rel 0x%x\n' % (i, rel))

    out.write('\n===== 작위: entry5 안 위치 =====\n')
    e5_off = table[5][0] * sec
    e5 = s11[e5_off:e5_off + table[5][1]]
    for w in ('大司馬', '大将軍', '州牧', '州刺史', '丞相', '皇帝', '王'):
        hs = find_all(e5, w.encode('cp932'))
        out.write('  %-6s %s\n' % (w, ' '.join('0x%x' % h for h in hs)))

    # 작위 테이블 = 관직(0x4382) 바로 앞. stride 0x2c로 뒤로 걸어본다.
    out.write('\n===== 작위 테이블 후보: 0x4382에서 stride 0x2c로 뒤로 =====\n')
    for k in range(1, 16):
        off = 0x4382 - k * 0x2c
        end = e5.find(b'\x00', off)
        try:
            nm = e5[off:end].decode('cp932')
        except Exception:
            nm = '<디코드실패>'
        rd_end = e5.find(b'\x00', end + 1)
        try:
            rd = e5[end + 1:rd_end].decode('cp932')
        except Exception:
            rd = '?'
        out.write('  -%2d  0x%04x  %-8s %s\n' % (k, off, nm, rd))
    out.close()


if __name__ == '__main__':
    main()
