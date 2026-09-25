# -*- coding: utf-8 -*-
"""압축 예산 때문에 잘라냈던 **튜토리얼·결전 축약을 되돌린다**.

2026-07-29 세션28에 해제 버퍼(0x18000)와 entry4 슬롯(380섹터)이 넓어져 전제가 사라졌다.

  튜토리얼: `my files/tutorial_trim.txt` 의 원본/축약 대조 기록이 정확한 출처다.
            **현재 tsv 가 「축약」 그대로인 줄만** 되돌린다 — 이후 다른 교정이 얹힌 줄은
            건드리면 그 교정이 날아간다(드리프트로 보고 건너뜀).
  결전:     `e4_kessen.tsv.bak_aggressive` 와의 차이 중
            ⛔「、→,」 구두점 정책(33줄)과 ⛔조사 교정(「{}라면」→「{}이라면」)은 **유지**하고,
            진짜 축약만 되돌린다.

Usage: python tools/revert_trims.py [--dry]
"""
import io
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_trim import parse_trim                                # noqa: E402

TUT = 'work/e4_tutorial.tsv'
TRIM = 'my files/tutorial_trim.txt'
KES = 'work/e4_kessen.tsv'
KES_BAK = 'work/e4_kessen.tsv.bak_aggressive'


def rows(path):
    out = {}
    for ln in io.open(path, encoding='utf-8'):
        c = ln.rstrip('\n').split('\t')
        if len(c) >= 5 and c[0].isdigit():
            out[(int(c[0]), int(c[1]))] = c[4]
    return out


def write(path, plan, tag):
    shutil.copy(path, path + tag)
    lines = io.open(path, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        c = ln.rstrip('\r').split('\t')
        if len(c) >= 5 and c[0].isdigit() and (int(c[0]), int(c[1])) in plan:
            c[4] = plan[(int(c[0]), int(c[1]))]
            lines[i] = '\t'.join(c)
            n += 1
    io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('  %s 갱신 %d줄 (백업 %s)' % (path, n, path + tag))


def main():
    dry = '--dry' in sys.argv

    # ── 튜토리얼 ──────────────────────────────────────────────
    cur = rows(TUT)
    plan, drift = {}, 0
    for k, (orig, short) in parse_trim(TRIM).items():
        if orig == short or k not in cur:
            continue
        if cur[k] != short:
            drift += 1                      # 트림 뒤에 다른 수정이 얹힌 줄 → 보존
            continue
        plan[k] = orig
    print('튜토리얼: 되돌릴 %d줄 / 이후 수정돼 보존할 %d줄' % (len(plan), drift))
    if not dry:
        write(TUT, plan, '.bak_untrim0729')

    # ── 결전 ─────────────────────────────────────────────────
    old, now = rows(KES_BAK), rows(KES)
    kplan = {}
    for k, o in old.items():
        if k not in now or o == now[k] or not o.strip():
            continue
        if o.replace('、', ',') == now[k]:
            continue                        # 구두점 정책 — 유지
        if o.replace('라면', '이라면') == now[k]:
            continue                        # 조사 교정 — 유지
        kplan[k] = o
    print('결전: 되돌릴 %d줄 (구두점·조사 교정은 제외)' % len(kplan))
    if not dry:
        write(KES, kplan, '.bak_untrim0729')
    if dry:
        print('(--dry: 파일 안 씀)')


if __name__ == '__main__':
    main()
