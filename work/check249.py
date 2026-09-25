# -*- coding: utf-8 -*-
import io, sys
sys.path.insert(0, 'analysis')
import e4_common as C
for p in C.read_tsv('work/e4_dict.tsv'):
    if p[0] == '22' and p[1] == '249':
        io.open('work/v249.txt', 'w', encoding='utf-8').write(p[3])
        break
print('ok')
