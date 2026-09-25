# -*- coding: utf-8 -*-
"""idx5(=entry5, s11pkres 0x1e9800)의 **기존 파이프라인이 안 덮는** 텍스트 필드를 뽑는다.

해독 경위(docs/15): 사용자가 PC판 scenario.s11(47,800B, idx5와 크기 동일)과 비교해 누락을
지적 → PC JPN↔KOR(도원결의) 바이트 diff를 "구조 오라클"로 써서(번역문은 안 씀, 사용자 방침)
레코드 격자를 확정했다. "가변 헤더"로 보이던 것은 전부 **옛 레이아웃 잔재**였고, 진짜 스키마는
특기·기교·능력 테이블과 똑같은 **고정 오프셋**이다:

  전장시설(배틀맵 오브젝트+시설 Lv변형): base 0x0B82, stride 0xBD × 60
      +0x00 이름(cap 8) · +0x09 읽기(건드리지 않음) · +0x1E 설명(cap 70) · +0x65 건설조건
      k0~30 = 都市·関所·港·陣·砦·城塞·弓櫓·連弩櫓·土塁·石壁·投石台·太鼓台·軍楽台·石兵八陣·
              根城×2·火種·火炎種·火球·火炎球·火船·業火球·業火種·落石·堤防·浅瀬·山岳·長城·
              遺跡·廟·銅雀台 / k31~35·50~59 = 시설 Lv1~3 / k36~49 = 고급시설
  병장: base 0x3AC2, stride 0x96 × 12   +0x00 이름 · +0x1A 설명
  지형: base 0x8A54, stride 0x17 × 20   +0x00 이름(cap 4 — 읽기가 +0x05) · k20 'tile20' placeholder
  관직[80]: 0x51E2 'なし' 1건 (관직 80개 배열 바로 뒤의 81번째 슬롯, 기존 파이프라인 미포함)

+0x7B 부근의 그럴듯한 문장들은 **다른 레코드 설명의 머리 잘린 파편 = 죽은 바이트**다
(KOR판도 안 건드림). 절대 필드로 취급하지 말 것.

이미 우리 빌드가 패치하는 필드(시설명 40종·시설효과 47종 등)는 패치된 ISO와의 diff로
자동 감지해 **제외**한다. 출력: work/idx5_extra_kr.tsv (table, k, field, rel_off, budget, jp, kr)

Usage: python tools/extract_idx5_extra.py [--iso <패치된iso>] [--out work/idx5_extra_kr.tsv]
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from tools.link import Link

S11_OFF, IDX5_OFF = 0x73e000, 0x1e9800   # 패치된 ISO에서 idx5를 읽는 위치

FAC_BASE, FAC_STRIDE, FAC_N = 0x0B82, 0xBD, 60
FAC_NAME_CAP, FAC_DESC_OFF, FAC_DESC_CAP, FAC_COND_OFF = 8, 0x1E, 0x46, 0x65
WPN_BASE, WPN_STRIDE, WPN_N, WPN_DESC_OFF = 0x3AC2, 0x96, 12, 0x1A
TER_BASE, TER_STRIDE, TER_N, TER_NAME_CAP = 0x8A54, 0x17, 20, 4
RANK81_OFF, RANK81_CAP = 0x51E2, 10

# KOR판(도원결의)조차 안 건드린 플레이스홀더성 문자열 — 문자열 키 조회에 쓰일 가능성을
# 배제 못 해 번역하지 않는다('制限' 46건은 어느 화면에 뜨는지도 미확인).
PLACEHOLDERS = {'制限', '説明文', '紹介文'}


def clean_text(buf, off, hard_cap=None):
    """고정 오프셋에서 널 종료 텍스트. 잔재 구분: 시작 바이트가 유효 SJIS 리드여야 하고
    끝까지 깨끗해야 한다. 아니면 None(잔재/빈 필드)."""
    e = off
    n = len(buf) if hard_cap is None else min(len(buf), off + hard_cap)
    while e < n and buf[e] != 0:
        e += 1
    if e == off:
        return None
    raw = buf[off:e]
    try:
        txt = raw.decode('cp932')
    except Exception:
        return None
    if any(ord(c) < 0x20 or 0xE000 <= ord(c) <= 0xF8FF or 0xFF61 <= ord(c) <= 0xFF9F
           for c in txt):
        return None
    if not re.search(r'[一-龠ぁ-ゟァ-ヿ]', txt):
        return None
    return txt


def cond_budget(orig, rec):
    """건설조건(+0x65)의 안전 예산 = 다음 레코드 이름 직전의 '살아있는 스탯 런' 시작까지.
    스탯 런 = 레코드 꼬리에서 다음 이름 바로 앞에 붙은 마지막 비-널 런(실측: 90 01 2c 01…
    류 14B 내외). 그 앞 여백까지가 쓰기 가능 폭이다."""
    tail = rec + FAC_STRIDE          # 다음 레코드 이름 오프셋
    j = tail - 1
    while j > rec + FAC_COND_OFF and orig[j] == 0:
        j -= 1
    # j = 마지막 비-널 바이트. 그 런의 시작까지 후퇴
    while j > rec + FAC_COND_OFF and orig[j - 1] != 0:
        j -= 1
    return max(0, j - (rec + FAC_COND_OFF) - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', default='work/s11pkres.bin')
    ap.add_argument('--iso', default='C:/claude/roms/ps2/San11_kr.iso')
    ap.add_argument('--out', default='work/idx5_extra_kr.tsv')
    args = ap.parse_args()

    orig = Link(args.archive).read(5)
    with open(args.iso, 'rb') as f:
        f.seek(S11_OFF + IDX5_OFF)
        pat = f.read(len(orig))

    def covered(off, span=4):
        """우리 빌드가 이미 이 필드를 패치하는가 (패치 ISO와 원본의 diff로 판정)"""
        return orig[off:off + span] != pat[off:off + span]

    rows = []

    def add(table, k, field, off, budget, jp):
        if jp in PLACEHOLDERS:
            return
        rows.append({'table': table, 'k': k, 'field': field,
                     'off': off, 'budget': budget, 'jp': jp})

    # ---- 전장시설 60 ----
    for k in range(FAC_N):
        rec = FAC_BASE + k * FAC_STRIDE
        nm = clean_text(orig, rec, FAC_NAME_CAP + 1)
        if nm and nm.strip('－') and not covered(rec):
            add('fac', k, 'name', rec, FAC_NAME_CAP, nm)
        ds = clean_text(orig, rec + FAC_DESC_OFF, FAC_DESC_CAP + 1)
        if ds and not covered(rec + FAC_DESC_OFF):
            add('fac', k, 'desc', rec + FAC_DESC_OFF, FAC_DESC_CAP, ds)
        cd = clean_text(orig, rec + FAC_COND_OFF)
        if cd and not covered(rec + FAC_COND_OFF):
            add('fac', k, 'cond', rec + FAC_COND_OFF, cond_budget(orig, rec), cd)

    # ---- 병장 12 (설명만 — 이름 12종은 기존 entry5 파이프라인이 처리) ----
    for k in range(WPN_N):
        rec = WPN_BASE + k * WPN_STRIDE
        ds = clean_text(orig, rec + WPN_DESC_OFF)
        if ds and not covered(rec + WPN_DESC_OFF):
            # 꼬리 스탯 런 실측으로 예산 산출 (건설조건과 같은 방식)
            tail = rec + WPN_STRIDE
            j = tail - 1
            while j > rec + WPN_DESC_OFF and orig[j] == 0:
                j -= 1
            while j > rec + WPN_DESC_OFF and orig[j - 1] != 0:
                j -= 1
            add('wpn', k, 'desc', rec + WPN_DESC_OFF,
                max(0, j - (rec + WPN_DESC_OFF) - 1), ds)

    # ---- 지형 20 (이름만 — cap 4B 하드, 읽기 +0x05는 불변) ----
    for k in range(TER_N):
        rec = TER_BASE + k * TER_STRIDE
        nm = clean_text(orig, rec, TER_NAME_CAP + 1)
        if nm and not covered(rec):
            add('ter', k, 'name', rec, TER_NAME_CAP, nm)

    # ---- 관직 81번째 なし ----
    nm = clean_text(orig, RANK81_OFF, RANK81_CAP + 1)
    if nm and not covered(RANK81_OFF):
        add('rank', 80, 'name', RANK81_OFF, RANK81_CAP, nm)

    total_chars = sum(len(r['jp']) for r in rows)
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        f.write('# idx5(entry5) 잔여 필드 — 기존 파이프라인 미커버분만. 구조 = docs/15\n')
        f.write('# %d필드 / %d자. budget = 널 포함 안 한 텍스트 최대 바이트(실측 스탯 런 경계)\n'
                % (len(rows), total_chars))
        f.write('# ⚠️kr 비우면 원본 유지. ⚠️지형 이름 cap 4B = 한글 2음절 하드 리밋(+0x05가 읽기)\n')
        f.write('# ⚠️번역문에 한자 금지(운반체). 기존 번역과 용어 일치시킬 것: 초원·땅·모래·강·바다·\n')
        f.write('#   하천·황야·대로·나루·물가·벼랑(지형11 실기 통과분) / 관문·본성·여울(facilities)\n')
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['table', 'k', 'field', 'off', 'budget', 'jp', 'kr'])
        for r in rows:
            w.writerow([r['table'], r['k'], r['field'], '%#x' % r['off'],
                        r['budget'], r['jp'], ''])
    print('%d fields / %d chars -> %s' % (len(rows), total_chars, args.out))
    from collections import Counter
    print(dict(Counter('%s.%s' % (r['table'], r['field']) for r in rows)))


if __name__ == '__main__':
    main()
