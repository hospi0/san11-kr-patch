# -*- coding: utf-8 -*-
"""시설 DB 레코드 경계 = 마커 `fe ff ff ff ff` 전수 스캔.

stride를 추측하지 않는다. 관측된 반복 구분자 `fe ff ff ff ff [type] 01 02 00 00`을
전수로 찾아 레코드 경계를 확정하고, 각 레코드의 이름/읽기/설명을 뽑는다.
"""
import sys

PATH = "work/entry5.bin"
d = open(PATH, "rb").read()
MARK = bytes.fromhex("feffffffff")


def sjis_run(b, i, maxlen=400):
    out, j = [], i
    while j < len(b) - 1 and (j - i) < maxlen:
        hi, lo = b[j], b[j + 1]
        if hi == 0:
            break
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); j += 2; continue
        try:
            out.append(bytes([hi, lo]).decode("cp932")); j += 2
        except Exception:
            break
    return "".join(out), j - i


def main():
    # 모든 마커 위치
    marks = []
    i = 0
    while True:
        p = d.find(MARK, i)
        if p < 0:
            break
        marks.append(p)
        i = p + 1
    print("마커 `fe ff ff ff ff` 총 %d개" % len(marks))
    print("첫 마커 0x%04x, 마지막 0x%04x\n" % (marks[0], marks[-1]))

    # 마커 간 간격 분포
    gaps = [marks[k + 1] - marks[k] for k in range(len(marks) - 1)]
    from collections import Counter
    print("간격 분포(top): %s" % Counter(gaps).most_common(12))
    print("간격 min=%d max=%d\n" % (min(gaps), max(gaps)))

    # 각 마커 뒤 type 바이트 + 그 다음 9바이트
    print("=== 마커별 뒤따르는 바이트 (앞 40개) ===")
    for p in marks[:40]:
        tail = d[p + 5:p + 5 + 10]
        print("  0x%04x  type=%02x  next=%s" % (
            p, tail[0], " ".join("%02x" % x for x in tail)))


main()
