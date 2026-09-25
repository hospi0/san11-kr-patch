# -*- coding: utf-8 -*-
"""UI 문자열 번역본 생성 (SLPM_667.01, 진짜 텍스트 3구역 2,600여개).

UI 한자어는 **독음이 곧 한국어 번역**이라 로스터와 같은 파이프라인이 통한다
(決定→결정, 初期化→초기화, 追放武将選択→추방무장선택). 그래서:
  1. ui_overrides.UI_OVERRIDES에 있으면 그걸 쓴다 (수작업 번역·교정)
  2. **한자 구간만 독음으로 바꾸고 나머지는 그대로 둔다**
     %3d年%2d月%2d日 → %3d년%2d월%2d일 / 技巧Ｐ → 기교Ｐ / ×·○·１２ → 그대로
     printf 서식·전각기호·숫자는 손대면 안 되므로 보존이 곧 정답이다.
  3. **가나(히라가나·가타카나)가 남으면 TODO** — 기계로 못 한다.
     히라가나 = 일본어 문장(어순·조사가 달라 재작성 필요),
     가타카나 = 외래어 음차(ロード→로드)라 사람이 정해야 한다.

예산: in-place라 한국어가 원래 슬롯에 들어가야 한다.
  한글바이트 + 1(종료자) <= 원문바이트 + 뒤널
전수 검사해서 초과분은 경고로 낸다. printf 포맷(%d·%s)·제어문자는 보존해야 하므로
자동 번역 대상에서 뺀다.

사용: python tools/translate_ui.py work/ui.tsv work/ui_kr.tsv
"""
import re
import sys

import hanja

from name_overrides import HANJA_OVERRIDES
from ui_overrides import UI_OVERRIDES

KANJI_RUN = re.compile(r"[一-鿿]+")
KANA = re.compile(r"[ぁ-ゖァ-ヺー]")
# 수사(숫자 리터럴 또는 printf 정수/문자열 서식)로 끝나는 앞부분 → 뒤 한자는 단위 명사
COUNTER_PRE = re.compile(r"(?:[0-9０-９]|%[-0-9.*]*[dsux])$")


def to_hangul(s, initial=True):
    """한자열 → 한글.

    initial=False면 **어중** 독음을 준다. 한자 구간만 잘라 번역하면 그 구간이
    전부 어두 취급을 받아 두음법칙이 잘못 걸린다(%3d年 → "%3d연", 190年 → "190연").
    앞에 더미 한자를 붙여 번역한 뒤 첫 음절을 떼면 어중 독음이 나온다.
      年: 단독 '연' / 一年 → '일년' → '년'
    """
    if not s:
        return ""
    src = ("一" + s) if not initial else s
    out = hanja.translate(src, "substitution")
    if len(out) != len(src):
        return None
    if not initial:
        out = out[1:]
    for h, ko in HANJA_OVERRIDES.items():
        if h in s:
            out = "".join(ko if s[i] == h else out[i] for i in range(len(s)))
    return out


def kr_bytes(s):
    """encoding.Codec.encode()와 **같은 규칙**으로 센 바이트 길이.

    여기가 어긋나면 예산 검사가 거짓말을 한다. 실제로 두 번 어긋났다:
      ① 코덱이 ASCII를 전각(2B)으로 보내는데 여기선 1B로 세서 "예산초과 0"이라고
         **거짓 통과**시켰다(세션3).
      ② 제어코드 토큰 `{ESC}`(=0x1b 1B)·`{N}`(=0x0a 1B)을 글자 그대로 5B·3B로 세서
         멀쩡한 문자열을 **거짓 초과**로 떨어뜨렸다(세션5).
    반각(1B): 공백 0x20 · ASCII 0x21-0x7E · 반각 카타카나 U+FF61-FF9F.
    """
    n = 0
    for part in re.split(r"(\{ESC\}|\{N\})", s):
        if part in ("{ESC}", "{N}"):            # 제어코드 = 1바이트
            n += 1
            continue
        for c in part:
            o = ord(c)
            n += 1 if (c == " " or 0x21 <= o <= 0x7E or 0xFF61 <= o <= 0xFF9F) else 2
    return n


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "work/ui.tsv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/ui_kr.tsv"

    rows = []
    for line in open(src, encoding="utf-8"):
        if line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 7:
            rows.append(p)

    out = []
    n_ov = n_auto = n_todo = 0
    over = []
    for off, va, s, blen, pad, bud, np_ in rows:
        bud = int(bud)
        kr, how = "", ""

        if s in UI_OVERRIDES:
            kr, how = UI_OVERRIDES[s], "override"; n_ov += 1
        elif KANA.search(s):
            # 가나가 있으면 기계 번역 불가 — 사람이 해야 한다
            how = "TODO(%s)" % ("히라가나" if re.search(r"[ぁ-ゖ]", s) else "가타카나")
            n_todo += 1
        else:
            # 한자 구간만 독음으로, 나머지(서식·기호·숫자)는 그대로
            bad = []

            def sub(m):
                # **수사 바로 뒤**의 한자는 단위 명사라 어두가 아니다: %3d年="3년", 190年="190년".
                # 그 외(공백·기호·글자 뒤)는 새 어절이므로 어두:
                #   190年 1月 曹操挙兵 → 조조거병 (공백 뒤)
                #   顔CG変更年齢 → 변경연령 (글자 뒤. "년령"이 아니다)
                pre = s[:m.start()]
                initial = not (COUNTER_PRE.search(pre))
                k = to_hangul(m.group(0), initial=initial)
                if not k or not all("가" <= c <= "힣" for c in k):
                    bad.append(m.group(0))
                    return m.group(0)
                return k

            k = KANJI_RUN.sub(sub, s)
            if bad:
                how = "TODO(독음실패 %s)" % "".join(bad); n_todo += 1
            elif k == s:
                kr, how = s, "keep"        # 한자가 없다 = 기호·숫자 = 그대로 두면 정답
                n_auto += 1
            else:
                kr, how = k, "auto"; n_auto += 1

        note = ""
        if kr and kr_bytes(kr) + 1 > bud:
            note = "예산초과 %dB+1 > %dB" % (kr_bytes(kr), bud)
            over.append((s, kr, kr_bytes(kr), bud))
        out.append((off, va, s, blen, pad, str(bud), np_, kr, how, note))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("# off\tVA\t원문\t바이트\t뒤널\t예산\t포인터수\t한글\t경로\t비고\n")
        for r in out:
            f.write("\t".join(r) + "\n")

    print("%s 저장: %d" % (dst, len(out)))
    print("  override %d / auto %d / TODO %d" % (n_ov, n_auto, n_todo))
    print("  예산초과 %d" % len(over))
    for o in over[:20]:
        print("    %-20s -> %-20s %dB > %dB" % o)


main()
