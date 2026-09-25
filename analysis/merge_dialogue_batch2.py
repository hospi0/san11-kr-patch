# -*- coding: utf-8 -*-
"""my files/kr/dialogue/e4_dialogue_*.txt (TSV, block/index/bytes/jp/kr) 배치를
work/e4_dialogue.tsv에 병합. jp 텍스트 불일치·이미 채워진 kr은 스킵(--force로만 덮어씀).

Usage: python analysis/merge_dialogue_batch2.py <file1> [file2 ...] [--dry] [--force]
"""
import io
import shutil
import sys
import unicodedata as U

DST = 'work/e4_dialogue.tsv'


def read_batch(path):
    rows = {}
    for ln in io.open(path, encoding='utf-8'):
        if ln.startswith('#') or ln.startswith('block\t'):
            continue
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            rows[(p[0], p[1])] = (p[3], p[4])
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    force = '--force' in sys.argv

    lines = io.open(DST, encoding='utf-8').read().split('\n')
    idxmap = {}
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            idxmap[(p[0], p[1])] = i

    merged = jp_mismatch = already_filled = no_new_kr = missing_row = 0
    mismatch_list = []
    for path in args:
        batch = read_batch(path)
        for key, (bjp, bkr) in batch.items():
            bkr = U.normalize('NFC', bkr).strip()
            if key not in idxmap:
                missing_row += 1
                continue
            i = idxmap[key]
            p = lines[i].split('\t')
            if U.normalize('NFC', p[3]) != U.normalize('NFC', bjp):
                jp_mismatch += 1
                mismatch_list.append((path, key))
                continue
            if not bkr:
                no_new_kr += 1
                continue
            if p[4].strip() and not force:
                already_filled += 1
                continue
            p[4] = bkr
            lines[i] = '\t'.join(p)
            merged += 1

    print('병합 %d줄 / jp불일치 %d / 이미채워짐(스킵) %d / 배치kr빈값 %d / 행없음 %d'
          % (merged, jp_mismatch, already_filled, no_new_kr, missing_row))
    if mismatch_list:
        print('  jp 불일치 샘플:')
        for path, key in mismatch_list[:15]:
            print('   ', path, key)
    if dry:
        print('(--dry: 저장 안 함)')
        return
    shutil.copy(DST, DST + '.bak_batch2')
    io.open(DST, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s (백업 %s.bak_batch2)' % (DST, DST))


if __name__ == '__main__':
    main()
