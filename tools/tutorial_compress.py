# -*- coding: utf-8 -*-
"""entry4 튜토리얼(work/e4_tutorial.tsv) 번역문의 안전한 1차 압축.

★★help_compress.py를 그대로 쓰면 안 된다 — 이 텍스트는 idx=3 UI 버튼바 힌트가 아니라
**신하가 군주(폐하)에게 말하는 극중 대사**다. "-습니다→-음" 명사형 축약을 돌려보니
"축하드립니다"→"축하드림", "알겠습니다"→"알겠음"처럼 존댓말 종결어미 자체가 깨져서
대사 톤이 반말/문자메시지투로 무너진다(962줄 적중, 6,458B 절감이지만 대부분 오역급 어색함).
**존댓말 종결은 이 텍스트에서 "불필요한 존칭"이 아니라 화자 관계상 필요한 문법이다.**

강조부사("정말로/참으로/그야말로/실로" 등)도 마찬가지로 손대지 않는다 — 표본 확인 결과
전부 극중 감정 표현(진심 어린 감사, 탄식, 비꼼)이라 UI 설명문의 군더더기와 다르다.

여기서 압축하는 건 **문법적으로 안전하게 기계 변환되는 것만**이다:
  1. "을 것입니다" → "습니다"          (추측형 어미 제거, 25회 확인)
  2. ㄹ받침 종성 + " 것입니다" → 받침 ㄹ→ㅂ + "니다"  (같은 추측형의 받침 융합판, 64회)
  3. "고 있겠습니다" → "겠습니다"      (미래 약속 표현의 중복 진행상 제거, 25회 확인,
     "다음 도전을 기다리고 있겠습니다"류 반복 상투구가 대부분)
전부 존댓말 종결(-습니다/-ㅂ니다)은 그대로 유지한 채 의미상 군더더기만 뺀다.
"""
import re

JONG_L, JONG_B = 8, 17    # 종성 인덱스: ㄹ=8, ㅂ=17


MEDIAL_U = 13   # 중성 인덱스: ㅜ


def _l_to_b(m):
    """ㄹ받침 음절 + ' 것입니다' → 받침을 ㅂ로 바꾸고 '니다'를 붙인다.
    될→됩+니다=됩니다 / 할→합+니다=합니다 (help_compress._nominalize와 같은 원리).

    ⚠️중성이 ㅜ인 경우(예: 쉬울·버거울)는 건드리지 않는다 — **적발된 비문 버그**:
    "쉬울 것입니다"를 기계적으로 "쉬웁니다"로 바꿨는데, "쉽다"는 ㅂ불규칙 활용이라
    실제 존댓말은 "쉽습니다"다(어간이 "쉽"이지 "쉬우"가 아님). 문제는 규칙 동사
    "배우다→배울→배웁니다"(정답)와 표면형이 완전히 같아서 **글자만 보고는 구별이
    안 된다** — 사전 없이는 못 푸는 문제라 아예 자동변환 대상에서 뺀다(3건 실제 발견
    후 수동 수정: 쉬울→쉬웁니다✗/쉽습니다✓ ×2, 버거울→버거웁니다✗/버겁습니다✓)."""
    ch = m.group(1)
    o = ord(ch) - 0xAC00
    if o % 28 != JONG_L:
        return m.group(0)
    if (o // 28) % 21 == MEDIAL_U:
        return m.group(0)
    return chr(0xAC00 + o - JONG_L + JONG_B) + "니다"


RULES = [
    (r"을\s*것입니다", "습니다"),
    (r"([가-힣])\s*것입니다", _l_to_b),
    (r"고\s*있겠습니다", "겠습니다"),
]


def compress(s):
    for pat, rep in RULES:
        s = re.sub(pat, rep, s)
    return s


def body_bytes(s):
    t = re.sub(r"\{[^}]+\}", "", s)
    return sum(2 if "가" <= c <= "힣" else 1 for c in t)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "work/e4_tutorial.tsv"
    lines = []
    changed = 0
    saved = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            if not raw or raw.startswith("#") or raw.startswith("block\t"):
                lines.append(raw)
                continue
            parts = raw.split("\t")
            if len(parts) < 5 or not parts[4].strip():
                lines.append(raw)
                continue
            kr = parts[4]
            new_kr = compress(kr)
            if new_kr != kr:
                changed += 1
                saved += body_bytes(kr) - body_bytes(new_kr)
                parts[4] = new_kr
            lines.append("\t".join(parts))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("압축 적용:", changed, "줄 / 절감:", saved, "B")
