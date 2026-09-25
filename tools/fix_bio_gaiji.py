# -*- coding: utf-8 -*-
"""열전·대사 KR 컬럼에 남은 가이지 토큰 {BTNxx} → 한글 독음.

증상(2026-07-29 사용자 제보): 무장열전에 「장琬」「비褘」「邢도영」처럼 한자가 섞여 보인다.
원인: 번역 시 {BTNxx}(가이지=SJIS 사용자정의 영역 한자)를 풀지 않고 그대로 남겼다.
      폰트가 원본 한자 글리프를 그리므로 화면에 한자가 나온다.

★예산: 가이지 1자 = SJIS 2B, 한글 1자 = 2B → **크기 완전 동일**. 재압축 예산 영향 없음.

⚠️{BTNae}(史 태그)·{BTNaf}(演 태그)·{BTNb8}이상(PS버튼)은 가이지가 아니다.
   GAIJI_MAP 에 없으므로 자동으로 건드리지 않는다.

  python tools/fix_bio_gaiji.py --audit   # 로스터 역산과 독음표 대조 (쓰기 없음)
  python tools/fix_bio_gaiji.py --dry     # 치환 미리보기
  python tools/fix_bio_gaiji.py --write
"""
import io
import os
import re
import sys
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from gaiji_map import GAIJI_MAP                    # noqa: E402
from gaiji_readings import GAIJI_READING           # noqa: E402

TOKEN = re.compile(r"\{BTN([0-9a-f]{2})\}")
TARGETS = ["work/e4_bio.tsv", "work/e4_dialogue.tsv", "work/e4_tutorial.tsv",
           "work/e4_sys.tsv", "work/e4_kessen.tsv", "work/e4_dict.tsv"]


def _repl(kr):
    """KR 문자열의 가이지 토큰만 한글로. (새문자열, 치환수)."""
    n = [0]

    def f(m):
        code = 0xF000 | int(m.group(1), 16)
        han = GAIJI_MAP.get(code)
        if han is None:
            return m.group(0)                      # 가이지 아님 → 보존
        kr1 = GAIJI_READING.get(han)
        if kr1 is None:
            return m.group(0)                      # 독음 미상 → 보존(로그로 잡힌다)
        n[0] += 1
        return kr1

    return TOKEN.sub(f, kr), n[0]


def audit():
    """로스터/지명 한글표에서 독음을 역산해 GAIJI_READING 과 대조."""
    cand = collections.defaultdict(collections.Counter)
    hanset = set(GAIJI_MAP.values())

    def feed(jp, kr):
        if jp and kr and len(jp) == len(kr):
            for a, b in zip(jp, kr):
                if a in hanset:
                    cand[a][b] += 1

    for ln in io.open(os.path.join(REPO, "work/roster_kr.tsv"), encoding="utf-8"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 8:
            feed(p[1], p[5]); feed(p[2], p[6]); feed(p[3], p[7])
    for ln in io.open(os.path.join(REPO, "work/places_kr.tsv"), encoding="utf-8"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 5:
            feed(p[2], p[4])

    bad = 0
    for han, ctr in sorted(cand.items()):
        mine = GAIJI_READING.get(han)
        if mine is None:
            print("  ⚠️ 표에 없음:", han, dict(ctr)); bad += 1
        elif mine not in ctr:
            print("  ❌ 불일치:", han, "표=", mine, "로스터=", dict(ctr)); bad += 1
        elif len(ctr) > 1:
            print("  ⚠️ 로스터가 여러 독음:", han, dict(ctr), "→ 표=", mine)
    only_manual = sorted(set(GAIJI_READING) - set(cand))
    print("  로스터 역산 대조 %d자, 불일치 %d건" % (len(cand), bad))
    print("  로스터에 없어 수동인 것:", " ".join(only_manual))
    return bad


def main(mode):
    if mode == "--audit":
        raise SystemExit(1 if audit() else 0)

    total, per = 0, collections.Counter()
    samples = []
    for rel in TARGETS:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            continue
        out, changed = [], 0
        for ln in io.open(path, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if ln.startswith("#") or len(p) < 5 or not p[4].strip():
                out.append(ln); continue
            new, n = _repl(p[4])
            if n:
                changed += n
                if len(samples) < 6:
                    i = p[4].find("{BTN")
                    samples.append((rel, p[4][max(0, i - 24):i + 40], new[max(0, i - 24):i + 36]))
                p[4] = new
                ln = "\t".join(p) + "\n"
            out.append(ln)
        if changed:
            per[rel] = changed; total += changed
            if mode == "--write":
                io.open(path, "w", encoding="utf-8", newline="").writelines(out)

    for k, v in per.items():
        print("  %-24s %d개" % (k, v))
    print("총 %d개 %s" % (total, "치환 기록" if mode == "--write" else "치환 예정(드라이런)"))
    print("\n표본 대조 (앞=현재, 뒤=수정후):")
    for rel, a, b in samples:
        print("  ", rel)
        print("    -", a)
        print("    +", b)

    # 남은 가이지 확인
    left = collections.Counter()
    for rel in TARGETS:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            continue
        for ln in io.open(path, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            for m in TOKEN.finditer(p[4]):
                if (0xF000 | int(m.group(1), 16)) in GAIJI_MAP:
                    left[m.group(1)] += 1
    print("\n기록 후 KR에 남은 가이지:", sum(left.values()), dict(left) if left else "")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
