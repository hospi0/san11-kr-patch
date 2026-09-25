# -*- coding: utf-8 -*-
"""이미 번역된 e4_*.tsv에서 **조각 대응 사전**(일본어→한국어)을 뽑는다 (세션26).

왜
  세션26에 되살린 130줄은 대부분 「不覚！」「感謝！」처럼 **다른 줄에서 이미 번역된 문장**이다.
  같은 문장을 새로 번역하면 표현이 흔들린다(같은 전법 대사가 화면마다 다른 말이 된다).
  그래서 기존 번역에서 대응을 캐내 재사용하고, **정말 처음 보는 조각만** 손으로 번역한다.

방법
  jp와 kr을 **토큰 시퀀스**로 잘라, 토큰열이 완전히 같은 줄만 채택한다(구조가 같아야 조각이
  1:1로 맞는다). 토큰 사이의 텍스트 조각끼리 짝지어 카운트하고, 최빈값을 사전으로 삼는다.
  ⚠️토큰열이 다른 줄은 버린다 — 억지로 맞추면 엉뚱한 대응이 섞인다.

Usage:  from phrase_memory import build_memory
"""
import io
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# help_codec.TOKEN_RE와 **같은 문법**이어야 한다(자체 정규식은 `{04}{%20`의 리터럴 `{`에 걸린다).
TOKEN_RE = re.compile(
    r"\{(?:V:[0-9a-f]{2,6}|N|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")
# `{01}C`/`{01}J` + 인수 2개는 통째로 하나의 토큰처럼 다룬다.
MACRO_RE = re.compile(r"\{01\}[CJ](?:\{[0-9a-f]{2}\}|[^{])(?:\{[0-9a-f]{2}\}|[^{])?")
HEAD_RE = re.compile(r"\{01\}S")

# 조각 앞머리에 붙는 **조건식 파편**. `{04}{V:0a4b}{04}=660兵が…` 의 `=660` 처럼 토큰이 아니라
# 평문으로 남는다. 떼어내지 않으면 같은 대사가 조건값마다 다른 조각으로 갈려 사전이 안 모인다.
# ⚠️루비 마커(`1x董卓`)는 건드리면 안 되므로 `[=%+]숫자` 와 `}|&` 만 뗀다.
COND_RE = re.compile(r"^(?:[=%+][0-9]+|[}|&])*")


def peel(s):
    """조각 -> (조건식 앞머리, 순수 텍스트). 사전 구축과 적용이 **같은 함수**를 써야 한다.

    ★NFC로 정규화한다 — 디코더는 탁점을 별도 문자로 낸다(じ = し+U+3099). 손으로 적은
      사전 파일은 NFC라, 정규화를 안 맞추면 `しくじった` 같은 흔한 조각이 통째로 매칭에
      실패한다(세션26에 실제로 240개 중 절반이 조용히 빗나갔다).
    """
    s = unicodedata.normalize('NFC', s)
    m = COND_RE.match(s)
    return s[:m.end()], s[m.end():]


def split_tokens(s):
    """(토큰열, 조각열) — 조각 개수는 토큰 개수 + 1."""
    toks, parts, pos, last = [], [], 0, 0
    while pos < len(s):
        m = MACRO_RE.match(s, pos) or HEAD_RE.match(s, pos) or TOKEN_RE.match(s, pos)
        if m:
            parts.append(s[last:m.start()])
            toks.append(m.group(0))
            pos = last = m.end()
            continue
        pos += 1
    parts.append(s[last:])
    return toks, parts


def build_memory(paths=None):
    """{jp조각: kr조각}. 빈 조각과 일본어가 없는 조각은 뺀다."""
    if paths is None:
        paths = ['work/' + f for f in sorted(os.listdir('work'))
                 if f.startswith('e4_') and f.endswith('.tsv')]
    pair = defaultdict(Counter)
    for path in paths:
        for ln in io.open(path, encoding='utf-8'):
            p = ln.rstrip('\n').rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
                continue
            jt, jp_parts = split_tokens(p[3])
            kt, kr_parts = split_tokens(p[4])
            if jt != kt:                       # 구조가 다르면 조각을 못 믿는다
                continue
            for a, b in zip(jp_parts, kr_parts):
                pa, a = peel(a.strip())
                pb, b = peel(b.strip())
                if pa != pb:                   # 조건식이 다르면 짝이 어긋난 것이다
                    continue
                if a and b and a != b:
                    pair[a][b] += 1
    return {a: c.most_common(1)[0][0] for a, c in pair.items()}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    mem = build_memory()
    print('조각 사전 %d개' % len(mem))
    for a, b in list(mem.items())[:25]:
        print('   %-28r -> %r' % (a, b))
