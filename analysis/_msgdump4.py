import sys, io
sys.path.insert(0,'analysis')
sys.path.insert(0,'tools')
import fix_dialogue_ctokens as F
import help_codec as H

rows = []
for ln in io.open('work/e4_sys_needtrans.tsv', encoding='utf-8'):
    p = ln.rstrip('\n').split('\t')
    if len(p) >= 3 and p[0].isdigit():
        rows.append((p[0], p[1], p[2]))

allidx = set()
for idx, blen, jp in rows:
    for m in F.PAT.finditer(jp):
        ti = F.tok_index(m)
        if ti is not None and ti not in F.KEEP and ti not in F.DROP:
            allidx.add(ti)

d, offs, msgs = H.load('work/entry3.bin')
mm = dict((i, seg) for i, off, seg in msgs)
out = io.open('work/_msg_lookup.txt','w',encoding='utf-8')
for idx in sorted(allidx):
    seg = mm.get(idx)
    txt = H.decode(seg, codec=None) if seg else '(empty)'
    rule = F.RULE_OF.get(idx,'?')
    out.write('%d\t%s\t%s\n' % (idx, rule, txt))
out.close()
print(len(allidx), 'written to work/_msg_lookup.txt')
