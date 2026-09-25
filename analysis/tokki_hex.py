"""특기 구역 원바이트를 오프셋·해석 붙여 덤프한다(포맷 해독용).

추측 금지: stride를 가정하지 않고 바이트를 그대로 찍어서 눈으로 경계를 잡는다.
"""
import io
import os
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')


def dump(blob, lo, hi, out):
    for base in range(lo, hi, 16):
        row = blob[base:base + 16]
        hexs = ' '.join('%02x' % b for b in row)
        try:
            txt = row.decode('cp932', errors='replace')
        except Exception:
            txt = ''
        txt = ''.join(ch if ch.isprintable() else '.' for ch in txt)
        out.write('%06x  %-47s  %s\n' % (base, hexs, txt))


def main():
    lo = int(sys.argv[2], 16)
    hi = int(sys.argv[3], 16)
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    dump(blob, lo, hi, out)
    out.close()


if __name__ == '__main__':
    main()
