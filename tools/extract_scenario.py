# -*- coding: utf-8 -*-
"""s11pkres.bin의 KOEI%SAN11 캠페인 시나리오 컨테이너(idx 6~21)에서 번역 대상 텍스트를 뽑는다.

구조(docs/14): 컨테이너 16개, 각 175,159B, 완전히 고정된 레이아웃(제목 길이와 무관):
  0x5f  제목(가변, 슬롯 0x5f~0x70 = 17B)
  0x70  개요문(가변, 슬롯 0x70~0x1a2 = 306B, 끝 24B는 실측상 항상 0)
  0x1a2 숫자 테이블(211B, 도시/세력 배치로 추정 — 텍스트 아님, 건드리지 않는다)
  0x275 세력별 공략문 배열, 47슬롯 × 0x138(312B). 슬롯 = [텍스트 최대 311B 0패딩][flag 1B]
        flag는 의미 미상이나 되읽기 때 그대로 보존해야 한다(오프셋 마지막 바이트).
        플레이스홀더 2종은 번역 대상 아님: "紹介文"(라벨만) / "…難易度ともに未作成"(미작성).
  0x3bcd 무장 이름 인덱스 → work/roster_kr.tsv 재사용 대상(이 도구는 다루지 않음, 별도 도구 예정)
  0x29119 역사 용어사전(공용, 전 컨테이너 동일) → 별도 도구 예정

출력: work/scenario_kr.tsv (idx, section, slot, flag, jp, kr, note)
  kr을 채우면 build_scenario.py가 반영한다. 미채움(공백) = 원문 유지.

Usage:
  python tools/extract_scenario.py [--out work/scenario_kr.tsv]
"""
import argparse
import csv
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.link import Link

CONTAINERS = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]

TITLE_OFF, TITLE_END = 0x5f, 0x70
OVERVIEW_OFF, OVERVIEW_END = 0x70, 0x1a2
BRIEF_BASE, BRIEF_STRIDE, BRIEF_COUNT = 0x275, 0x138, 47

PLACEHOLDER_LABEL = '紹介文'
PLACEHOLDER_MARK = '未作成'


def decode(b):
    """SJIS -> str, 가이지(0xf0/0xf1 lead byte)는 [Gf0xx] 토큰으로 보존.
    entry5 추출기(analysis/extract_entry5.py name_at)와 같은 관례."""
    b = b.rstrip(b'\x00')
    out, j = [], 0
    while j < len(b):
        hi = b[j]
        if hi < 0x80:
            out.append(chr(hi)); j += 1; continue
        if 0xa1 <= hi <= 0xdf:  # 반각 가나
            out.append(bytes([hi]).decode('cp932')); j += 1; continue
        if j + 1 >= len(b):
            out.append('[X%02x]' % hi); j += 1; continue
        lo = b[j + 1]
        if 0xf0 <= hi <= 0xf1:
            out.append('[G%02x%02x]' % (hi, lo)); j += 2; continue
        try:
            ch = bytes([hi, lo]).decode('cp932')
            if len(ch) != 1:
                raise ValueError
            out.append(ch); j += 2
        except Exception:
            out.append('[X%02x%02x]' % (hi, lo)); j += 2
    return ''.join(out)


TITLE_ALREADY_DONE = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}  # build_kr.py SCENARIO_TITLES


def extract_one(a, idx, rows):
    d = a.read(idx)
    assert struct.unpack('<I', d[:4])[0] == 0xfffe0000, 'idx %d: not a KOEI%%SAN11 container' % idx

    if idx not in TITLE_ALREADY_DONE:  # idx6~19는 build_kr.py가 이미 별도 경로로 패치한다
        title = decode(d[TITLE_OFF:TITLE_END])
        rows.append({'idx': idx, 'section': 'title', 'slot': 0, 'flag': '', 'jp': title, 'kr': ''})

    overview = decode(d[OVERVIEW_OFF:OVERVIEW_END])
    rows.append({'idx': idx, 'section': 'overview', 'slot': 0, 'flag': '', 'jp': overview, 'kr': ''})

    n_real = 0
    for s in range(BRIEF_COUNT):
        off = BRIEF_BASE + s * BRIEF_STRIDE
        rec = d[off:off + BRIEF_STRIDE]
        flag = rec[-1]
        text = rec[:-1].rstrip(b'\x00')
        if not text:
            continue
        txt = decode(text)
        if txt == PLACEHOLDER_LABEL or PLACEHOLDER_MARK in txt:
            continue  # not translatable content
        if '[X' in txt or not re.search(r'[一-龠]', txt):
            continue  # 꼬리 슬롯의 잔여 바이너리 쓰레기(스탯/포인터 leftover) — 텍스트 아님
        rows.append({'idx': idx, 'section': 'brief', 'slot': s, 'flag': flag, 'jp': txt, 'kr': ''})
        n_real += 1
    return n_real


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', default='work/s11pkres.bin')
    ap.add_argument('--out', default='work/scenario_kr.tsv')
    args = ap.parse_args()

    a = Link(args.archive)
    rows = []
    total_briefs = 0
    for idx in CONTAINERS:
        n = extract_one(a, idx, rows)
        total_briefs += n
        print('idx=%d briefs=%d' % (idx, n))

    n_title = sum(1 for r in rows if r['section'] == 'title')
    n_overview = sum(1 for r in rows if r['section'] == 'overview')
    total_chars = sum(len(r['jp']) for r in rows if r['section'] != 'title')
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        f.write('# 시나리오 캠페인 16개(idx 6~21). title %d(idx6~19는 build_kr.py가 이미 처리, 여기 제외) '
                '+ overview %d + brief %d = %d줄 / %d자\n'
                % (n_title, n_overview, total_briefs, len(rows), total_chars))
        f.write('# title=0x5f~0x70(17B) / overview=0x70~0x1a2(306B) / brief=0x275+slot*0x138, 텍스트 311B+flag 1B\n')
        f.write('# ⚠️kr을 비우면 원본 유지(빌더가 원문을 씀). placeholder(紹介文/…未作成)는 추출 대상에서 이미 제외.\n')
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['idx', 'section', 'slot', 'flag', 'jp', 'kr'])
        for r in rows:
            w.writerow([r['idx'], r['section'], r['slot'], r['flag'], r['jp'], r['kr']])

    print('\n%d rows (title %d + overview %d + brief %d) / %d chars (title 제외) -> %s'
          % (len(rows), n_title, n_overview, total_briefs, total_chars, args.out))


if __name__ == '__main__':
    main()
