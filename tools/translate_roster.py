# -*- coding: utf-8 -*-
"""무장 로스터 900명 한글 독음 번역본 생성.

핵심 함정 두 가지를 피한다:
  1. 姓과 名을 따로 변환하면 두음법칙이 잘못 걸린다(諸葛亮 → "제갈양").
     → 姓+名을 통째로 변환한 뒤 글자 수로 자른다. 1:1 대응 위반 0건 검증됨.
  2. 게임 데이터의 가이지([Gf0xx])는 hanja가 못 읽는다.
     → gaiji_map으로 실제 한자를 복원한 뒤 변환.

字(あざな)는 그 자체가 독립된 단어이므로 따로 변환한다(두음법칙 적용 맞음).

사용: python tools/translate_roster.py work/roster_ram.txt work/roster_kr.tsv
"""
import re, sys, hanja
from gaiji_map import GAIJI_MAP
from name_overrides import NAME_OVERRIDES, HANJA_OVERRIDES

GAIJI_RE = re.compile(r"\[G(f0[0-9a-f]{2}|f1[0-9a-f]{2})\]")


def restore_gaiji(s):
    """[Gf07d] → 瓘. 비정 안 된 가이지는 그대로 두어 눈에 띄게 한다."""
    def sub(m):
        code = int(m.group(1), 16)
        return GAIJI_MAP.get(code, m.group(0))
    return GAIJI_RE.sub(sub, s)


def to_hangul(s):
    """한자열 → 한글. 단어 단위로 호출해야 두음법칙이 맞는다."""
    if not s:
        return ""
    out = hanja.translate(s, "substitution")
    # 관례 교정: 라이브러리 독음이 삼국지 국내 표기와 다른 글자
    for h, ko in HANJA_OVERRIDES.items():
        if h in s:
            out = "".join(ko if s[i] == h else out[i] for i in range(len(s)))
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "work/roster_ram.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/roster_kr.tsv"

    rows = []
    for line in open(src, encoding="utf-8"):
        if line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        rows.append(p)

    out = []
    warn = []
    for idx, sei, mei, azana, yomi in rows:
        if not (sei or mei):
            continue

        # 「史実０１」류 = 실존인물 아닌 이벤트용 placeholder
        if re.search(r"[０-９]", sei + mei):
            k_sei = to_hangul(sei) if sei else ""
            k_mei = mei                      # 전각숫자는 그대로 (게임이 번호로 씀)
            k_az = ""
            out.append((idx, sei, mei, azana, yomi, k_sei, k_mei, k_az, "placeholder"))
            continue

        j_sei, j_mei, j_az = (restore_gaiji(x) for x in (sei, mei, azana))
        full = j_sei + j_mei

        if GAIJI_RE.search(full + j_az):
            warn.append((idx, full, j_az, "미비정 가이지"))

        # 수동 지정 이름이 있으면 우선
        ov = NAME_OVERRIDES.get(full)
        if ov:
            k_sei, k_mei = ov
        else:
            k_full = to_hangul(full)
            if len(k_full) != len(full):
                warn.append((idx, full, k_full, "길이 불일치"))
                k_sei, k_mei = k_full[:len(j_sei)], k_full[len(j_sei):]
            else:
                k_sei, k_mei = k_full[:len(j_sei)], k_full[len(j_sei):]

        k_az = to_hangul(j_az) if j_az else ""

        # 한자가 남았으면 = 독음 실패
        for label, ko in (("姓名", k_sei + k_mei), ("字", k_az)):
            bad = [c for c in ko if not ("가" <= c <= "힣" or c in "０１２３４５６７８９")]
            if bad:
                warn.append((idx, full + "/" + j_az, "".join(bad), label + " 독음실패"))

        out.append((idx, j_sei, j_mei, j_az, yomi, k_sei, k_mei, k_az, ""))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("# idx\t姓\t名\t字\t読み\t姓KR\t名KR\t字KR\t비고\n")
        for r in out:
            f.write("\t".join(str(x) for x in r) + "\n")

    print("%s 저장: %d명" % (dst, len(out)))
    print("경고 %d건" % len(warn))
    for w in warn[:30]:
        print("   ", w)


main()
