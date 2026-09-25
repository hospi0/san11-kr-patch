# -*- coding: utf-8 -*-
"""도시 42 · 관 10 · 항 35 = 87개 지명 한글 독음 번역본 생성.

이름은 레코드 앞의 고정폭 필드(都市 5B / 関·港 7B)에 SJIS로 들어있고,
한자 1자(2B) = 한글 1음절(2B)이므로 독음이 1:1이면 바이트 동일 패치가 된다.
가이지도 SJIS 2바이트라 마찬가지.

사용: python tools/translate_places.py work/places.tsv work/places_kr.tsv
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
    src = sys.argv[1] if len(sys.argv) > 1 else "work/places.tsv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/places_kr.tsv"

    out, warn = [], []
    for line in open(src, encoding="utf-8"):
        if line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        typ, off, nw, name, yomi = p[0], p[1], int(p[2]), p[3], p[4]

        j = restore_gaiji(name)
        if GAIJI_RE.search(j):
            warn.append((off, name, "미비정 가이지"))
            out.append((typ, off, j, yomi, "", "미비정 가이지"))
            continue

        k = PLACE_OVERRIDES.get(j) or to_hangul(j)

        note = ""
        if len(k) != len(j):
            note = "길이 불일치 %d→%d" % (len(j), len(k))
        else:
            bad = [c for c in k if not ("가" <= c <= "힣")]
            if bad:
                note = "독음실패 " + "".join(bad)
        # 바이트 예산: 한글 n자 = 2n B, 필드는 nw-1 B까지 (종료자 1B)
        if len(k) * 2 > nw - 1:
            note = (note + " / " if note else "") + "필드초과 %dB > %dB" % (len(k) * 2, nw - 1)
        if note:
            warn.append((off, j, k, note))

        out.append((typ, off, j, yomi, k, note))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("# 종류\toffset\t원문\t読み\t한글\t비고\n")
        for r in out:
            f.write("\t".join(r) + "\n")

    print("%s 저장: %d개, 경고 %d건" % (dst, len(out), len(warn)))
    for w in warn:
        print("   ", w)


main()
