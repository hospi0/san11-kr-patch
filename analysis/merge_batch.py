# -*- coding: utf-8 -*-
"""배치 JSON을 임의의 e4_*.tsv(또는 다른 4컬럼+ TSV)의 kr 열에 병합 — 통합판.

키는 자동 감지: JSON 키에 ':'가 있으면 "block:index"(dict 등 다중 블록),
없으면 "index"(sys 등 단일 인덱스). 두 방식 다 지원한다.

★이미 채워진 kr은 덮지 않는다(--force로만). 빈 값은 쓰지 않는다(원본 삭제 사고 방지).

Usage:
  python analysis/merge_batch.py work/e4_dict.tsv work/e4_dict_kr_batch1.json [--force] [--dry]
"""
import io
import json
import shutil
import sys
import unicodedata as U


def main():
    tsv, path = sys.argv[1], sys.argv[2]
    force = '--force' in sys.argv
    dry = '--dry' in sys.argv
    kr = {k: v for k, v in json.load(io.open(path, encoding='utf-8')).items()
          if not k.startswith('_')}
    block_key = any(':' in k for k in kr)

    lines = io.open(tsv, encoding='utf-8').read().split('\n')
    out, n, skipped, seen = [], 0, [], set()
    for ln in lines:
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            key = ('%s:%s' % (p[0], p[1])) if block_key else p[1]
            seen.add(key)
            if key in kr:
                t = U.normalize('NFC', kr[key]).strip()
                if not t:
                    skipped.append((key, '배치 값이 빈 문자열'))
                elif p[4].strip() and not force:
                    skipped.append((key, '이미 번역됨 — 건너뜀'))
                else:
                    p[4] = t
                    ln = '\t'.join(p)
                    n += 1
        out.append(ln)

    print('%d줄 병합 (키=%s)' % (n, 'block:index' if block_key else 'index'))
    for s in skipped:
        print('  건너뜀 [%s] %s' % s)
    miss = [k for k in kr if k not in seen]
    if miss:
        print('  ⚠️TSV에 없는 키:', miss)
    if dry:
        print('(--dry: 쓰지 않음)')
        return
    shutil.copy(tsv, tsv + '.bak')
    io.open(tsv, 'w', encoding='utf-8', newline='').write('\n'.join(out))
    print('-> %s (백업 %s.bak)' % (tsv, tsv))


if __name__ == '__main__':
    main()
