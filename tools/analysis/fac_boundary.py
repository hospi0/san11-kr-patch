# -*- coding: utf-8 -*-
"""시설 레코드 경계 불변식 찾기 — 각 이름\\0 앞뒤 컨텍스트 전수 비교.

추측 stride 금지. 확정된 시설명(name\\0 정확일치)마다 앞 12B·뒤 20B를 보여줘
'레코드 시작' 공통 시그니처가 있는지 육안·통계로 확인한다.
"""
import sys
from collections import Counter

d = open("work/entry5.bin", "rb").read()

FAC = ["都市", "関所", "陣", "港", "城塞", "連弩櫓", "砦", "石壁", "太鼓台",
       "弓櫓", "石兵八陣", "根城", "土塁", "火炎種", "火炎球", "投石台",
       "業火球", "落石", "軍楽台", "浅瀬", "長城", "廟", "市場", "農場"]


def sjis_at(b, i, n=12):
    out, j = [], i
    while j < len(b) - 1 and len(out) < n:
        hi, lo = b[j], b[j + 1]
        if hi == 0:
            out.append("\\0"); j += 1; continue
        if 0xf0 <= hi <= 0xf1:
            out.append("[G]"); j += 2; continue
        try:
            ch = bytes([hi, lo]).decode("cp932")
            if len(ch) == 1 and (ch.isprintable()):
                out.append(ch); j += 2; continue
        except Exception:
            pass
        out.append("."); j += 1
    return "".join(out)


def main():
    rows = []
    for nm in FAC:
        pat = nm.encode("cp932") + b"\x00"
        p = d.find(pat, 0xb82)
        if 0xb82 <= p < 0x2200:
            rows.append((p, nm))
    rows.sort()

    print("시설명 %d개, 앞 8B(hex) | 이름 | 뒤 16B(hex)\n" % len(rows))
    before2 = Counter()
    for p, nm in rows:
        pre = d[p - 8:p]
        post = d[p + len(nm.encode('cp932')) + 1:p + len(nm.encode('cp932')) + 1 + 16]
        before2[d[p - 2:p].hex()] += 1
        print("  0x%04x  %-18s | %-6s | %s"
              % (p, " ".join("%02x" % x for x in pre), nm,
                 " ".join("%02x" % x for x in post)))

    print("\n이름 직전 2바이트 분포:", before2.most_common())

    # 이름\0 뒤에 곧바로(<=2B) 카타카나 읽기가 오는가?
    print("\n이름\\0 뒤 곧 카타카나 여부:")
    for p, nm in rows:
        after = p + len(nm.encode('cp932')) + 1
        b0, b1 = d[after], d[after + 1]
        iskata = b0 == 0x83
        print("  %-6s 뒤: %02x %02x  %s" % (nm, b0, b1, "카타카나?" if iskata else ""))


main()
