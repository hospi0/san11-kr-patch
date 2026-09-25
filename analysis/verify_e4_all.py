# -*- coding: utf-8 -*-
"""entry4_kr.bin을 **빌더와 무관하게 새로 파싱**해 번역된 전 블록(21·22·23)을 검증한다.
verify_e4_sys.py의 일반화판 — dict(21·22) 전체 완료 후 sys와 함께 한 번에 돈다.

  ① 번역한 줄  = TSV의 kr과 글자단위 일치하는가 (되읽기)
  ② 번역 안 한 줄 = 원본 entry4와 **바이트 동일**한가 (빈 값이 원본을 지우지 않았는가)
  ③ 메시지 개수 = 블록별로 그대로인가
  ④ 건드리지 않은 나머지 블록(0~20,24~29)은 완전히 불변인가

Usage: python analysis/verify_e4_all.py
"""
import io
import os
import sys
import unicodedata as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import ls11                                              # noqa: E402
from help_codec import parse_offsets, segments, decode   # noqa: E402
from encoding import Codec                               # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
TSV_BY_BLOCK = {21: 'work/e4_dict.tsv', 22: 'work/e4_dict.tsv', 23: 'work/e4_sys.tsv'}


def load_kr(path):
    kr = {}
    for ln in io.open(path, encoding='utf-8'):
        if ln.startswith('#'):
            continue
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit() and p[4].strip():
            kr[(int(p[0]), int(p[1]))] = U.normalize('NFC', p[4]).strip()
    return kr


def main():
    src = open('work/entry4.bin', 'rb').read()
    new = open('work/entry4_kr.bin', 'rb').read()
    codec = Codec(ELF)

    kr_cache = {}
    total_ok_tr = total_bad_tr = total_ok_keep = total_bad_keep = 0

    for block, tsv in TSV_BY_BLOCK.items():
        if tsv not in kr_cache:
            kr_cache[tsv] = load_kr(tsv)
        kr = kr_cache[tsv]

        d_old = ls11.decode_block(src, block)
        d_new = ls11.decode_block(new, block)
        s_old = segments(d_old, parse_offsets(d_old))
        s_new = segments(d_new, parse_offsets(d_new))
        msg_ok = len(s_old) == len(s_new)
        print('block%d 메시지 개수: 원본 %d -> 빌드 %d  %s'
              % (block, len(s_old), len(s_new), 'OK' if msg_ok else '★불일치'))

        ok_tr = bad_tr = ok_keep = bad_keep = 0
        for i, (a, b) in enumerate(zip(s_old, s_new)):
            key = (block, i)
            if key in kr:
                got = U.normalize('NFC', decode(b, codec))
                want = kr[key]
                if want in got:
                    ok_tr += 1
                else:
                    bad_tr += 1
                    if bad_tr <= 5:
                        print('★[%d:%d] 되읽기 불일치\n   기대: %s\n   실제: %s'
                              % (block, i, want[:70], got[:70]))
            else:
                if a == b:
                    ok_keep += 1
                else:
                    bad_keep += 1
                    if bad_keep <= 5:
                        print('★[%d:%d] 미번역인데 바이트가 바뀌었다 (%d B -> %d B)'
                              % (block, i, len(a), len(b)))
        print('  번역줄  : %d 일치 / %d 불일치' % (ok_tr, bad_tr))
        print('  미번역줄: %d 원본유지 / %d 오염' % (ok_keep, bad_keep))
        total_ok_tr += ok_tr
        total_bad_tr += bad_tr
        total_ok_keep += ok_keep
        total_bad_keep += bad_keep

    touched = set(TSV_BY_BLOCK)
    other = sum(1 for i in range(30) if i not in touched
                and ls11.decode_block(src, i) != ls11.decode_block(new, i))
    print('\n건드리지 않은 %d블록 중 바뀐 것: %d개 (0이어야 정상)' % (30 - len(touched), other))
    print('\n총합: 번역줄 %d 일치 / %d 불일치 · 미번역줄 %d 원본유지 / %d 오염'
          % (total_ok_tr, total_bad_tr, total_ok_keep, total_bad_keep))
    bad = total_bad_tr or total_bad_keep or other
    print('\n' + ('★★실패' if bad else '✓ 전체 통과'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
