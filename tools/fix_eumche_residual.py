# -*- coding: utf-8 -*-
"""음슴체(~ㅁ/음 종결) 잔재 → 정중체. **JP가 정중체일 때만** 고친다.

예산 압축 시절에 「감사드림」「축하드림」「확인됐음」처럼 종결어미를 잘라낸 흔적이 남았다
(2026-07-29 사용자 제보: 손책 「감사드림」, 문관 「칙명이라 하옴」).

⚠️원본이 **체언 종결**인 로그도 있다 — 「{V:0a32}の傷病が回復」→「회복됨」은 JP도 어미가 없다.
   그래서 세그먼트({05} 분기) 단위로 JP와 짝지어 **JP가 ます/ました/ません 로 끝날 때만** 고친다.

  python tools/fix_eumche_residual.py --dry
  python tools/fix_eumche_residual.py --write
"""
import io
import os
import re
import sys
import glob

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# JP 세그먼트가 정중체로 끝나는가 (뒤쪽 기호·제어토큰은 무시)
JP_POLITE = re.compile(r"(ます|ました|ません|ませぬ|ください|ございます)[。！？…\s]*$")

# 음슴체 종결 → 정중체. 긴 것부터.
FIX = [
    ("되었음", "되었습니다"), ("완료됐음", "완료되었습니다"), ("확인됐음", "확인되었습니다"),
    ("들어왔음", "들어왔습니다"), ("중단했음", "중단했습니다"), ("실패했음", "실패했습니다"),
    ("중지했음", "중지했습니다"), ("승리했음", "승리했습니다"), ("패배했음", "패배했습니다"),
    ("해산됨", "해산됩니다"), ("추가됨", "추가됩니다"),
    ("있음", "있습니다"), ("없음", "없습니다"),
    ("했음", "했습니다"), ("됐음", "되었습니다"), ("왔음", "왔습니다"),
]
TAIL = re.compile(r"(%s)$" % "|".join(re.escape(a) for a, _ in FIX))
MAP = dict(FIX)


def _fix_unit(j, k, hits):
    """JP 조각 j 가 정중체로 끝나면 KR 조각 k 의 음슴체 종결을 고친다."""
    if not JP_POLITE.search(j.strip()):
        return k
    m = TAIL.search(k.rstrip())
    if not m:
        return k
    old = m.group(1)
    hits.append((old, MAP[old], j.strip()[-18:]))
    return k.rstrip()[: m.start()] + MAP[old] + k[len(k.rstrip()):]


def fix_line(jp, kr):
    a, b = jp.split("{05}"), kr.split("{05}")
    if len(a) != len(b):
        return kr, []                      # 분기 수가 다르면 짝지을 수 없다 → 손대지 않는다
    hits = []
    for i, (j, k) in enumerate(zip(a, b)):
        # ★세그먼트 끝만 보면 「…추가됨{N}새로 게임을…」처럼 **줄 중간에서 끝나는** 문장을
        #   놓친다. {N} 으로 한 번 더 쪼개 줄 단위로 짝짓고, 줄 수가 같을 때만 줄 단위로 본다.
        jl, kl = j.split("{N}"), k.split("{N}")
        if len(jl) == len(kl) and len(jl) > 1:
            for t in range(len(jl)):
                kl[t] = _fix_unit(jl[t], kl[t], hits)
            b[i] = "{N}".join(kl)
        else:
            b[i] = _fix_unit(j, k, hits)
    return "{05}".join(b), hits


def main(mode):
    total = 0
    for path in sorted(glob.glob(os.path.join(REPO, "work/e4_*.tsv"))):
        if ".bak" in path:
            continue
        out, n = [], 0
        for ln in io.open(path, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if ln.startswith("#") or len(p) < 5 or not p[4].strip():
                out.append(ln); continue
            new, hits = fix_line(p[3], p[4])
            if hits:
                n += len(hits)
                for o, w, j in hits:
                    print("  %s  %s → %s   (JP…%s)"
                          % (os.path.basename(path), o, w, j))
                p[4] = new
                ln = "\t".join(p) + "\n"
            out.append(ln)
        if n and mode == "--write":
            io.open(path, "w", encoding="utf-8", newline="").writelines(out)
        total += n
    print("\n%d건 %s" % (total, "기록" if mode == "--write" else "드라이런"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
