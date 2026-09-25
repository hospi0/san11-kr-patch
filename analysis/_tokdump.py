import re, sys, io
sys.path.insert(0,'analysis')
sys.path.insert(0,'tools')
import fix_dialogue_ctokens as F

rows = []
for ln in io.open('work/e4_sys_needtrans.tsv', encoding='utf-8'):
    p = ln.rstrip('\n').split('\t')
    if len(p) >= 3 and p[0].isdigit():
        rows.append((p[0], p[1], p[2]))

for idx, blen, jp in rows:
    print('=== idx=%s (%s bytes) ===' % (idx, blen))
    for m in F.PAT.finditer(jp):
        ti = F.tok_index(m)
        rule = F.RULE_OF.get(ti)
        tag = 'KEEP' if ti in F.KEEP else ('DROP' if ti in F.DROP else (rule or ('REVIEW' if ti in F.REVIEW_ALWAYS else '?')))
        print('  tok=%r idx=%s -> %s' % (m.group(0), ti, tag))
