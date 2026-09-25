# -*- coding: utf-8 -*-
import io, sys
sys.path.insert(0, 'analysis')
import e4_common as C
rows = [r for r in C.read_tsv('work/e4_dict.tsv') if r[0] == '22']
passthrough, needs = [], []
for r in rows:
    if C.residual_jp(r[3]) or any('぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿' for ch in r[3]):
        needs.append(r)
    else:
        passthrough.append(r)
print('총 %d / passthrough(번역불필요) %d / 번역필요 %d' % (len(rows), len(passthrough), len(needs)))
print('passthrough 인덱스 범위:', passthrough[0][1] if passthrough else None, '~', passthrough[-1][1] if passthrough else None)
# passthrough 구간이 연속인지 확인
idxs = sorted(int(r[1]) for r in passthrough)
gaps = [(idxs[i], idxs[i+1]) for i in range(len(idxs)-1) if idxs[i+1]-idxs[i] > 1]
print('불연속 구간(앞,다음):', gaps[:20])
