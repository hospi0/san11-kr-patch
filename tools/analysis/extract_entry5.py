# -*- coding: utf-8 -*-
"""entry5 서브테이블 추출 — 확정된 클린 이름 테이블 + 시설명 후보.

★확정(고정 stride, 경계 정합):
    병장  base 0x3d1a  stride 0x96(150)   8개  이름 [0:name\\0]
    관직  base 0x4382  stride 0x2e(46)   80개  이름 [0:name\\0]

시설(施設)은 가변길이 레코드다. 이름\\0이 레코드 맨 앞이지만 읽기가 바로
뒤에 안 붙고 스탯 바이트가 끼어든다 → 인접 크립 불가. name\\0 정확일치로
후보만 나열하되 경계 미확정으로 표시한다(화면 검증 후 패치).

한글 독음은 1:1(한자1자=한글1음절=2B)이라 원문이 맞으면 바이트 동일 →
in-place 패치. 예산초과 여부를 같이 검증한다.
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
try:
    from kr_names import to_hangul
except Exception:
    to_hangul = None

d = open(os.path.join(os.path.dirname(HERE), "work/entry5.bin"), "rb").read() \
    if os.path.exists(os.path.join(os.path.dirname(HERE), "work/entry5.bin")) \
    else open("work/entry5.bin", "rb").read()


def name_at(off):
    """off에서 첫 0x00까지 SJIS 이름. (문자열, 바이트수, 가이지수)."""
    out, j, gaiji = [], off, 0
    while j < len(d) - 1:
        hi, lo = d[j], d[j + 1]
        if hi == 0:
            break
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); j += 2; gaiji += 1; continue
        try:
            ch = bytes([hi, lo]).decode("cp932")
            if len(ch) != 1:
                break
            out.append(ch); j += 2
        except Exception:
            break
    return "".join(out), j - off, gaiji


def kr_of(name, nbytes):
    """한글 독음. 가이지 포함 시 스킵. 예산(원문 바이트) 초과 검사."""
    if "[G" in name or to_hangul is None:
        return "", ""
    try:
        kr = to_hangul(name)
    except Exception:
        return "", "변환실패"
    if not kr:
        return "", ""
    note = ""
    if len(kr) != len(name):
        note = "1:1불일치 %r→%r" % (name, kr)
    else:
        kb = len(kr.encode("cp932", errors="ignore"))
        if kb > nbytes:
            note = "예산초과 %dB>%dB" % (kb, nbytes)
    return kr, note


def extract_fixed(label, base, stride, count):
    print("\n=== %s : base 0x%04x stride 0x%02x(%d) × %d ===" % (
        label, base, stride, stride, count))
    rows, over = [], 0
    for k in range(count):
        off = base + k * stride
        nm, nb, gaiji = name_at(off)
        kr, note = kr_of(nm, nb)
        if note.startswith("예산초과"):
            over += 1
        rows.append((off, nm, nb, kr, note))
        mark = ("  ← %s" % note) if note else ""
        print("  0x%04x  %-12s (%dB)  → %-8s%s" % (off, nm, nb, kr or "·", mark))
    print("  소계 %d개, 예산초과 %d건" % (count, over))
    return rows


def facility_candidates():
    """시설명 후보: 0xb82~0x2100 구간에서 name\\0 정확일치.
    가변길이라 레코드 경계는 미확정 — 첫 등장만, 오프셋순."""
    known = ["都市", "関所", "陣", "港", "城塞", "連弩櫓", "砦", "石壁",
             "太鼓台", "弓櫓", "石兵八陣", "根城", "土塁", "火炎種", "火炎球",
             "業火球", "落石", "浅瀬", "長城", "廟", "投石台", "軍楽台",
             "市場", "農場", "符節台", "錬兵所", "工房", "造船所", "民家"]
    print("\n=== 시설명 후보 (name\\0 정확일치, 0xb82~0x2100, 첫 등장) ===")
    seen, rows = {}, []
    for nm in known:
        pat = nm.encode("cp932") + b"\x00"
        p = d.find(pat, 0xb82)
        if 0xb82 <= p < 0x2100:
            rows.append((p, nm))
    rows.sort()
    for p, nm in rows:
        nb = len(nm.encode("cp932"))
        kr, note = kr_of(nm, nb)
        print("  0x%04x  %-8s (%dB)  → %s%s" % (
            p, nm, nb, kr or "·", ("  ← " + note) if note else ""))
    print("  후보 %d개 (경계 미확정 — 화면 검증 후 패치)" % len(rows))
    return rows


def write_tsv(dst="work/entry5_names.tsv"):
    with open(dst, "w", encoding="utf-8") as f:
        f.write("# 종류\toffset\t원문\t바이트\t한글\t비고\n")
        for label, base, stride, cnt in [("병장", 0x3d1a, 0x96, 8),
                                         ("관직", 0x4382, 0x2e, 80)]:
            for k in range(cnt):
                off = base + k * stride
                nm, nb, _ = name_at(off)
                kr, note = kr_of(nm, nb)
                f.write("%s\t0x%04x\t%s\t%d\t%s\t%s\n"
                        % (label, off, nm, nb, kr, note))
    print("\n%s 저장" % dst)


def main():
    extract_fixed("병장(무기)", 0x3d1a, 0x96, 8)
    extract_fixed("관직", 0x4382, 0x2e, 80)
    facility_candidates()
    write_tsv()


main()
