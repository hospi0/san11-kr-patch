"""특기 테이블 레이아웃 가설 검정.

관측: 확인된 특기 이름 오프셋이 두 계열로 갈린다.
  A = 0x541b + n*0x5d  (鬼門 0x541b, 沈着 0x54d5, 築城 0x5649, 繁殖 0x57bd)
  B = 0x543e + n*0x5d  (踏破 0x543e, 運搬 0x549b, 解毒 0x54f8, 待伏 0x57e0,
                        不屈 0x5bdf, 金剛 0x5c3c, 鉄壁 0x5c99)
즉 이름 간격이 0x23, 0x3a, 0x23, 0x3a… 로 번갈아 = 주기 0x5d에 이름이 둘.

이게 진짜인지 두 계열을 끝까지 걸어보고, 각 자리에 '이름\\0 + 카타카나읽기\\0' 크립이
서는지 본다. 크립이 깨지는 지점 = 테이블 끝.

⚠️stride를 결론으로 쓰지 말 것. 크립 성공률을 같이 찍어서, 실패가 몇 개인지 드러낸다
([[feedback_scan_coverage_and_detectors]] — 커버리지 없는 '확정'은 무효).
"""
import io
import os
import re
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
KATA = re.compile(r'^[ァ-ヶー・]+$')
NAME_OK = re.compile(r'^[一-鿿]{2,4}$')


def cstr(blob, off):
    end = blob.find(b'\x00', off)
    if end < 0:
        return None, len(blob)
    try:
        return blob[off:end].decode('cp932'), end + 1
    except UnicodeDecodeError:
        return None, end + 1


def probe(blob, off):
    """off에 '이름\\0 읽기\\0'이 서면 (이름, 읽기), 아니면 (원문, None)."""
    name, nxt = cstr(blob, off)
    if name is None:
        return '<디코드실패>', None
    if not NAME_OK.match(name):
        return name, None
    reading, _ = cstr(blob, nxt)
    if reading and KATA.match(reading):
        return name, reading
    return name, None


def walk(blob, base, stride, out, label):
    out.write('\n===== 계열 %s: base 0x%x, stride 0x%x =====\n' % (label, base, stride))
    ok = bad = 0
    rows = []
    for n in range(0, 200):
        off = base + n * stride
        if off + stride > len(blob):
            break
        name, reading = probe(blob, off)
        good = reading is not None
        ok, bad = ok + good, bad + (not good)
        rows.append((n, off, name, reading, good))
    # 연속 실패가 4개 이상 나오는 첫 지점 = 테이블 끝 후보
    end = None
    run = 0
    for n, off, name, reading, good in rows:
        run = 0 if good else run + 1
        if run >= 4 and end is None:
            end = off - 3 * stride
    for n, off, name, reading, good in rows:
        if end is not None and off >= end:
            break
        out.write('%3d  0x%04x  %-5s %-14s %s\n'
                  % (n, off, name, reading or '', '' if good else '  ← 크립 실패'))
    inside = [r for r in rows if end is None or r[1] < end]
    g = sum(1 for r in inside if r[4])
    out.write('# 계열 %s: 테이블 끝 후보 0x%s / 범위 안 %d칸 중 크립 성공 %d (%.0f%%)\n'
              % (label, ('%04x' % end) if end else '?', len(inside), g,
                 100.0 * g / max(1, len(inside))))
    return end


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    walk(blob, 0x541b, 0x5d, out, 'A')
    walk(blob, 0x543e, 0x5d, out, 'B')
    out.close()


if __name__ == '__main__':
    main()
