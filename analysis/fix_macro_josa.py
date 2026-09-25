# -*- coding: utf-8 -*-
"""인칭·호칭 매크로 뒤 조사를 **매크로의 받침 부류**에 맞춘다 (2026-07-20 세션23).

## 문제
사용자가 실기에서 「소인가」를 발견했다. `{01}C{00}{00}` 은 화자에 따라
「소인/이몸/소첩/짐/과인」으로 런타임에 바뀌는 1인칭 매크로인데, 번역문이 그 뒤에
`가`를 붙여놨다. 이 부류는 **전부 받침으로 끝나므로** `이`가 맞다.

## 왜 병기(이(가))로 안 푸는가
943곳을 병기로 바꾸면 약 3.8KB가 늘어나는데 entry4 여유는 644B뿐이다.
그런데 **애초에 병기가 필요 없다** — `build_help.PART1_WORD_REPL` 이 매크로별로
후보 단어를 **같은 받침 부류로 통일**해 놨기 때문이다(그 파일 주석에 설계가 적혀 있다).
부류에 맞는 홑조사를 쓰면 되고, **글자 수가 같아 바이트도 안 늘어난다**.

## 부류 (work/entry3.bin 의 실제 번역 후보를 전수 덤프해 확인, 추측 아님)
  받침류(이/은/을/과/으로): C{00}=소인·이몸·소첩·짐·과인 / C{0e}=님·공·귀공 /
                            CC=분·사람 / CE·CY·Ck=님·공(+1인칭 분기)
  모음류(가/는/를/와/로)  : C{07}=우리·저희 / C#=그대 / C4=너
  ⚠️C{0f}·C$ 는 **혼재**(형님·숙모님 같은 받침류와 그대가 섞임) → 손대지 않는다.
     이 둘만은 병기가 유일한 해법이지만 빈도가 낮아 보류.

사용: python analysis/fix_macro_josa.py [--dry]
"""
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BATCHIM = ['{01}C{00}{00}', '{01}C{0e}{00}', '{01}CC{00}',
           '{01}CE{00}', '{01}CY{00}', '{01}Ck{00}']
VOWEL = ['{01}C{07}{00}', '{01}C#{00}', '{01}C4{00}']

# 잘못된 조사 -> 맞는 조사
TO_BATCHIM = {'가': '이', '는': '은', '를': '을', '와': '과', '로': '으로'}
TO_VOWEL = {'이': '가', '은': '는', '을': '를', '과': '와', '으로': '로'}

FILES = ('e4_dialogue.tsv', 'e4_kessen.tsv', 'e4_tutorial.tsv',
         'e4_bio.tsv', 'e4_sys.tsv', 'e4_dict.tsv')


def build_pats():
    pats = []
    for group, table in ((BATCHIM, TO_BATCHIM), (VOWEL, TO_VOWEL)):
        for mac in group:
            for bad, good in table.items():
                # 이미 병기된 것(이(가))은 건드리지 않는다 → 뒤에 '(' 가 오면 제외
                pats.append((re.compile(re.escape(mac) + bad + r'(?!\()'),
                             mac + good, mac, bad, good))
    return pats


def main():
    dry = '--dry' in sys.argv
    pats = build_pats()
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
            kr = cols[4]
            for pat, rep, mac, bad, good in pats:
                kr, k = pat.subn(rep, kr)
                if k:
                    stat[(mac, bad, good)] += k
                    n += k
            if kr != cols[4]:
                cols[4] = kr
                lines[i] = '\t'.join(cols)
        if n and not dry:
            bak = path + '.bak_josa'
            if not os.path.exists(bak):
                open(bak, 'w', encoding='utf-8').write(
                    open(path, encoding='utf-8').read())
            open(path, 'w', encoding='utf-8').write('\n'.join(lines))
        print('%-20s %4d곳' % (fn, n))
        total += n
    print()
    for (mac, bad, good), k in stat.most_common():
        print('  %s  %s -> %s   %d회' % (mac, bad, good, k))
    print('\n합계 %d곳%s' % (total, ' (dry)' if dry else ''))


if __name__ == '__main__':
    main()
