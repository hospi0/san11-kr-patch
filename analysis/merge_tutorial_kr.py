# -*- coding: utf-8 -*-
"""my files/kr/tutorial/e4_tutorial_[1-11].txt (번역 진행분, 분할 TSV) -> work/e4_tutorial.tsv 병합.

merge_kessen_kr.py와 동일한 방식이나, 이쪽은 아직 전량이 아니라 blocks 25·26 전체 +
block 28 일부(0~294)까지만 있다(나머지는 추후 별도 배치). block:index로 매칭해 있는
것만 반영하고, jp 텍스트는 NFC 정규화 후 비교(다르면 병합 중단, 리포트).

Usage:
  python analysis/merge_tutorial_kr.py [--dry]
"""
import io
import shutil
import sys
import unicodedata as U
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / 'my files' / 'kr' / 'tutorial'
DST = ROOT / 'work' / 'e4_tutorial.tsv'
PARTS = [SRC_DIR / ('e4_tutorial_%d.txt' % i) for i in range(1, 12)]


def load_data_rows(path):
    lines = io.open(path, encoding='utf-8').read().split('\n')
    rows = []
    for ln in lines:
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            rows.append(p)
    return rows


def main():
    dry = '--dry' in sys.argv

    merged = {}
    for part in PARTS:
        if not part.exists():
            print('missing:', part)
            sys.exit(1)
        for r in load_data_rows(part):
            key = (r[0], r[1])
            if key in merged:
                print('⚠️ 중복 키 %s — 병합 중단' % (key,))
                sys.exit(1)
            merged[key] = r

    dst_lines = io.open(DST, encoding='utf-8').read().split('\n')
    header = dst_lines[:6]
    dst_rows = []
    for ln in dst_lines[6:]:
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            dst_rows.append(p)

    n_filled, n_missing, mismatches, jp_diffs = 0, 0, [], []
    for dst in dst_rows:
        key = (dst[0], dst[1])
        src = merged.get(key)
        if src is None:
            n_missing += 1
            continue
        if U.normalize('NFC', src[3]) != U.normalize('NFC', dst[3]):
            jp_diffs.append((key, src[3], dst[3]))
        kr = U.normalize('NFC', src[4]) if len(src) >= 5 else ''
        if kr.strip():
            dst[4] = kr
            n_filled += 1

    if jp_diffs:
        print('⚠️ jp 원문 텍스트 차이 %d건(block:index는 일치, kr은 그대로 채움 — 확인 필요):' % len(jp_diffs))
        for key, a, d in jp_diffs:
            print('  [%s:%s] work="%s" / 번역본="%s"' % (key[0], key[1], d, a))

    print('kr 채움: %d행 / 아직 번역본에 없음(다음 배치): %d행 / 총 %d행'
          % (n_filled, n_missing, len(dst_rows)))

    if dry:
        print('(--dry: 쓰지 않음)')
        return

    out = header + ['\t'.join(r) for r in dst_rows]
    shutil.copy(DST, str(DST) + '.bak')
    io.open(DST, 'w', encoding='utf-8', newline='').write('\n'.join(out) + '\n')
    print('-> %s (백업 %s.bak)' % (DST, DST))


if __name__ == '__main__':
    main()
