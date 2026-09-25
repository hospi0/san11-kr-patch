# -*- coding: utf-8 -*-
"""e4_kessen.tsv 가이지({BTNxx}) 잔존 11줄을 한글 표기로 완전히 풀어쓴다.
work/cities_kr.tsv·places_kr.tsv·e4_sys.tsv에 이미 쓰인 기존 표기와 맞춘다:
  下{BTN60} -> 하비 (下邳) / {BTN6d} -> 업 (鄴)
  張{BTN43} -> 장합 (張郃) / 蒋{BTN59} -> 장완 (蒋琬) / 費{BTN92} -> 비의 (費禕)

Usage: python analysis/fix_kessen_gaiji.py [--dry]
"""
import io
import shutil
import sys

TSV = 'work/e4_kessen.tsv'

FIXES = {
    ('27', '80'): ('{V:96}5x하{BTN60}{V:96}0x', '{V:96}5x하비{V:96}0x'),
    ('27', '81'): ('{V:96}5x하{BTN60}{V:96}0x', '{V:96}5x하비{V:96}0x'),
    ('27', '210'): ('{V:96}1x장{BTN43}{V:96}0x', '{V:96}1x장합{V:96}0x'),
    ('29', '70'): ('{V:96}19x{BTN6d}병기전{V:96}0x', '{V:96}19x업 병기전{V:96}0x'),
    ('29', '88'): ('{V:96}19x{BTN6d}{V:96}0x함락', '{V:96}19x업{V:96}0x 함락'),
    ('29', '90'): ('{V:96}19x{BTN6d}{V:96}0x과', '{V:96}19x업{V:96}0x과'),
    ('29', '211'): [
        ('{V:96}1x장{BTN59}{V:96}0x', '{V:96}1x장완{V:96}0x'),
        ('{V:96}1x비{BTN92}{V:96}0x', '{V:96}1x비의{V:96}0x'),
    ],
    ('29', '223'): [
        ('{V:96}1x장{BTN59}{V:96}0x', '{V:96}1x장완{V:96}0x'),
        ('{V:96}1x비{BTN92}{V:96}0x', '{V:96}1x비의{V:96}0x'),
    ],
    ('29', '378'): ('{V:96}1x장{BTN43}{V:96}0x', '{V:96}1x장합{V:96}0x'),
    ('29', '379'): ('{V:96}1x장{BTN43}{V:96}0x', '{V:96}1x장합{V:96}0x'),
    ('29', '539'): ('하{BTN60}', '하비'),
}


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) < 5 or not p[0].isdigit():
            continue
        key = (p[0], p[1])
        if key not in FIXES:
            continue
        subs = FIXES[key]
        if isinstance(subs, tuple):
            subs = [subs]
        kr = p[4]
        for old, new in subs:
            if old not in kr:
                print('★[%s:%s] 찾는 문자열 없음: %r' % (key[0], key[1], old))
                sys.exit(1)
            kr = kr.replace(old, new)
        p[4] = kr
        lines[i] = '\t'.join(p)
        n += 1

    print('%d줄 수정' % n)
    if dry:
        print('(--dry: 쓰지 않음)')
        return
    shutil.copy(TSV, TSV + '.bak2')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s' % TSV)


if __name__ == '__main__':
    main()
