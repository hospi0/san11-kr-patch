"""특기 테이블의 진짜 시작점을 뒤로 걸어서 찾는다.

0x543e에서 stride 0x5d로 앞으로 94칸이 깨끗했고 0x7664(기교 base)에서 정확히 끝났다.
하지만 長駆·飛将·遁走·強行처럼 능력연구 테이블에 있는 특기가 94개 안에 없다
= 테이블이 0x543e보다 앞에서 시작한다는 뜻. 음수 n으로 걸어 크립이 언제 깨지는지 본다.

⚠️앞쪽 이웃은 관직 테이블(0x4382 stride 0x2e × 80, docs/10)이다. 특기 base는
관직 테이블 끝(0x51e2) 뒤여야 한다 — 이게 독립 검산이 된다.
"""
import io
import os
import re
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
KATA = re.compile(r'^[ァ-ヶー・]+$')
NAME_OK = re.compile(r'^[一-鿿]{2,4}$')
ANCHOR, STRIDE = 0x543e, 0x5d
KANSHOKU_END = 0x4382 + 80 * 0x2e   # 관직 테이블 끝 = 특기가 넘어설 수 없는 하한


def cstr(blob, off):
    end = blob.find(b'\x00', off)
    if end < 0:
        return None, len(blob)
    try:
        return blob[off:end].decode('cp932'), end + 1
    except UnicodeDecodeError:
        return None, end + 1


def probe(blob, off):
    name, nxt = cstr(blob, off)
    if name is None:
        return '<디코드실패>', None
    if not NAME_OK.match(name):
        return name, None
    reading, _ = cstr(blob, nxt)
    if reading and KATA.match(reading):
        return name, reading
    return name, None


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    out.write('# 관직 테이블 끝 = 0x%x → 특기 base는 이보다 커야 한다\n' % KANSHOKU_END)
    out.write('# 앵커 0x%x 에서 뒤로 걷기\n\n' % ANCHOR)
    n = 0
    first_ok = ANCHOR
    while True:
        n -= 1
        off = ANCHOR + n * STRIDE
        if off < 0:
            break
        name, reading = probe(blob, off)
        out.write('%3d  0x%04x  %-5s %-14s %s\n'
                  % (n, off, name, reading or '', '' if reading else '  ← 크립 실패'))
        if reading:
            first_ok = off
        if off < KANSHOKU_END:
            out.write('#   ↑ 관직 테이블 영역까지 내려왔다 — 여기서 멈춤\n')
            break
    out.write('\n# 크립이 선 가장 앞 = 0x%x\n' % first_ok)
    out.write('# 그 경우 특기 개수 = (0x7664 - 0x%x) / 0x5d = %s\n'
              % (first_ok, (0x7664 - first_ok) / STRIDE))
    out.close()


if __name__ == '__main__':
    main()
