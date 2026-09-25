# -*- coding: utf-8 -*-
import io
lines = io.open('work/e4_dict.tsv', encoding='utf-8').read().split('\n')
out = []
for ln in lines:
    p = ln.split('\t')
    if len(p) >= 5 and p[0] == '21' and p[1] == '345':
        p[4] = p[4].replace('「눈(雪)」', '「눈」')
        ln = '\t'.join(p)
    out.append(ln)
io.open('work/e4_dict.tsv', 'w', encoding='utf-8', newline='').write('\n'.join(out))
print('fixed')
