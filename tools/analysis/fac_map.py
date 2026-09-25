# -*- coding: utf-8 -*-
"""entry5 서브테이블 경계 지도 — 랜드마크 문자열 + 마커로 구역 확정.

추측 stride 금지. 알려진 이름 문자열들의 실제 위치를 찾아 구역을 나눈다.
"""
import sys

d = open("work/entry5.bin", "rb").read()

# 알려진 이름들 (memory + docs 기준). name\0 형태로만 매칭(설명문 안 부분일치 배제).
LANDMARKS = {
    "시설": ["都市", "関所", "陣", "港", "城塞", "連弩櫓", "砦", "石壁",
             "太鼓台", "弓櫓", "石兵八陣", "根城", "土塁", "火炎種", "火炎球",
             "業火球", "落石", "浅瀬", "長城", "廟", "投石台", "軍楽台",
             "市場", "農場", "符節台", "錬兵所", "工房", "造船所"],
    "병장": ["軍馬", "衝車", "井闌", "楼船", "闘艦", "走舸", "木獣", "投石"],
    "관직": ["丞相", "司空", "太尉", "司徒", "大都督", "車騎将軍", "武衛校尉",
             "僕射", "長水校尉", "奮威校尉"],
    "특기": ["鬼門", "神算", "眼力", "百出", "反計", "看破", "冷静", "解毒"],
}


def find_named(name):
    """name\\0 로 끝나는 위치 전부(이름 필드일 가능성 높음)."""
    pat = name.encode("cp932") + b"\x00"
    out, i = [], 0
    while True:
        p = d.find(pat, i)
        if p < 0:
            break
        out.append(p)
        i = p + 1
    return out


def main():
    print("=== 랜드마크 위치 (name\\0 완전일치) ===\n")
    rows = []
    for cat, names in LANDMARKS.items():
        for nm in names:
            offs = find_named(nm)
            for o in offs:
                rows.append((o, cat, nm))
    rows.sort()
    for o, cat, nm in rows:
        print("  0x%04x  [%s] %s" % (o, cat, nm))


main()
