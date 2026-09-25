# -*- coding: utf-8 -*-
"""2026-07-29 해제버퍼 대응으로 깎았던 **축약을 되돌린다** (문법·오역 교정은 유지).

배경: 그날의 1,422 B 감축은 「버퍼가 0x13000 고정」이라는 전제에서 나온 것이었다.
      같은 날 늦게 **힙 용량까지 같이 키우면 버퍼를 0x18000 으로 확대할 수 있음**이
      실기로 확인돼(e4_buffer.py) 그 전제가 사라졌다. 축약은 품질 손실이므로 되돌린다.

되돌리는 것 = 축약 (예: 「발견했습니다→찾았습니다」 32곳, 반복 슬로건 30곳,
  「~해 주십시오→~하십시오」, 「되었→됐」, 「인재 탐색→탐색」 …)
유지하는 것 = 문법·오역 교정
  ① 「듯하는군요 → 듯하군요」 34곳
  ② idx607 「와주었습니다{N}시니, 」 → 「와주셨군요{N}」 (JP 「して、」 오독)
  ③ (신규) 같은 계열 잔재 「간단/무모/부족/이상/미숙 하는군요」 7곳도 함께 교정

Usage: python tools/revert_shrink0729.py [--dry]
"""
import io
import re
import shutil
import sys

SRC = 'work/e4_dialogue.tsv'
BAK = 'work/_bak_shrink0729.tsv'          # 축약 직전 상태(07-29 13:11)
OUT_BAK = 'work/e4_dialogue.tsv.bak_revert0729'

# ① 유지할 문법 교정 — 되돌린 본문에 다시 얹는다
KEEP_GLOBAL = [('듯하는군요', '듯하군요')]
# ③ 같은 계열 잔재(이번에 새로 교정)
RESIDUAL = re.compile(r'([가-힣]{1,3})하는군요')
KEEP_ROW = {(0, 607): [('와주었습니다{N}시니, ', '와주셨군요{N}')]}


def rows(path):
    out = {}
    for ln in io.open(path, encoding='utf-8'):
        c = ln.rstrip('\n').split('\t')
        if len(c) >= 5 and c[0].isdigit():
            out[(int(c[0]), int(c[1]))] = c[4]
    return out


def main():
    dry = '--dry' in sys.argv
    old, cur = rows(BAK), rows(SRC)
    assert set(old) == set(cur), '행 키가 다르다 — 백업이 맞는 파일인지 확인할 것'

    plan, kept, resid = {}, 0, 0
    for k, o in old.items():
        if o == cur[k]:
            continue
        t = o                                        # ← 축약 이전으로 복귀
        for a, b in KEEP_GLOBAL + KEEP_ROW.get(k, []):
            if a in t:
                t = t.replace(a, b)
                kept += 1
        plan[k] = t
    # ③ 잔재 교정은 파일 전체 대상
    for k, v in cur.items():
        t = plan.get(k, v)
        t2 = RESIDUAL.sub(r'\1하군요', t)
        if t2 != t:
            resid += RESIDUAL.subn(r'\1하군요', t)[1]
            plan[k] = t2

    delta = sum(len(plan[k]) - len(cur[k]) for k in plan)
    print('되돌릴 줄 %d개 / 문법교정 재적용 %d곳 / 잔재 「~하는군요」 교정 %d곳'
          % (len(plan), kept, resid))
    print('텍스트 길이 변화 %+d자 (인코딩 기준 대략 %+d B)' % (delta, delta * 2))
    for k in sorted(plan)[:4]:
        print('   blk%d idx%-4d %s' % (k[0], k[1], plan[k][:78]))
    if dry:
        print('(--dry: 파일 안 씀)')
        return

    shutil.copy(SRC, OUT_BAK)
    lines = io.open(SRC, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        c = ln.rstrip('\r').split('\t')
        if len(c) >= 5 and c[0].isdigit() and (int(c[0]), int(c[1])) in plan:
            c[4] = plan[(int(c[0]), int(c[1]))]
            lines[i] = '\t'.join(c)
            n += 1
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('%s 갱신 %d줄 (백업 %s)' % (SRC, n, OUT_BAK))


if __name__ == '__main__':
    main()
