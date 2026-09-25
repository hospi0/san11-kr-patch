# -*- coding: utf-8 -*-
"""兵舎/鍛冶 용어 일관성 점검 — 원문에 해당 한자가 있는데 번역이 어긋난 줄만 뽑는다.

주의: '병사'는 兵士(soldier)의 정상 번역이기도 하다.
     그러므로 **원문에 兵舎가 있는 줄**만 후보로 삼는다. 무조건 치환하면 안 된다.
"""
import os, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    ("兵舎", "병사", "병영"),
    ("鍛冶", "단야", "대장간"),
]
SKIP = (".bak", "_bak", "backup")


def files():
    out = []
    for pat in ("work/*.tsv", "my files/**/*.txt", "my files/*.tsv", "tools/*.py"):
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            if any(s in os.path.basename(p) for s in SKIP):
                continue
            out.append(p)
    return sorted(set(out))


def main():
    for jp, cur, want in TARGETS:
        print("=" * 70)
        print("원문 %s : 현재 '%s' -> 제안 '%s'" % (jp, cur, want))
        print("=" * 70)
        tot = 0
        for p in files():
            try:
                lines = open(p, encoding="utf-8").read().split("\n")
            except Exception:
                continue
            hits = []
            for i, ln in enumerate(lines, 1):
                if jp in ln and cur in ln:
                    hits.append((i, ln))
            if hits:
                rel = os.path.relpath(p, ROOT)
                print("\n[%s] %d줄" % (rel, len(hits)))
                for i, ln in hits[:6]:
                    s = ln if len(ln) < 150 else ln[:150] + "…"
                    print("   %5d| %s" % (i, s))
                if len(hits) > 6:
                    print("   ... 외 %d줄" % (len(hits) - 6))
                tot += len(hits)
        print("\n>> %s 관련 후보 총 %d줄\n" % (jp, tot))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
