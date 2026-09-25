# -*- coding: utf-8 -*-
"""시설 레코드 시작 = 이름\\0 + (스탯 ≤10B) + 카타카나 읽기(≥3자).

설명문 조각(制限·増加 등)은 이 패턴을 못 만든다(뒤에 자기 읽기가 안 옴).
1글자 시설도 읽기가 뒤따르면 진짜. 2벌(본편/PUK) 다 잡는다.
"""
import sys

d = open("work/entry5.bin", "rb").read()


def read_cjk(i):
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
        if 0x4e00 <= o <= 0x9fff or o == 0x3005:
            out.append(ch); j += 2; cnt += 1
        else:
            break
    return "".join(out), j - i, cnt


def kata_within(after, window=12):
    """after부터 window 안에서 카타카나 런(≥3자) 시작하면 (읽기, 시작오프셋)."""
    for s in range(after, after + window):
        # 카타카나 런 읽기
        out, j = [], s
        while j < len(d) - 1:
            hi, lo = d[j], d[j + 1]
            try:
                ch = bytes([hi, lo]).decode("cp932")
            except Exception:
                break
            if len(ch) == 1 and (0x30a0 <= ord(ch) <= 0x30ff or ch in "ー・"):
                out.append(ch); j += 2
            else:
                break
        if len(out) >= 3:
            return "".join(out), s
    return None, -1


def main():
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xb82
    end = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1e00
    recs = []
    i = start
    while i < end:
        nm, nb, cnt = read_cjk(i)
        if 1 <= cnt <= 4 and i + nb < len(d) and d[i + nb] == 0:
            yomi, ypos = kata_within(i + nb + 1)
            if yomi:
                recs.append((i, nm, nb, yomi))
                i = i + nb          # 이름 소비(겹침 방지)
                continue
        i += 1

    print("시설 레코드 %d개 (0x%04x~0x%04x)\n" % (len(recs), start, end))
    prev = None
    from collections import Counter
    names = Counter()
    for off, nm, nb, yomi in recs:
        gap = "" if prev is None else " Δ%d" % (off - prev)
        names[nm] += 1
        print("  0x%04x  %-10s %dB / %-14s%s" % (off, nm, nb, yomi[:14], gap))
        prev = off
    print("\n고유 시설 %d종:" % len(names))
    print("  ", dict(names))


main()
