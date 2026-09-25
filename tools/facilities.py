# -*- coding: utf-8 -*-
"""시설(施設) 이름 — 정본 리스트 + 한글 + entry5 유효 위치 탐색.

원칙(경계 오판 방지):
  · 정본 시설명(full)으로만 매칭 → 부분일치 노이즈(制限·増加·拠点) 배제
  · null 종료(name\\0) + **직전이 CJK가 아님** → 石兵八陣 속 陣 같은 복합어 내부 배제
  · 설명문은 시설명을 포함하지 않으므로(실측) 유효 위치는 전부 이름 필드
  · 시설은 2벌(본편/PUK)이라 **모든 유효 위치**를 패치 대상으로 반환

한글은 1:1 독음(바이트 동일)이 기본, 관례·의미로 교정할 땐 **글자 수 동일**만 허용
(浅瀬 2자→여울 2자 OK / 厩舎→마구간 3자는 예산초과라 2자 「마사」).
"""
import os

# 정본 시설명 → 한글. 값이 None이면 to_hangul 독음 사용.
# ★시설명은 entry5에 여러 벌 있고, 시설설정 메뉴는 0x2xxx 고급시설 테이블을 읽는다.
#   그래서 구역을 전체(0xb82~0x3800)로 넓혀 모든 복사본을 잡는다(전부 바이트동일).
FACILITIES = {
    "都市": None,        # 도시
    "関所": "관문",       # 독음 관소 → 관문(관례)
    "陣": None,          # 진
    "港": None,          # 항
    "城塞": None,        # 성새
    "連弩櫓": None,      # 연노로
    "砦": None,          # 채
    "石壁": None,        # 석벽
    "太鼓台": None,      # 태고대
    "弓櫓": None,        # 궁로
    "石兵八陣": None,    # 석병팔진
    "根城": "본성",       # 독음 근성 → 본성(의미)
    "土塁": None,        # 토루
    "火炎種": None,      # 화염종
    "火炎球": None,      # 화염구
    "投石台": None,      # 투석대
    "業火球": None,      # 업화구
    "落石": None,        # 낙석
    "軍楽台": None,      # 군악대
    "浅瀬": "여울",       # 독음 천뢰 → 여울(의미)
    "長城": None,        # 장성
    "廟": None,          # 묘
    "市場": None,        # 시장
    "兵舎": "병영",       # 병영 (兵士=병사 충돌 회피; 독음 병사)
    "厩舎": "마사",       # 馬舍. 독음 「구사」는 한국어로 뜻이 안 통하고
                         # 「마구간」은 3자라 필드(2자 고정)를 넘는다 (2026-07-29 사용자 확정)
    "堤防": None,        # 제방
    "農場": None,        # 농장
    "魚市場": None,      # 어시장
    "軍事府": None,      # 군사부
    "穀倉": None,        # 곡창
    # ── 고급/PUK 시설 (0x2xxx 구역, 시설설정 메뉴가 읽는 복사본) ──
    "造幣": None,        # 조폐
    "闇市場": None,      # 암시장
    "大市場": None,      # 대시장
    "工房": None,        # 공방
    "錬兵所": "연병소",   # 錬→동 lib오류 회피(두음: 錬兵=연병)
    "符節台": None,      # 부절대
    "人材府": None,      # 인재부
    "外交府": None,      # 외교부
    "計略府": None,      # 계략부
    "造船": None,        # 조선 (화면 表記는 造船所, 데이터는 造船 2자)
    "軍屯農": None,      # 군둔농 (화면 表記는 軍屯田, 데이터는 軍屯農 3자)
}


def _is_cjk_byte_pair(b, i):
    if i < 1:
        return False
    hi, lo = b[i - 2], b[i - 1]
    try:
        ch = bytes([hi, lo]).decode("cp932")
    except Exception:
        return False
    return len(ch) == 1 and (0x4e00 <= ord(ch) <= 0x9fff)


def _has_reading(ent, after, window=14):
    """after부터 window 안에 카타카나 런(≥2자)이 시작하면 True = 이름 필드."""
    for s in range(after, min(after + window, len(ent) - 1)):
        cnt, j = 0, s
        while j < len(ent) - 1:
            try:
                ch = bytes(ent[j:j + 2]).decode("cp932")
            except Exception:
                break
            if len(ch) == 1 and (0x30a0 <= ord(ch) <= 0x30ff or ch in "ー・"):
                cnt += 1; j += 2
            else:
                break
        if cnt >= 2:
            return True
    return False


def find_facility_offsets(ent, region=(0xb82, 0x3800)):
    """(rel_off, jp, nbytes) 리스트. 모든 유효 이름 필드(복사본 포함).

    안전 3중 게이트: ①정본 full 매칭 ②null 종료 ③직전 비CJK(복합어 배제)
    ④이름\\0 뒤 카타카나 읽기 동반(설명문 끝 오검출 배제).
    """
    lo, hi = region
    out = []
    for jp in FACILITIES:
        pat = jp.encode("cp932") + b"\x00"
        i = lo
        while True:
            p = ent.find(pat, i, hi + len(pat))
            if p < 0:
                break
            if not _is_cjk_byte_pair(ent, p) and _has_reading(ent, p + len(pat)):
                out.append((p, jp, len(jp.encode("cp932"))))
            i = p + 1
    out.sort()
    return out


def kr_of(jp, to_hangul):
    """한글. override 있으면 사용, 없으면 독음. (kr, note)."""
    ov = FACILITIES.get(jp)
    if ov:
        if len(ov) != len(jp):
            return ov, "글자수 불일치(예산위험)"
        return ov, "의미역"
    kr = to_hangul(jp)
    if len(kr) != len(jp):
        return kr, "1:1불일치"
    return kr, ""
