# -*- coding: utf-8 -*-
import io, sys
sys.path.insert(0, 'analysis')
lines = io.open('work/e4_dict.tsv', encoding='utf-8').read().split('\n')
out = []
for ln in lines:
    p = ln.split('\t')
    if len(p) >= 5 and p[0] == '21' and p[1] == '168':
        p[4] = p[4].replace('자（자字）', '자')
        ln = '\t'.join(p)
    out.append(ln)
io.open('work/e4_dict.tsv', 'w', encoding='utf-8', newline='').write('\n'.join(out))
print('fixed')
