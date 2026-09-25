# -*- coding: utf-8 -*-
"""22:171(성장기)·22:172(능력지속) — 22:139와 같은 4분기 구조. 조건 토큰 그대로,
   본문만 번역해 재조립."""
import io
import json
import re
import sys

sys.path.insert(0, 'analysis')
import e4_common as C

rows = {(r[0], r[1]): r[3] for r in C.read_tsv('work/e4_dict.tsv')}
COND_RE = re.compile(r'^(\{04\}\{V:e7\}(?:\{06\}&\{V:e8\}\{04\}=\d|\{04\}=\d\{06\}&\{V:e8\}\{04\}=\d))')

SCENARIOS = ['영웅집결', '여인의 전쟁', '영웅난무']
scen_by_branch = [
    ['영웅집결', '여인의 전쟁', '영웅난무'],
    ['영웅집결', '여인의 전쟁'],
    ['영웅집결', '영웅난무'],
    ['영웅집결'],
]

LINK_PREFIX_6 = (
    '무장 데이터의 하나.{N}【{1c}[{1c}I00000179무장 데이터 편집{1c}]】나 '
    '【{1c}[{1c}I00000197무장편집{1c}]】, 【{1c}[{1c}I00000213신무장등록{1c}]】에서 설정할 수 있다.{N}'
)


def body171(scen):
    quoted = ''.join('「%s」' % s for s in scen)
    return (
        LINK_PREFIX_6 +
        '※【무장 데이터 편집】과 【무장편집】에서는 「성장」으로 표기된다.{N}{N}'
        '{1c}[{1c}I00000198기초능력{1c}]의 성장기를 나타낸다.{N}'
        '기초능력은 자연히 {1c}[{1c}I00000180소질{1c}]의 수치까지 성장한다.{N}'
        '「개안」은 성장기가 ２번 찾아온다.{N}{N}'
        '※【환경설정】→【게임】의 【능력변동】이 【무효】인 경우, 또는 시나리오가 %s인 경우 '
        '무장의 기초능력은 처음부터 소질의 수치가 된다.{N}{N}'
        '※플레이 중 얻은 {1c}[{1c}I00000183경험{1c}]에 의해 기초능력이 소질의 수치를 '
        '넘는 경우도 있다.'
    ) % quoted


def body172(scen):
    quoted = ''.join('「%s」' % s for s in scen)
    return (
        LINK_PREFIX_6 +
        '※【무장 데이터 편집】과 【무장편집】에서는 「지속」으로 표기된다.{N}{N}'
        '{1c}[{1c}I00000198기초능력{1c}]이 완전히 성장한（{1c}[{1c}I00000180소질{1c}]의 수치까지 '
        '오른）상태의 지속 기간.{N}'
        '「길다」로 하면 완전히 성장한 상태가 오래 지속된다.{N}'
        '（기초능력의 정점이 길다）{N}{N}'
        '※【환경설정】→【게임】의 【능력변동】이 【무효】인 경우, 또는 시나리오가 %s인 경우 '
        '무장의 기초능력은 처음부터 소질의 수치가 된다.{N}{N}'
        '※플레이 중 얻은 {1c}[{1c}I00000183경험{1c}]에 의해 기초능력이 소질의 수치를 '
        '넘는 경우도 있다.'
    ) % quoted


def build(key, body_fn):
    jp = rows[key]
    parts = re.split(r'((?:\{05\})+)', jp)
    assert len(parts) == 7, len(parts)
    bodies = [parts[0], parts[2], parts[4], parts[6]]
    seps = [parts[1], parts[3], parts[5]]
    out_bodies = []
    for i, b in enumerate(bodies):
        m = COND_RE.match(b)
        cond = m.group(1) if m else ''
        out_bodies.append(cond + body_fn(scen_by_branch[i]))
    return out_bodies[0] + seps[0] + out_bodies[1] + seps[1] + out_bodies[2] + seps[2] + out_bodies[3]


result = {
    '_note': '22:171/172 조건분기 4벌',
    '22:171': build(('22', '171'), body171),
    '22:172': build(('22', '172'), body172),
}
json.dump(result, io.open('work/e4_dict_kr_22_171_172.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('done', {k: len(v) for k, v in result.items() if k != '_note'})
