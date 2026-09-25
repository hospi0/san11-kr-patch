# -*- coding: utf-8 -*-
"""깨진 줄바꿈 토큰(`N}` / `{N}}`)을 고친다 (세션26).

증상(실기 제보): 대사창에 「일리가 있군요N)각자가…」, 「…하아아N)창밖의…」처럼
**토큰이 글자로 새어 나온다**. 원인은 번역할 때 여는 중괄호를 빠뜨린 단순 오타다.
`{N}`이어야 할 것이 `N}`으로 남으면 인코더는 그냥 ASCII 'N' + '}' 를 찍는다.

빌드도 되읽기도 통과한다 — 바이트로는 멀쩡한 문자열이기 때문. **실기에서만 드러난다.**

Usage: python tools/fix_broken_ntoken.py [--write]
"""
import io
import os
import re
import sys

BAD_N = re.compile(r'(?<!\{)N\}')


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
            kr = p[4]
            new = BAD_N.sub('{N}', kr).replace('{N}}', '{N}')
            if new == kr:
                continue
            # ★jp의 줄바꿈 개수와 맞는지 대조 — 고치고 나면 같아야 정상이다.
            nj, nk = p[3].count('{N}'), new.count('{N}')
            print('%s blk%s #%s   {N} jp=%d kr=%d %s' % (f, p[0], p[1], nj, nk,
                                                         '' if nj == nk else '⚠️개수 불일치'))
            print('   전: %s' % kr[:150])
            print('   후: %s' % new[:150])
            p[4] = new
            lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            n += 1
        if n:
            total += n
            if write:
                bak = path + '.bak_ntoken'
                if not os.path.exists(bak):
                    io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
                io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print()
    print('%d줄 %s' % (total, '수정 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
