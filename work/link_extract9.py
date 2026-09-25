# -*- coding: utf-8 -*-
import io, re, json
ws = {}
for ln in io.open('work/dict_worksheet.tsv', encoding='utf-8'):
    if ln.startswith('#'): continue
    p = ln.rstrip('\n').split('\t')
    if len(p) >= 4 and p[0].isdigit():
        ws[(p[0], p[1])] = p[3]
FULL_LINK = re.compile(r'\{1c\}\[\{1c\}I[0-9A-Fa-f]{8}[^{]*\{1c\}\]')
targets = [('22', str(i)) for i in range(111, 151)]
out = {}
lines = []
for k in targets:
    text = ws[k]
    links = FULL_LINK.findall(text)
    out['%s:%s' % k] = links
    lines.append('%s:%s  n=%d  %s' % (k[0], k[1], len(links), links))
json.dump(out, io.open('work/links22_111_150.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
io.open('work/links_dump.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('ok')
