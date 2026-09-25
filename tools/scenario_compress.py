# -*- coding: utf-8 -*-
"""시나리오 개요·공략문(work/scenario_kr.tsv) 번역문을 슬롯 예산(overview 282B /
brief 311B)에 맞춰 기계적으로 1차 압축한다.

★help_compress.py(idx=3 도움말)와 문체가 다르다 — 도움말은 하십시오체(합니다/습니다)라
명사형으로 깎았지만, 시나리오는 이미 평서체(-다)로 번역돼 있어 그 규칙이 하나도 안 걸린다.
여기서 노리는 건 존댓말이 아니라 **반복되는 완곡 어미**(-고 싶다, -것이다, -라 할 수 있다)다.
전수 스캔 결과: "고 싶다" 62회, "것이다" 49회, "라 할 수 있다" 20회 — 압도적 상위 3개.

규칙은 전부 **문장 종결 위치**에서만 걸리도록 `.`(마침표) 앞에만 앵커한다. 일반화가 위험한
동사 활용(예: "할 것이다" → 어간마다 불규칙 활용이 달라 기계적으로 못 바꿈)은 규칙에서
뺐다 — san11 프로젝트 교훈: 규칙 하나가 여러 줄을 동시에 망가뜨린 전례(help_compress.py
의 "않습니다→안 함" 비문 사고) 때문에, 문법이 균일하게 보장되는 경우만 규칙화했다.
"""
import re


def _copula(m):
    """`(이)라 할 수 있다` → `(이)다`. "이"의 유무는 원문이 이미 받침 규칙을 반영해
    인코딩하고 있으므로 그대로 캡처만 옮기면 된다(부족이라→부족이다 / 인재라→인재다)."""
    has_i = m.group(1) or ""
    term = m.group(2) or ""
    return has_i + "다" + term


# 정확히 반복되는 시나리오 도입 상투구 — 전수 스캔으로 찾음(38/16/12/5회). 리터럴
# 문자열 치환이라 일반화 위험이 없다(내가 양쪽을 다 쓴 고정 문장이지, 변수가 낀 패턴이 아님).
LITERAL_RULES = [
    ("외교 관계, 국력 모두 전 세력이 비등한 상태에 있다.", "외교·국력 모두 전 세력이 비등하다."),
    ("다른 제후와 동맹하여 황건 타도를 목표로 하게 된다.", "다른 제후와 동맹해 황건 타도가 목표다."),
    ("반동탁 연합에 가담하여 제후들과 함께 동탁 타도를 목표로 하게 된다.",
     "반동탁 연합에 가담해 제후들과 함께 동탁 타도가 목표다."),
    ("대부분의 세력과 마찬가지로 하진 타도를 목표로 한다.", "대부분의 세력과 마찬가지로 하진 타도가 목표다."),
]

# (정규식, 치환) — 순서 중요: 긴 패턴을 먼저.
RULES = [
    (r"고\s*싶은\s*참이다\.", "자."),
    (r"고\s*싶다\.", "자."),
    (r"(이)?라\s*할\s*수\s*있다(\.)?", _copula),
    (r"일\s*것이다\.", "이다."),
    (r"것이\s*좋을\s*것이다\.", "것이 좋다."),
    (r"해야\s*할\s*것이다\.", "해야 한다."),
    (r"그렇다고는\s*해도", "다만"),
    # idx10/18 형남 4국 클러스터 — 8줄에 걸쳐 거의 동일한 상투구(어미만 미세하게 다름).
    (r"주[위변]는\s*우호적인\s*세력뿐이지만,?\s*아무것도\s*하지\s*않고\s*지내면\s*"
     r"천하의\s*형세는\s*(정해지고\s*만다|정해져\s*버린다|결정되어\s*버린다)\.",
     "주위는 우호 세력뿐이나, 방심하면 천하 형세가 정해진다."),
    (r"조조가\s*남하하기\s*전에\s*형남은\s*확보해두자\.", "조조 남하 전에 형남을 확보하자."),
    (r"조조와\s*손권이\s*다투는\s*(사이에|동안),?\s*형남을\s*(눌러\s*두자|확보해\s*두자)\.",
     "조조·손권이 다투는 동안 형남을 확보하자."),
    (r"지략\s*면에서\s*다소\s*어려움이\s*있지만", "지략이 다소 부족하나"),
    (r"\s+", " "),
]


def compress(s):
    for old, new in LITERAL_RULES:
        s = s.replace(old, new)
    for pat, rep in RULES:
        s = re.sub(pat, rep, s)
    return s.strip()


def body_bytes(s):
    """토큰 없는 순수 한글/ASCII 텍스트의 인코딩 바이트 수 근사(한글 2B, 그 외 1B).
    실제 게임 인코딩(tools/encoding.py의 Codec)과 동일한 규칙 — ASCII는 반각 1B,
    완성형 한글은 전용 2B 코드. [Gxxxx] 같은 플레이스홀더는 ASCII라 이미 1B/자로 맞다."""
    return sum(2 if "가" <= c <= "힣" else 1 for c in s)


if __name__ == "__main__":
    import sys
    CAP = {"overview": 282, "brief": 311}
    path = sys.argv[1] if len(sys.argv) > 1 else "work/scenario_kr.tsv"
    lines = []
    changed = 0
    still_over = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            if not raw or raw.startswith("#") or raw.startswith("idx\t"):
                lines.append(raw)
                continue
            parts = raw.split("\t")
            idx, section, slot, flag, jp, kr = parts[:6]
            if section in CAP and kr:
                new_kr = compress(kr)
                if new_kr != kr:
                    changed += 1
                    kr = new_kr
                cap = CAP[section]
                if body_bytes(kr) + 1 > cap:
                    still_over.append((idx, section, slot, body_bytes(kr), cap))
            lines.append("\t".join([idx, section, slot, flag, jp, kr]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("압축 적용:", changed, "줄")
    print("압축 후에도 예산 초과:", len(still_over), "줄")
    for o in still_over:
        print(" ", o)
