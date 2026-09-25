# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'analysis')
import e4_common as C
rows = C.read_tsv('work/e4_dict.tsv')
from collections import Counter
tot = Counter(r[0] for r in rows)
done = Counter(r[0] for r in rows if r[4].strip())
for b in sorted(tot):
    print('block %s: %d/%d' % (b, done[b], tot[b]))
print('total: %d/%d' % (sum(done.values()), sum(tot.values())))
