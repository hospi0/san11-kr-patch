# -*- coding: utf-8 -*-
"""block22 idx 25~110 = 순수 숫자/{V:96}하이라이트 패턴(번역할 일본어 텍스트 없음).
   kr = jp 그대로 채워 '번역 완료'로 표시(원문 그대로가 곧 정답)."""
import io
import sys

sys.path.insert(0, 'analysis')
import e4_common as C

lines = io.open('work/e4_dict.tsv', encoding='utf-8').read().split('\n')
out, n = [], 0
for ln in lines:
    p = ln.split('\t')
    if len(p) >= 5 and p[0] == '22' and p[1].isdigit():
        idx = int(p[1])
        if 25 <= idx <= 110 and not p[4].strip():
            if not C.residual_jp(p[3]):
                p[4] = p[3]
                ln = '\t'.join(p)
                n += 1
    out.append(ln)

io.open('work/e4_dict.tsv', 'w', encoding='utf-8', newline='').write('\n'.join(out))
print('%d개 패스스루 채움' % n)
