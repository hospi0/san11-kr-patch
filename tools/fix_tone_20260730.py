"""2026-07-30 사용자 제보 3건 수정.

1) 시설명 「구사」 → 「마사」
   work/idx5_extra_kr.tsv 의 fac 35/58/59 (厩舎 Lv1~3). 예산 8B라 「마구간」(10B)은 불가,
   tools/facilities.py 가 이미 쓰고 있는 「마사」로 통일한다.

2) 아이템 분류 「장병기」 → 「장병」
   長柄. tools/ui_overrides.py(재생성 소스) + work/ui_kr.tsv(빌더가 읽는 파일) 양쪽.
   예산 8B, 「장병」 4B.

3) 장비(무장 ID 432) 말투 — 군주에게 하는 보고가 해라체라 건방지게 들린다.
   JP 원문의 「〜ぜ／〜な」는 거친 말씨이되 주군에게 하는 말이므로 **하오체**로 통일.
   ⚠️예외로 남기는 것: 등용 거절(129)·추방(327)·포로석방(340)은 상대가 주군이 아니거나
     이미 결별한 상황이고, 혼잣말(261·223 뒷줄)은 반말이 자연스럽다.
     외교 사절/설전(600~711, blk4)도 상대가 타 세력이라 손대지 않는다.
"""
import io
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 1) 구사 → 마사 ────────────────────────────────────────────────────
FAC = {"구사 Lv1": "마사 Lv1", "구사 Lv2": "마사 Lv2", "구사 Lv3": "마사 Lv3"}

# ── 3) 장비 대사 (KR 필드 안의 {04}=432 분기 텍스트) ────────────────────
#     (blk0 idx, 기존, 신규)
ZHANGFEI = [
    (68,  "{V:3c32}에 갔다 오겠어",
          "{V:3c32}에 갔다 오겠소"),
    (79,  "인재라는 건 없더군{N}그래도 {V:5a32} 발견했어",
          "인재라는 건 없더구려{N}그래도 {V:5a32} 발견했소"),
    (112, "목에 밧줄을 감아서라도{N}데려와 주지！",
          "목에 밧줄을 감아서라도{N}데려오겠소！"),
    (118, "이 {V:96}1x장비{V:96}0x님이 가담한 이상{N}가는 곳마다 적이 없을 것이다！",
          "이 {V:96}1x장비{V:96}0x님이 가담한 이상{N}가는 곳마다 적이 없을 것이오！"),
    (135, "고맙다！{N}술값이 생겼구나！",
          "고맙소！{N}술값이 생겼구려！"),
    (143, "고맙다！{N}좋은 걸 받았구나！",
          "고맙소！{N}좋은 걸 받았소！"),
    (178, "{V:5032} 만드는 건{N}이 {V:0a32}님께 맡겨라！",
          "{V:5032} 만드는 건{N}이 {V:0a32}님께 맡겨 두시오！"),
    (185, "{V:5032}{N}만들어 주었다！",
          "{V:5032}{N}만들어 놓았소！"),
    (191, "군량, 사 뒀다！",
          "군량, 사 뒀소！"),
    (196, "군량 팔이 따위{N}내 일이 아니지",
          "군량 팔이 따위{N}내가 할 일은 아니오"),
    (209, "{V:8c}라니……{N}그게 대체 뭐냐",
          "{V:8c}라니……{N}그게 대체 뭐요"),
    (215, "어디 보자……{V:8c}였나？{N}연구, 끝났다！",
          "어디 보자……{V:8c}였나？{N}연구, 끝났소！"),
    (223, "팔팔한 병사가 모였다！{N}당장 훈련이나 해볼까？",
          "팔팔한 병사가 모였소！{N}당장 훈련이나 시켜 볼까？"),
    (231, "이호……뭐였더라？{N}잠깐 다녀오마",
          "이호……뭐였더라？{N}잠깐 다녀오겠소"),
    (247, "호랑이가 어쨌다더라？{N}뭐, 일단 다녀오마",
          "호랑이가 어쨌다더라？{N}뭐, 일단 다녀오겠소"),
    (299, "뭐, 잘 모르겠지만{N}나눠 뒀다",
          "뭐, 잘 모르겠지만{N}나눠 뒀소"),
]


def backup(path, tag):
    dst = path + ".bak_" + tag
    if not os.path.exists(dst):
        shutil.copy2(path, dst)


def fix_idx5_extra():
    p = os.path.join(ROOT, "work/idx5_extra_kr.tsv")
    backup(p, "tone0730")
    lines = io.open(p, encoding="utf-8").read().split("\n")
    n = 0
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if len(c) >= 7 and c[6] in FAC:
            c[6] = FAC[c[6]]
            lines[i] = "\t".join(c)
            n += 1
    io.open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    print("idx5_extra_kr.tsv  구사→마사 %d곳" % n)
    return n


def fix_ui():
    n = 0
    p = os.path.join(ROOT, "work/ui_kr.tsv")
    backup(p, "tone0730")
    lines = io.open(p, encoding="utf-8").read().split("\n")
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if len(c) >= 8 and c[2] == "長柄" and c[7] == "장병기":
            c[7] = "장병"
            lines[i] = "\t".join(c)
            n += 1
    io.open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    print("ui_kr.tsv          長柄 장병기→장병 %d곳" % n)

    p = os.path.join(ROOT, "tools/ui_overrides.py")
    src = io.open(p, encoding="utf-8").read()
    old = '"長柄": "장병기",'
    if old in src:
        io.open(p, "w", encoding="utf-8", newline="").write(
            src.replace(old, '"長柄": "장병",'))
        print("ui_overrides.py    長柄 장병기→장병")
    return n


def fix_dialogue():
    p = os.path.join(ROOT, "work/e4_dialogue.tsv")
    backup(p, "tone0730")
    lines = io.open(p, encoding="utf-8").read().split("\n")
    byidx = {}
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if len(c) >= 5 and c[0] == "0" and c[1].isdigit():
            byidx[int(c[1])] = i

    delta = 0
    miss = []
    for idx, old, new in ZHANGFEI:
        i = byidx.get(idx)
        if i is None:
            miss.append(idx)
            continue
        c = lines[i].split("\t")
        marker = "{04}=432" + old
        if marker not in c[4]:
            miss.append(idx)
            continue
        c[4] = c[4].replace(marker, "{04}=432" + new)
        lines[i] = "\t".join(c)
        delta += len(new.encode("utf-8")) - len(old.encode("utf-8"))
    if miss:
        print("!! 미적용 idx: %s" % miss)
        return False
    io.open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    print("e4_dialogue.tsv    장비(432) 말투 %d줄 (UTF-8 기준 %+dB)"
          % (len(ZHANGFEI), delta))
    return True


if __name__ == "__main__":
    fix_idx5_extra()
    fix_ui()
    ok = fix_dialogue()
    sys.exit(0 if ok else 1)
