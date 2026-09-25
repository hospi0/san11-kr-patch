# -*- coding: utf-8 -*-
"""인칭·호칭 매크로 뒤 **서술격조사 '이-'** 정합 (2026-07-20 세션23).

## 문제
`fix_macro_josa.py` 는 주격·목적격만 봤다. 사용자가 실기에서 「소인다」를 발견 —
서술격조사 '이다'의 '이'가 빠진 것이다. 같은 부류가 더 있다:
  소인다 → 소인이다 / 님라면 → 님이라면 / 님여 → 님이여 / 님야말로 → 님이야말로

받침류 매크로(소인·짐·님·공…)는 '이-'가 필요하고, 모음류(우리·그대·너)는 붙이면 안 된다.
부류 판정 근거는 [[fix_macro_josa]] 와 같다(entry3 번역 후보 전수 덤프).

## ⚠️건드리면 안 되는 것
  `{매크로}다운`  = 「님다운 배려」 — 형용사 '답다'의 활용이지 서술격조사가 아니다.
  `{매크로}들`    = 복수 접미사.
긴 것부터 적용해야 `라면`이 `라`에 먼저 안 먹힌다.

사용: python analysis/fix_macro_copula.py [--dry]
"""
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ('e4_dialogue.tsv', 'e4_kessen.tsv', 'e4_tutorial.tsv',
         'e4_bio.tsv', 'e4_sys.tsv', 'e4_dict.tsv')

BATCHIM = ['{01}C{00}{00}', '{01}C{0e}{00}', '{01}CC{00}',
           '{01}CE{00}', '{01}CY{00}', '{01}Ck{00}']
VOWEL = ['{01}C{07}{00}', '{01}C#{00}', '{01}C4{00}']

# 받침류: '이' 를 넣는다. (긴 것 먼저)
ADD = ['야말로', '라면', '라도', '라', '여', '다']
# 모음류: 잘못 들어간 '이' 를 뺀다.
DEL = ['이야말로', '이라면', '이라도', '이라', '이여', '이다']
# '다'로 시작하지만 서술격조사가 아닌 것 → 제외
SKIP_AFTER_DA = ('운', '오')     # 다운(답다), 다오


def main():
    dry = '--dry' in sys.argv
    stat = Counter()
    total = 0
    for fn in FILES:
        path = os.path.join(REPO, 'work', fn)
        if not os.path.exists(path):
            continue
        lines = open(path, encoding='utf-8').read().split('\n')
        n = 0
        for i, line in enumerate(lines):
            cols = line.split('\t')
            if len(cols) < 5:
                continue
            kr = orig = cols[4]
            for mac in BATCHIM:
                for t in ADD:
                    pat = mac + t
                    st = 0
                    while True:
                        k = kr.find(pat, st)
                        if k < 0:
                            break
                        nxt = kr[k + len(pat):k + len(pat) + 1]
                        if t == '다' and nxt in SKIP_AFTER_DA:
                            st = k + 1
                            continue
                        kr = kr[:k] + mac + '이' + t + kr[k + len(pat):]
                        st = k + len(mac) + 1 + len(t)
                        stat[(mac, t, '+이')] += 1
                        n += 1
            for mac in VOWEL:
                for t in DEL:
                    pat = mac + t
                    while pat in kr:
                        kr = kr.replace(pat, mac + t[1:], 1)
                        stat[(mac, t, '-이')] += 1
                        n += 1
            if kr != orig:
                cols[4] = kr
                lines[i] = '\t'.join(cols)
        if n and not dry:
            bak = path + '.bak_copula'
            if not os.path.exists(bak):
                open(bak, 'w', encoding='utf-8').write(
                    open(path, encoding='utf-8').read())
            open(path, 'w', encoding='utf-8').write('\n'.join(lines))
        if n:
            print('%-20s %3d곳' % (fn, n))
        total += n
    print()
    for (mac, t, how), k in stat.most_common():
        print('  %s + %-5s %s   %d회' % (mac, t, how, k))
    print('\n합계 %d곳%s' % (total, ' (dry)' if dry else ''))


if __name__ == '__main__':
    main()
