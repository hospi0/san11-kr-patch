# -*- coding: utf-8 -*-
import io, re, json
ws = {}
for ln in io.open('work/dict_worksheet.tsv', encoding='utf-8'):
    if ln.startswith('#'): continue
    p = ln.rstrip('\n').split('\t')
    if len(p) >= 4 and p[0].isdigit():
        ws[(p[0], p[1])] = p[3]
FULL_LINK = re.compile(r'\{1c\}\[\{1c\}I[0-9A-Fa-f]{8}[^{]*\{1c\}\]')
targets = [('21', str(i)) for i in range(310, 350)]
n_with = sum(1 for k in targets if FULL_LINK.search(ws[k]))
print('링크 있는 항목:', n_with, '/', len(targets))
