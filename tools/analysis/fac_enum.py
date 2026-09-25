# -*- coding: utf-8 -*-
"""시설 레코드 전수 열거 — 이름 필드 후보를 빠짐없이.

레코드는 name\\0로 시작(변길이 ~94B). 누락 방지를 위해 구역 0xb82~end에서
'CJK 2~8자 + \\0' 이면서 '직전이 \\0 또는 스탯 경계'인 위치를 전부 찾는다.
그다음 육안으로 진짜 이름 vs 설명 조각을 가른다.
"""
import sys

d = open("work/entry5.bin", "rb").read()


def read_cjk(i):
    """i에서 CJK/가이지 이름 런. (문자열, 바이트수, 글자수)."""
    out, j, cnt = [], i, 0
    while j < len(d) - 1:
        hi, lo = d[j], d[j + 1]
        if hi == 0:
            break
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); j += 2; cnt += 1; continue
        try:
            ch = bytes([hi, lo]).decode("cp932")
        except Exception:
            break
        if len(ch) != 1:
            break
        o = ord(ch)
        if 0x4e00 <= o <= 0x9fff or o == 0x3005:      # CJK만(가나·기호 제외)
            out.append(ch); j += 2; cnt += 1
        else:
            break
    return "".join(out), j - i, cnt


def main():
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xb82
    end = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1e00
    hits = []
    i = start
    while i < end:
        nm, nb, cnt = read_cjk(i)
        # 이름 후보: 2~8바이트(1~4자) CJK + 뒤 \0 + 직전이 \0 또는 구역시작
        if 1 <= cnt <= 4 and i + nb < len(d) and d[i + nb] == 0:
            prev = d[i - 1] if i > 0 else 0
            hits.append((i, nm, nb, cnt, prev))
        i += 1

    print("이름 후보 %d개 (0x%04x~0x%04x)\n" % (len(hits), start, end))
    prev_off = None
    for off, nm, nb, cnt, prev in hits:
        gap = "" if prev_off is None else " Δ%d" % (off - prev_off)
        pmark = "직전\\0" if prev == 0 else "직전%02x" % prev
        print("  0x%04x  %-10s %dB  [%s]%s" % (off, nm, nb, pmark, gap))
        prev_off = off


main()
