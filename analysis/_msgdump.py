import sys, io
sys.path.insert(0, 'tools')
import help_codec as H

d, offs, msgs = H.load('work/entry3.bin')
mm = dict((i, seg) for i, off, seg in msgs)
want = [243,232,410,143,205,16,21,20,23,24,22,17,18,19,207,204,213]
for idx in want:
    seg = mm.get(idx)
    if seg is None:
        print(idx, '(no msg / empty)')
        continue
    txt = H.decode(seg, codec=None)
    print(idx, repr(txt))
