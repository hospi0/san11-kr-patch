# -*- coding: utf-8 -*-
"""번역문에서 사라진 `{01}S` 성격분기 헤더를 되살린다 (세션26).

`{01}S{V:c9}%3` = **성격별 대사 분기 셀렉터**다. 뒤따르는 `{05}{05}{05}`로 구분된 변형들 중
하나를 무장 성격으로 고른다. 이 헤더가 없으면 게임은 변형 묶음을 고를 근거를 잃는다.

blk1(진언·외교 대사)에서 61줄이 헤더 없이 나갔다. 61줄 전부 jp가 정확히 `{01}S{V:c9}%3`로
시작하므로 그 접두사만 되붙이면 원래 구조로 돌아온다(본문은 손대지 않는다).

⚠️이 검사는 「토큰 시퀀스 대조」로만 잡힌다 — 빌드도 되읽기도 통과하고, 화면에는 글자가
그럴듯하게 뜨기 때문에 눈으로는 못 찾는다.

Usage: python tools/fix_lost_s_header.py [--write]
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phrase_memory import split_tokens        # noqa: E402

HEAD = re.compile(r'^\{01\}S(?:\{V:[0-9a-f]{2,6}\}%\d+)?')


def main():
    write = '--write' in sys.argv
    total = 0
    for f in sorted(os.listdir('work')):
        if not (f.startswith('e4_') and f.endswith('.tsv')):
            continue
        path = os.path.join('work', f)
        raw = io.open(path, encoding='utf-8', newline='').read()
        lines = raw.split('\n')
        n = 0
        for i, ln in enumerate(lines):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
                continue
            jt, _ = split_tokens(p[3])
            kt, _ = split_tokens(p[4])
            if jt.count('{01}S') != 1 or kt.count('{01}S') != 0:
                continue
            m = HEAD.match(p[3])
            if not m:
                print('   ⚠️%s blk%s #%s: {01}S가 선두가 아니다 — 건너뛴다' % (f, p[0], p[1]))
                continue
            p[4] = m.group(0) + p[4]
            lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            n += 1
            if n <= 3:
                print('   %s blk%s #%s  +%r' % (f, p[0], p[1], m.group(0)))
        if n:
            total += n
            print('%s: %d줄' % (f, n))
            if write:
                bak = path + '.bak_shead'
                if not os.path.exists(bak):
                    io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
                io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print()
    print('%d줄 %s' % (total, '복원 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
