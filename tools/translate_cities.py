# -*- coding: utf-8 -*-
"""도시·관·항·주 97개 한글 독음 번역본 생성.

도시 테이블은 연속 SJIS(패딩 없음)라 이름 바이트 길이가 곧 제약이다.
한자 1자(2B) = 한글 1음절(2B)이므로 독음이 1:1이면 바이트 동일 패치가 된다.
가이지도 SJIS 2바이트라 마찬가지.

사용: python tools/translate_cities.py work/cities.txt work/cities_kr.tsv
"""
import re, sys, hanja
from gaiji_map import GAIJI_MAP
from name_overrides import HANJA_OVERRIDES
from place_overrides import PLACE_OVERRIDES

GAIJI_RE = re.compile(r"\[G(f0[0-9a-f]{2}|f1[0-9a-f]{2})\]")


def restore_gaiji(s):
    return GAIJI_RE.sub(lambda m: GAIJI_MAP.get(int(m.group(1), 16), m.group(0)), s)


def to_hangul(s):
    out = hanja.translate(s, "substitution")
    if len(out) != len(s):
        return out
    for h, ko in HANJA_OVERRIDES.items():
        if h in s:
            out = "".join(ko if s[i] == h else out[i] for i in range(len(s)))
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "work/cities.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/cities_kr.tsv"

    out, warn = [], []
    for line in open(src, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3:
            continue
        off, typ, name = p[0], p[1], p[2]
        yomi = p[3] if len(p) > 3 else ""

        j = restore_gaiji(name)
        if GAIJI_RE.search(j):
            warn.append((off, name, "미비정 가이지"))
            out.append((off, typ, j, yomi, "", "미비정 가이지"))
            continue

        k = PLACE_OVERRIDES.get(j) or to_hangul(j)

        note = ""
        if len(k) != len(j):
            note = "길이 불일치 %d→%d" % (len(j), len(k))
            warn.append((off, j, note))
        bad = [c for c in k if not ("가" <= c <= "힣")]
        if bad:
            note = "독음실패 " + "".join(bad)
            warn.append((off, j, note))

        out.append((off, typ, j, yomi, k, note))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("# offset\t종류\t원문\t読み\t한글\t비고\n")
        for r in out:
            f.write("\t".join(r) + "\n")

    print("%s 저장: %d개" % (dst, len(out)))
    print("경고 %d건" % len(warn))
    for w in warn:
        print("   ", w)


main()
