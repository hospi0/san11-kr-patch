import sys
sys.path.insert(0, 'tools')
import help_codec as H
d, offs, msgs = H.load('work/entry3.bin')
mm = dict((i, seg) for i, off, seg in msgs)
for idx in [411, 144]:
    seg = mm.get(idx)
    print(idx, repr(H.decode(seg, codec=None)) if seg else None)
