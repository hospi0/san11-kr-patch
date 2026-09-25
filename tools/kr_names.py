# -*- coding: utf-8 -*-
"""이름 한글 변환의 단일 진실 공급원. 추출기·번역기·빌더가 전부 이걸 쓴다.

핵심 함정 세 가지를 여기서 한 번에 막는다:
  1. 姓과 名을 따로 변환하면 두음법칙이 잘못 걸린다(諸葛亮 → "제갈양").
     → 姓+名을 통째로 변환한 뒤 글자 수로 자른다. 1:1 대응 위반 0건 검증됨.
  2. 가이지([Gf0xx])는 hanja가 못 읽는다 → gaiji_map으로 실제 한자 복원 후 변환.
  3. 자동 독음이 관례와 어긋나는 글자·아예 이름이 아닌 보통명사가 있다
     → name_overrides에서 교정.

가나(히라가나·카타카나)가 섞인 필드는 이름이 아니라 placeholder다(史実０１·
イベ６４·いに３３). 한자가 아니므로 그대로 통과시킨다.
"""
import re

from gaiji_map import GAIJI_MAP
from name_overrides import NAME_OVERRIDES, HANJA_OVERRIDES

import hanja

GAIJI_RE = re.compile(r"\[G(f0[0-9a-f]{2}|f1[0-9a-f]{2})\]")
KANA_RE = re.compile(r"[ぁ-ゖァ-ヺー０-９Ａ-Ｚ]")


def restore_gaiji(s):
    """[Gf07d] → 瓘. 비정 안 된 가이지는 그대로 남겨 눈에 띄게 한다."""
    return GAIJI_RE.sub(lambda m: GAIJI_MAP.get(int(m.group(1), 16), m.group(0)), s)


def to_hangul(s):
    """한자열 → 한글. **단어 단위**로 호출해야 두음법칙이 맞는다."""
    if not s:
        return ""
    out = hanja.translate(s, "substitution")
    if len(out) != len(s):
        return out                      # 1:1 깨짐 → 호출부가 경고 처리
    for h, ko in HANJA_OVERRIDES.items():
        if h in s:
            out = "".join(ko if s[i] == h else out[i] for i in range(len(s)))
    return out


def is_placeholder(sei, mei):
    """史実０１ / イベ６４ / いに３３ 류 = 실존 인물 아님."""
    return bool(KANA_RE.search(sei + mei))


def translate_name(sei, mei, azana):
    """(姓, 名, 字) 일본어 → (姓KR, 名KR, 字KR, 경고). 입력은 [Gf0xx] 표기 가능.

    경고가 비어있지 않으면 그 이름은 사람이 확인해야 한다.
    """
    j_sei, j_mei, j_az = (restore_gaiji(x or "") for x in (sei, mei, azana))

    if GAIJI_RE.search(j_sei + j_mei + j_az):
        return j_sei, j_mei, j_az, "미비정 가이지"

    if is_placeholder(j_sei, j_mei):
        # 한자 부분만 읽고 가나·전각숫자는 그대로 둔다
        k_sei = "".join(c if KANA_RE.match(c) else to_hangul(c) for c in j_sei)
        return k_sei, j_mei, "", ""

    full = j_sei + j_mei
    ov = NAME_OVERRIDES.get(full)
    if ov:
        k_sei, k_mei = ov
    else:
        k_full = to_hangul(full)
        if len(k_full) != len(full):
            return j_sei, j_mei, j_az, "길이 불일치 %r→%r" % (full, k_full)
        k_sei, k_mei = k_full[:len(j_sei)], k_full[len(j_sei):]

    k_az = to_hangul(j_az) if j_az else ""

    bad = [c for c in (k_sei + k_mei + k_az)
           if not ("가" <= c <= "힣" or "０" <= c <= "９")]
    if bad:
        return k_sei, k_mei, k_az, "독음실패 " + "".join(bad)
    return k_sei, k_mei, k_az, ""
