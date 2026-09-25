# -*- coding: utf-8 -*-
import io, re, sys, json
sys.path.insert(0, 'analysis')
import e4_common as C
rows = {(r[0], r[1]): r[3] for r in C.read_tsv('work/e4_dict.tsv')}
for key in [('22','171'), ('22','172')]:
    jp = rows[key]
    parts = re.split(r'((?:\{05\})+)', jp)
    print(key, 'parts:', len(parts), [len(p) for p in parts])
