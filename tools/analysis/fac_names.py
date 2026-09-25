# -*- coding: utf-8 -*-
"""시설/병장/관직 이름 전수 검출 — 인접 크립 방식.

레코드 stride를 추측하지 않는다. 대신 이 DB의 불변 패턴을 앵커로 쓴다:
    [한자·한글자 이름 SJIS 런] 00 [카타카나 읽기 런] 00
이름 바로 뒤에 그 읽기가 붙는다는 관례는 지명 테이블에서도 성립했고,
설명문(히라가나 섞임)이나 스탯 바이너리는 이 패턴을 만들지 못한다.

각 이름의 오프셋·바이트폭을 뽑아 in-place 패치 예산을 확정한다.
"""
import sys

PATH = "work/entry5.bin"
d = open(PATH, "rb").read()


def is_name_char(hi, lo):
    """이름에 허용: SJIS 한자/전각영숫자/가이지. (히라가나·카타카나 제외)"""
    if 0xf0 <= hi <= 0xf1:
        return "gaiji"
    try:
        ch = bytes([hi, lo]).decode("cp932")
    except Exception:
        return None
    if len(ch) != 1:
        return None
    o = ord(ch)
    # 한자(CJK), 전각 영숫자·기호는 이름에 올 수 있음. 가나는 이름 아님(읽기 필드).
    if 0x3040 <= o <= 0x30ff:   # 히라가나·카타카나
        return None
    if 0x4e00 <= o <= 0x9fff:   # CJK
        return "kanji"
    if o in (0x3005,):          # 々
        return "kanji"
    if 0xff00 <= o <= 0xffef:   # 전각 영숫자
        return "full"
    return None


def read_kanji_name(i):
    """i에서 한자 이름 런. (문자열, 바이트수, 한자수) 또는 None."""
    out, j, cnt = [], i, 0
    while j < len(d) - 1:
        r = is_name_char(d[j], d[j + 1])
        if r is None:
            break
        if r == "gaiji":
            out.append("[G%02x%02x]" % (d[j], d[j + 1]))
        else:
            out.append(bytes([d[j], d[j + 1]]).decode("cp932"))
        j += 2; cnt += 1
    return ("".join(out), j - i, cnt) if cnt else None


def read_kata(i):
    """i에서 카타카나 읽기 런. (문자열, 바이트수) 또는 None."""
    out, j = [], i
    while j < len(d) - 1:
        hi, lo = d[j], d[j + 1]
        try:
            ch = bytes([hi, lo]).decode("cp932")
        except Exception:
            break
        if len(ch) != 1:
            break
        if 0x30a0 <= ord(ch) <= 0x30ff or ch in "ー・":
            out.append(ch); j += 2
        else:
            break
    return ("".join(out), j - i) if out else None


def main():
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xb82
    hits = []
    i = start
    while i < len(d) - 4:
        nm = read_kanji_name(i)
        if nm and nm[2] >= 1 and d[i + nm[1]] == 0:
            kpos = i + nm[1] + 1
            kt = read_kata(kpos)
            if kt and d[kpos + kt[1]] == 0:
                hits.append((i, nm[0], nm[1], kt[0], kt[1]))
                i = kpos + kt[1] + 1
                continue
        i += 1

    print("이름+읽기 인접 히트 %d개 (start=0x%04x)\n" % (len(hits), start))
    prev = None
    for off, nm, nb, kt, kb in hits:
        gap = "" if prev is None else "  Δ0x%x" % (off - prev)
        print("  0x%04x  %-10s (%dB) / %-14s%s" % (off, nm, nb, kt, gap))
        prev = off


main()
