import sys
sys.path.insert(0,'analysis')
sys.path.insert(0,'tools')
import fix_dialogue_ctokens as F
import help_codec as H

for s in ['{01}Cま{00}']:
    for m in F.PAT.finditer(s):
        print(s, '->', F.tok_index(m))

d, offs, msgs = H.load('work/entry3.bin')
mm = dict((i, seg) for i, off, seg in msgs)
for idx in [153+256-256]:
    pass
# compute index for 'ま' bank0
import re
ch='ま'
o=ord(ch)
print('ord',hex(o))
if 0x3041 <= o <= 0x3096:
    ch2 = chr(o+0x60)
    print('shifted', ch2, hex(ord(ch2)))
low = H._HW.get(ch2)
print('low', low)
seg = mm.get(low)
print(low, repr(H.decode(seg, codec=None)) if seg else None)
