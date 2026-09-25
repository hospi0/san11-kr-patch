# -*- coding: utf-8 -*-
"""兵舎=병사→병영 · 鍛冶=단야→대장간 용어 교정 (2026-07-21).

주의(scan_heisha.py 교훈):
  · '병사'는 兵士(soldier)의 정상역이기도 하다 → **한 줄에 兵士(유지)와 兵舎(교정)가
    공존**한다. 일괄 치환 금지. 아래는 원문 대조로 확정한 위치별 교정만 한다.
  · 병사(개음절)→병영(받침) 이므로 **조사가 바뀐다**(를→을·가→이·는→은·와→과).
  · '단야'는 오직 鍛冶의 독음뿐 → 전역 치환 안전. 시설참조토큰 I00000203병사(=兵舎)·
    I00000111단야(=鍛冶)도 ID가 시설을 특정하므로 전역 안전.

바이트 예산:
  · 한글 1음절=2B, 반각(ASCII/공백)=1B (encoding.py).
  · 병사→병영: 길이 동일(예산 무변).
  · 단야→대장간: +2B/회. entry4(LS11) 여유 702B·LZ압축 → 안전. idx5 시설 Lv명은
    예산 8→10 필요(레코드 내 카타카나 읽기 カジ만 ジ로 바뀌고 종료자·후속필드는 보존,
    한글 화면엔 안 보이는 정렬용 필드 — 실측 hex로 확인).
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")


def bwidth(s):
    """encoding.py 규칙과 동일한 바이트폭."""
    n = 0
    for ch in s:
        o = ord(ch)
        if ch == ' ' or 0x21 <= o <= 0x7E or 0xFF61 <= o <= 0xFF9F:
            n += 1
        else:
            n += 2
    return n


# ── 전역(해당 파일 전체에 안전) ──────────────────────────────────────
GLOBAL = {
    "work/e4_dict.tsv": [
        ("I00000203병사", "I00000203병영"),   # 兵舎 시설참조토큰
        ("단야", "대장간"),                     # 鍛冶 (독음, 전역안전)
    ],
    "work/e4_tutorial.tsv": [
        # 단야 없음(이미 대장간). 兵舎는 {V:96} 마크업이라 조사 때문에 아래 라인별로.
    ],
}

# ── 라인별(조사 포함, 원문 대조로 확정) ──────────────────────────────
# (파일, 1-based 라인, old, new, 기대횟수)
PER_LINE = [
    # e4_dict.tsv — 兵舎(「병사」) 교정, 兵士(병사)는 건드리지 않음
    ("work/e4_dict.tsv", 512, "「병사」를 개발해서", "「병영」을 개발해서", 1),
    ("work/e4_dict.tsv", 514, "「병사」（", "「병영」（", 1),
    ("work/e4_dict.tsv", 582, "또한 「병사」의 {1c}[{1c}I00000204Lv{1c}]가",
     "또한 「병영」의 {1c}[{1c}I00000204Lv{1c}]가", 1),   # 도시의「병사」(兵士)는 유지
    ("work/e4_dict.tsv", 636, "「병사」의 수와 같은 횟수만큼", "「병영」의 수와 같은 횟수만큼", 1),
    ("work/e4_dict.tsv", 636, "다른 세력의 「병사」를 파괴하면", "다른 세력의 「병영」을 파괴하면", 1),
    ("work/e4_dict.tsv", 636, "「병사」의 소속 도시에서", "「병영」의 소속 도시에서", 1),

    # e4_tutorial.tsv — {V:96}6x병사{V:96}0x = 兵舎, 조사 교정
    ("work/e4_tutorial.tsv", 75, "「{V:96}6x병사{V:96}0x」는 병사를 모으는",
     "「{V:96}6x병영{V:96}0x」은 병사를 모으는", 1),                      # 뒤 병사(兵) 유지
    ("work/e4_tutorial.tsv", 75, "개발된 「{V:96}6x병사{V:96}0x」의 수만큼",
     "개발된 「{V:96}6x병영{V:96}0x」의 수만큼", 1),
    ("work/e4_tutorial.tsv", 76, "「{V:96}6x병사{V:96}0x」가 없는",
     "「{V:96}6x병영{V:96}0x」이 없는", 1),
    ("work/e4_tutorial.tsv", 131, "「{V:96}6x병사{V:96}0x」를 개발하여",
     "「{V:96}6x병영{V:96}0x」을 개발하여", 1),
    ("work/e4_tutorial.tsv", 134, "「{V:96}6x병사{V:96}0x」의 수만큼",
     "「{V:96}6x병영{V:96}0x」의 수만큼", 1),
    ("work/e4_tutorial.tsv", 135, "많은 「{V:96}6x병사{V:96}0x」를{N}개발",
     "많은 「{V:96}6x병영{V:96}0x」을{N}개발", 1),                        # 앞 병사(兵) 유지
    ("work/e4_tutorial.tsv", 136, "「병사」가 하나 있다", "「병영」이 하나 있다", 1),
    ("work/e4_tutorial.tsv", 395, "병사와 마구간을", "병영과 마구간을", 1),
    ("work/e4_tutorial.tsv", 396, "농장, 병사, 대장간", "농장, 병영, 대장간", 1),
]

# ── idx5_extra_kr.tsv (탭 컬럼: table k field off budget jp kr) ────────
# (라인, 새 budget, jp확인, old_kr, new_kr)
IDX5 = [
    (33, 8,  "兵舎 Lv1", "병사 Lv1", "병영 Lv1"),
    (44, 8,  "兵舎 Lv2", "병사 Lv2", "병영 Lv2"),
    (45, 8,  "兵舎 Lv3", "병사 Lv3", "병영 Lv3"),
    (35, 10, "鍛冶 Lv1", "단야 Lv1", "대장간 Lv1"),
    (46, 10, "鍛冶 Lv2", "단야 Lv2", "대장간 Lv2"),
    (47, 10, "鍛冶 Lv3", "단야 Lv3", "대장간 Lv3"),
]

# ── ui_kr.tsv (탭 컬럼: off off2 jp .. budget=5 .. kr=7 mode) ──────────
# (라인, jp확인, old_kr, new_kr)
UI = [
    (607,  "空兵舎",    "공병사",   "공병영"),
    (1086, "空き兵舎数", "빈병사수", "빈병영수"),
    (2313, "兵舎",      "병사",     "병영"),
    (2578, "兵舎",      "병사",     "병영"),
    (1978, "鍛冶",      "단야",     "대장간"),
    (2579, "鍛冶",      "단야",     "대장간"),
]

# ── 단순 문자열 파일 (facilities.py, ui_overrides.py) ────────────────
SIMPLE = [
    ("tools/facilities.py", '"兵舎": None,        # 병사',
     '"兵舎": "병영",       # 병영 (兵士=병사 충돌 회피; 독음 병사)'),
    ("tools/ui_overrides.py", '"空き兵舎数": "빈병사수"', '"空き兵舎数": "빈병영수"'),
]


def patch_tsv_lines(rel, edits):
    p = os.path.join(ROOT, rel)
    lines = open(p, encoding="utf-8").read().split("\n")
    for (ln, old, new, cnt) in edits:
        s = lines[ln - 1]
        c = s.count(old)
        assert c == cnt, "%s L%d: '%s' %d회(기대 %d)" % (rel, ln, old, c, cnt)
        lines[ln - 1] = s.replace(old, new)
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))


def patch_global(rel, subs):
    p = os.path.join(ROOT, rel)
    txt = open(p, encoding="utf-8").read()
    for old, new in subs:
        n = txt.count(old)
        txt = txt.replace(old, new)
        print("  [전역] %-24s %d회" % ("%s→%s" % (old, new), n))
    open(p, "w", encoding="utf-8", newline="").write(txt)


def patch_idx5():
    p = os.path.join(ROOT, "work/idx5_extra_kr.tsv")
    lines = open(p, encoding="utf-8").read().split("\n")
    for (ln, newbud, jp, oldkr, newkr) in IDX5:
        cols = lines[ln - 1].split("\t")
        assert cols[5] == jp, "idx5 L%d jp=%r != %r" % (ln, cols[5], jp)
        assert cols[6] == oldkr, "idx5 L%d kr=%r != %r" % (ln, cols[6], oldkr)
        b = bwidth(newkr)
        assert b <= newbud, "idx5 L%d %r=%dB>예산%d" % (ln, newkr, b, newbud)
        cols[4] = str(newbud)
        cols[6] = newkr
        lines[ln - 1] = "\t".join(cols)
        print("  [idx5] L%d %s→%s (%dB≤예산%d)" % (ln, oldkr, newkr, b, newbud))
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))


def patch_ui():
    p = os.path.join(ROOT, "work/ui_kr.tsv")
    lines = open(p, encoding="utf-8").read().split("\n")
    for (ln, jp, oldkr, newkr) in UI:
        cols = lines[ln - 1].split("\t")
        assert cols[2] == jp, "ui L%d jp=%r != %r" % (ln, cols[2], jp)
        assert cols[7] == oldkr, "ui L%d kr=%r != %r" % (ln, cols[7], oldkr)
        bud = int(cols[5])
        b = bwidth(newkr)
        assert b <= bud, "ui L%d %r=%dB>예산%d" % (ln, newkr, b, bud)
        cols[7] = newkr
        lines[ln - 1] = "\t".join(cols)
        print("  [ui]   L%d %s→%s (%dB≤예산%d)" % (ln, oldkr, newkr, b, bud))
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))


def patch_simple():
    for rel, old, new in SIMPLE:
        p = os.path.join(ROOT, rel)
        txt = open(p, encoding="utf-8").read()
        c = txt.count(old)
        assert c == 1, "%s: %r %d회(기대 1)" % (rel, old, c)
        open(p, "w", encoding="utf-8", newline="").write(txt.replace(old, new))
        print("  [파일] %s: %s→%s" % (rel, old.strip(), new.strip()))


def main():
    print("=== 전역 치환 (dict) ===")
    for rel, subs in GLOBAL.items():
        if subs:
            print(rel); patch_global(rel, subs)
    print("=== 라인별 치환 (dict/tutorial) ===")
    # 파일별로 묶어서
    byfile = {}
    for f, ln, old, new, cnt in PER_LINE:
        byfile.setdefault(f, []).append((ln, old, new, cnt))
    for f, ed in byfile.items():
        patch_tsv_lines(f, ed)
        print("  %s: %d곳" % (f, len(ed)))
    print("=== idx5_extra_kr.tsv ===")
    patch_idx5()
    print("=== ui_kr.tsv ===")
    patch_ui()
    print("=== facilities.py / ui_overrides.py ===")
    patch_simple()
    print("\n완료.")


if __name__ == "__main__":
    main()
