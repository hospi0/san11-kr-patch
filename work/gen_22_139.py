# -*- coding: utf-8 -*-
"""22:139 — 조건분기 4벌(素質/기초능력 설명). 조건 토큰({04}{V:..}{06}&{V:..}{04}=N)은
   원문에서 그대로 복사하고, 자연어 본문만 번역해 재조립한다(토큰 위치 오염 방지)."""
import io
import json
import re
import sys

sys.path.insert(0, 'analysis')
import e4_common as C

for p in C.read_tsv('work/e4_dict.tsv'):
    if p[0] == '22' and p[1] == '139':
        jp = p[3]
        break

parts = re.split(r'((?:\{05\})+)', jp)
assert len(parts) == 7, len(parts)
bodies = [parts[0], parts[2], parts[4], parts[6]]
seps = [parts[1], parts[3], parts[5]]

COND_RE = re.compile(r'^(\{04\}\{V:e7\}(?:\{06\}&\{V:e8\}\{04\}=\d|\{04\}=\d\{06\}&\{V:e8\}\{04\}=\d))')

SCENARIOS = [
    '영웅집결', '여인의 전쟁', '영웅난무',       # branch0: 3개
    '영웅집결', '여인의 전쟁',                    # branch1: 2개
    '영웅집결', '영웅난무',                        # branch2: 2개 (다른 조합)
    '영웅집결',                                    # branch3: 1개
]
scen_idx = [0, 3, 5, 7, 8]  # slice points into SCENARIOS


def body_kr(scen_list):
    quoted = ''.join('「%s」' % s for s in scen_list)
    return (
        '무장 데이터의 하나.{N}【{1c}[{1c}I00000179무장 데이터 편집{1c}]】나 '
        '【{1c}[{1c}I00000197무장편집{1c}]】에서 설정할 수 있다.{N}{N}'
        '「나이에 따라 성장하는」{1c}[{1c}I00000198기초능력{1c}]의 최고치를 나타낸다.{N}'
        '기초능력은 자연히 소질의 수치까지 성장하고, 소질의 수치에 도달하면 '
        '나이에 따라 서서히 내려간다.{N}{N}'
        '※【환경설정】→【게임】의 【능력변동】이 【무효】이거나, 시나리오가 %s인 경우 '
        '무장의 기초능력은 처음부터 소질의 수치가 된다.{N}'
        '※플레이 중 얻은 {1c}[{1c}I00000183경험{1c}]에 의해 기초능력이 소질의 수치를 '
        '넘는 경우도 있다.'
    ) % quoted


out_bodies = []
for i, b in enumerate(bodies):
    m = COND_RE.match(b)
    cond = m.group(1) if m else ''
    scen = SCENARIOS[scen_idx[i]:scen_idx[i + 1]]
    out_bodies.append(cond + body_kr(scen))

kr = out_bodies[0] + seps[0] + out_bodies[1] + seps[1] + out_bodies[2] + seps[2] + out_bodies[3]

json.dump({'_note': '22:139 조건분기 4벌', '22:139': kr},
          io.open('work/e4_dict_kr_22_139.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('done, len', len(kr))
