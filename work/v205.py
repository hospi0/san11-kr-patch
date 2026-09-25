# -*- coding: utf-8 -*-
import io, sys
sys.path.insert(0, 'analysis')
import e4_common as C
for p in C.read_tsv('work/e4_dict.tsv'):
    if p[0] == '21' and p[1] == '205':
        io.open('work/v205.txt', 'w', encoding='utf-8').write(p[4].replace('{N}', '\n'))
        break
print('done')
