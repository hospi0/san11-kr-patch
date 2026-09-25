# -*- coding: utf-8 -*-
import io, re, sys
sys.path.insert(0, 'analysis')
import e4_common as C
for p in C.read_tsv('work/e4_dict.tsv'):
    if p[0] == '22' and p[1] == '139':
        jp = p[3]
        break

parts = re.split(r'((?:\{05\})+)', jp)
print('parts:', len(parts))
for i, pt in enumerate(parts):
    print('--- %d (%d chars) ---' % (i, len(pt)))
    print(pt[:60], '...' if len(pt) > 60 else '')
io.open('work/v139_full.txt', 'w', encoding='utf-8').write(
    '\n\n=====SPLIT=====\n\n'.join(parts))
