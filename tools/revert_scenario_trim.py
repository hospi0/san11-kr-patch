# -*- coding: utf-8 -*-
"""시나리오 개요·공략문(scenario_kr)의 **압축 축약을 되돌린다** — 캡에 들어가는 줄만.

⚠️다른 파일과 달리 여기는 컨테이너에 **고정 레이아웃**으로 박혀 있어 레코드마다 절대 캡이 있다:
    overview 282 B / brief 311 B (build_kr.SCN_* 와 같은 값을 그대로 가져다 쓴다)
  캡을 넘는 줄은 구조적으로 못 돌아간다 — 압축본을 그대로 둔다.

되돌림 대상 판별(축약만 고르고 이후 교정은 보존):
  ① `bak_pre_compress` 와 현재가 다르고
  ② 축약본이 **더 짧고**(= 압축의 흔적)
  ③ 옛 본문의 **가이지 토큰 `[Gf0xx]` 은 현재 파이프라인대로 한글로 풀어** 얹는다
     (압축 뒤에 가이지 교정이 들어갔으므로 그냥 되돌리면 「하[Gf060]」가 되살아난다).
     그러고도 토큰 집합이 다르면 다른 교정이 있었던 것이므로 건너뛴다.
  ④ 인코딩해서 **캡+널이 들어간다**

Usage: python tools/revert_scenario_trim.py [--dry]
"""
import io
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from encoding import Codec                                       # noqa: E402
from kr_names import restore_gaiji, to_hangul, GAIJI_RE          # noqa: E402

SRC = 'work/scenario_kr.tsv'
BAK = 'work/scenario_kr.tsv.bak_pre_compress'
ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
CAP = {'overview': 282, 'brief': 311, 'title': 16}
TOKEN = re.compile(r'\{[^}]*\}|\[[^\]]*\]')


def rows(path):
    out = {}
    for ln in io.open(path, encoding='utf-8'):
        if ln.startswith('#') or ln.startswith('idx\t'):
            continue
        c = ln.rstrip('\n').split('\t')
        if len(c) == 6 and c[5]:
            out[(c[0], c[1], c[2])] = c[5]
    return out


def main():
    dry = '--dry' in sys.argv
    codec = Codec(ELF)
    old, cur = rows(BAK), rows(SRC)
    plan = {}
    skip_cap = skip_token = skip_longer = 0
    for k, o in old.items():
        if k not in cur or o == cur[k]:
            continue
        if len(o) <= len(cur[k]):
            skip_longer += 1                       # 축약이 아니다(나중 수정)
            continue
        if GAIJI_RE.search(o):                     # 압축 뒤에 들어간 가이지 교정을 얹는다
            o = GAIJI_RE.sub(lambda m: to_hangul(restore_gaiji(m.group(0))), o)
        if TOKEN.findall(o) != TOKEN.findall(cur[k]):
            skip_token += 1                        # 토큰이 다르다 = 가이지 등 교정
            continue
        try:
            n = len(codec.encode(o, halfwidth_space=True))
        except Exception:
            skip_token += 1
            continue
        if n + 1 > CAP[k[1]]:
            skip_cap += 1                          # 캡 초과 — 구조적으로 불가
            continue
        plan[k] = o
    print('시나리오: 되돌릴 %d줄 / 캡초과라 보류 %d줄 / 토큰다름·인코딩불가 %d줄 / 축약아님 %d줄'
          % (len(plan), skip_cap, skip_token, skip_longer))
    if dry:
        for k in list(plan)[:3]:
            print('   idx%s %s slot%s' % k)
            print('     후(현재) %s' % cur[k][:76])
            print('     전(복원) %s' % plan[k][:76])
        print('(--dry: 파일 안 씀)')
        return

    shutil.copy(SRC, SRC + '.bak_untrim0729')
    lines = io.open(SRC, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        if ln.startswith('#') or ln.startswith('idx\t'):
            continue
        c = ln.rstrip('\r').split('\t')
        if len(c) == 6 and (c[0], c[1], c[2]) in plan:
            c[5] = plan[(c[0], c[1], c[2])]
            lines[i] = '\t'.join(c)
            n += 1
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('  %s 갱신 %d줄 (백업 %s)' % (SRC, n, SRC + '.bak_untrim0729'))


if __name__ == '__main__':
    main()
