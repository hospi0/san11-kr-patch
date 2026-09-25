# -*- coding: utf-8 -*-
"""시설(施設) DB 구조 규명 — 크립 기반 정밀 조사.

절대 stride를 추측으로 밀지 않는다. 대신:
  1. 헤더(0x00~0x60) 덤프 — 카운트/디렉토리 여부 확인
  2. 카타카나 읽기 런을 전부 찾는다(= 모든 레코드가 하나씩 가지는 앵커).
     각 읽기 앞뒤로 무엇이 오는지 관측 → 레코드 레이아웃 역산.
  3. SJIS 이름 후보(2자+널)와 설명문(긴 SJIS 런) 위치도 같이 표시.

사용: python tools/analysis/fac_probe.py [start_hex] [end_hex]
"""
import sys

PATH = "work/entry5.bin"
d = open(PATH, "rb").read()


def sjis_run(b, i):
    """i에서 시작하는 최대 SJIS 런(가이지 포함) 디코드. (문자열, 소비바이트)."""
    out, j = [], i
    while j < len(b) - 1:
        hi, lo = b[j], b[j + 1]
        if hi == 0:
            break
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); j += 2; continue
        try:
            ch = bytes([hi, lo]).decode("cp932")
        except Exception:
            break
        out.append(ch); j += 2
    return "".join(out), j - i


def is_kata(s):
    return s and all(0x30a0 <= ord(c) <= 0x30ff or c in "ー・" for c in s)


def hexdump(off, length):
    for r in range(off, off + length, 16):
        row = d[r:r + 16]
        hexs = " ".join("%02x" % x for x in row)
        # sjis-ish ascii
        asc = ""
        k = 0
        while k < len(row):
            hi = row[k]
            if 0x81 <= hi <= 0x9f or 0xe0 <= hi <= 0xf1:
                if k + 1 < len(row):
                    try:
                        asc += bytes(row[k:k + 2]).decode("cp932")
                    except Exception:
                        asc += ".."
                    k += 2
                    continue
            asc += chr(hi) if 0x20 <= hi < 0x7f else "."
            k += 1
        print("0x%04x  %-47s  %s" % (r, hexs, asc))


def main():
    if len(sys.argv) >= 3:
        start, end = int(sys.argv[1], 16), int(sys.argv[2], 16)
        hexdump(start, end - start)
        return

    print("=== 파일 크기 0x%04x (%d) ===\n" % (len(d), len(d)))
    print("=== 헤더 0x00~0x60 ===")
    hexdump(0x00, 0x60)

    print("\n=== 지명 테이블 끝(0xb82) 직전/직후 0xb60~0xc00 ===")
    hexdump(0xb60, 0xa0)

    # 모든 카타카나 읽기 런(길이>=2) 찾기 — 시설 DB 영역만(0xb82~)
    print("\n=== 카타카나 읽기 런 (0xb82~, 길이>=2) ===")
    i = 0xb82
    readings = []
    while i < len(d) - 1:
        s, n = sjis_run(d, i)
        if n >= 4 and is_kata(s):   # 카타카나 2자 이상
            readings.append((i, s, n))
            i += n
        else:
            i += 1
    print("총 %d개 카타카나 런" % len(readings))
    prev = None
    for off, s, n in readings[:80]:
        gap = "" if prev is None else "  (+0x%x=%d)" % (off - prev, off - prev)
        print("  0x%04x  %-20s len=%d%s" % (off, s, n, gap))
        prev = off


main()
