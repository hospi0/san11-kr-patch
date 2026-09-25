# -*- coding: utf-8 -*-
import io, sys
sys.path.insert(0, 'analysis')
import e4_common as C
rows = {(r[0], r[1]): r[3] for r in C.read_tsv('work/e4_dict.tsv')}
for idx in ['267','268','269','270','271','272','274']:
    jp = rows[('22', idx)]
    lines = jp.split('{N}')
    widths = [C.width(l) for l in lines]
    print(idx, 'lines:', len(lines), 'widths:', [round(w,1) for w in widths])
