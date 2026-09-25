# -*- coding: utf-8 -*-
"""시설 효과 설명 추출 — 스탯 바이트 앞붙음 대응 견고판.

문제: 설명 앞에 스탯 바이트가 있어 시작점이 어긋나거나(市場→場), \\0 미접이라
     놓친다. 해결: 위치 p가 '진짜 시작'인지 = **직전 2바이트가 일본어 글자를
     이루지 않으면**(스탯/제어/\\0) 시작으로 본다.
"""
import sys

ent = open("work/entry5.bin", "rb").read()


def is_jp_char(b0, b1):
    """2바이트가 SJIS 일본어 1글자(한자·가나·구두점·전각)면 True."""
    if b0 == 0:
        return False
    try:
        ch = bytes([b0, b1]).decode("cp932")
    except Exception:
        return False
    if len(ch) != 1:
        return False
    o = ord(ch)
    return (0x3040 <= o <= 0x30ff or 0x4e00 <= o <= 0x9fff
            or 0x3000 <= o <= 0x303f or 0xff00 <= o <= 0xffef or o == 0x3005)


def sjis_run(i):
    out, j, hira, kana = [], i, 0, 0
    while j < len(ent) - 1:
        b0, b1 = ent[j], ent[j + 1]
        if b0 == 0:
            break
        if 0xf0 <= b0 <= 0xf1:
            out.append("[G%02x%02x]" % (b0, b1)); j += 2; continue
        try:
            ch = bytes([b0, b1]).decode("cp932")
        except Exception:
            return None, 0, 0, 0
        if len(ch) != 1:
            return None, 0, 0, 0
        o = ord(ch)
        if 0x3040 <= o <= 0x309f:
            hira += 1
        if 0x30a0 <= o <= 0x30ff:
            kana += 1
        out.append(ch); j += 2
    return "".join(out), j - i, hira, kana


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x2000
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x3000
    rows = []
    i = lo
    while i < hi:
        if ent[i] == 0:
            i += 1; continue
        # 진짜 시작? 직전 2바이트가 일본어 글자면 mid-string
        if i >= 2 and is_jp_char(ent[i - 2], ent[i - 1]):
            i += 1; continue
        s, nb, hira, kana = sjis_run(i)
        if s is None:
            i += 1; continue
        n_chars = len([c for c in s if not c.startswith("[")])
        if nb >= 10 and hira >= 2 and n_chars >= 5 and hira >= kana:
            slack = 0
            k = i + nb
            while k < len(ent) and ent[k] == 0:
                slack += 1; k += 1
            rows.append((i, s, nb, slack))
            i += nb
        else:
            i += 1
    print("설명 %d개 (0x%04x~0x%04x)\n" % (len(rows), lo, hi))
    for off, s, nb, slack in rows:
        print("  0x%04x  %2dB +슬랙%d  %s" % (off, nb, slack, s))


main()
