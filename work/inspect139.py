# -*- coding: utf-8 -*-
import io, re, sys
sys.path.insert(0, 'analysis')
import e4_common as C
for p in C.read_tsv('work/e4_dict.tsv'):
    if p[0] == '22' and p[1] == '139':
        jp = p[3]
        break

# {05}{05}{05}... 런으로 쪼갠다
parts = re.split(r'(\{05\}+)', jp)
io.open('work/v139_parts.txt', 'w', encoding='utf-8').write(
    '\n\n=====SPLIT=====\n\n'.join(parts))
print('parts:', len(parts))
for i, pt in enumerate(parts):
    print(i, repr(pt[:80]))
