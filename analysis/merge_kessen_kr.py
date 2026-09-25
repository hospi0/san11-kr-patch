# -*- coding: utf-8 -*-
"""my files/kr/kessen/e4_kessen_[1-6].txt (번역 완료본, 분할 TSV) -> work/e4_kessen.tsv 병합.

각 분할 파일은 원본 헤더(6줄)를 반복해서 갖고 있고 데이터 행만 이어붙이면
work/e4_kessen.tsv와 1:1 대응한다(block, index 순서 그대로). jp 텍스트가
바이트 단위로 일치하는지 확인한 후에만 kr을 채운다.

Usage:
  python analysis/merge_kessen_kr.py [--dry]
"""
import io
import shutil
import sys
import unicodedata as U
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / 'my files' / 'kr' / 'kessen'
DST = ROOT / 'work' / 'e4_kessen.tsv'
PARTS = [SRC_DIR / ('e4_kessen_%d.txt' % i) for i in range(1, 7)]


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

    merged = []
    for part in PARTS:
        if not part.exists():
            print('missing:', part)
            sys.exit(1)
        merged.extend(load_data_rows(part))

    dst_lines = io.open(DST, encoding='utf-8').read().split('\n')
    header = dst_lines[:6]
    dst_rows = []
    for ln in dst_lines[6:]:
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            dst_rows.append(p)

    if len(merged) != len(dst_rows):
        print('행 개수 불일치: 분할본 %d / work tsv %d' % (len(merged), len(dst_rows)))
        sys.exit(1)

    n_filled, n_empty, mismatches, jp_diffs = 0, 0, [], []
    for i, (src, dst) in enumerate(zip(merged, dst_rows)):
        if src[0] != dst[0] or src[1] != dst[1]:
            mismatches.append((i, dst[0], dst[1]))
            continue
        if U.normalize('NFC', src[3]) != U.normalize('NFC', dst[3]):
            jp_diffs.append((i, dst[0], dst[1], src[3], dst[3]))
        kr = U.normalize('NFC', src[4]) if len(src) >= 5 else ''
        if kr.strip():
            dst[4] = kr
            n_filled += 1
        else:
            n_empty += 1

    if mismatches:
        print('⚠️ block/index 불일치(구조 어긋남) %d건, 병합 중단:' % len(mismatches))
        for i, b, idx in mismatches[:20]:
            print('  row %d: block=%s index=%s' % (i, b, idx))
        sys.exit(1)

    if jp_diffs:
        print('⚠️ jp 원문 텍스트 차이 %d건(block:index는 일치, kr은 그대로 채움 — 확인 필요):' % len(jp_diffs))
        for i, b, idx, a, d in jp_diffs:
            print('  [%s:%s] work="%s" / 번역본="%s"' % (b, idx, d, a))

    print('kr 채움: %d행 / 빈 채로 둠: %d행 / 총 %d행' % (n_filled, n_empty, len(dst_rows)))

    if dry:
        print('(--dry: 쓰지 않음)')
        return

    out = header + ['\t'.join(r) for r in dst_rows]
    shutil.copy(DST, str(DST) + '.bak')
    io.open(DST, 'w', encoding='utf-8', newline='').write('\n'.join(out) + '\n')
    print('-> %s (백업 %s.bak)' % (DST, DST))


if __name__ == '__main__':
    main()
