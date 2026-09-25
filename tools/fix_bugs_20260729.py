# -*- coding: utf-8 -*-
"""2026-07-29 실기 제보 버그 일괄 수정 (TSV 텍스트 계열).

  python tools/fix_bugs_20260729.py --dry
  python tools/fix_bugs_20260729.py --write

각 항목은 (파일, 줄번호, 원본조각, 수정조각). 줄번호+원본조각 **동시 일치**를 요구하므로
이미 고쳐졌거나 줄이 밀리면 조용히 통과하지 않고 실패로 보고된다.
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DLG = "work/e4_dialogue.tsv"
TUT = "work/e4_tutorial.tsv"

# ── 1) 매크로 앞 공백 누락 ────────────────────────────────────────────────
#    화면: 「소인의 설득으로는공도공을」 「안타깝게도허공공의 등용에」
EDITS = [
    (DLG, 157, "{01}C{00}{00}의 설득으로는{01}CE{00}을",
               "{01}C{00}{00}의 설득으로는 {01}CE{00}을"),
    (DLG, 157, "안타깝게도{01}CE{00}의 등용에",
               "안타깝게도 {01}CE{00}의 등용에"),

    # ── 2) 음슴체 잔재 (군주 앞에서 쓰는 말투가 아니다) ──────────────────
    #    JP=感謝します/感謝いたします ×3분기
    (DLG, 728, "=0감사드림{N}", "=0감사드립니다{N}"),
    (DLG, 728, "=1감사드림{N}", "=1감사드립니다{N}"),
    (DLG, 728, "{05}감사드림{N}", "{05}감사드립니다{N}"),
    #    JP=爵位授与の沙汰にございます (「ございます」= 최상급 공손)
    (DLG, 726, "작위 수여의 칙명이라 하옴", "작위 수여의 칙명이라 하옵니다"),

    # ── 3) 군주에게 반말 ────────────────────────────────────────────────
    #    JP=今回はどのように？  신하가 군주에게 묻는 말
    (DLG, 495, "{N}이번엔 어떻게 할까?", "{N}이번엔 어떻게 하시겠습니까?"),
    #    JP=加えて{01}C{f9}{00} (=加えていただけますか) 청원문인데 평서문으로 나갔다
    (DLG, 128, "말석에{N}끼워 주겠습니다", "말석에{N}끼워 주시겠습니까"),
    (DLG, 132, "말석에{N}끼워 주겠습니다", "말석에{N}끼워 주시겠습니까"),

    # ── 4) 일본어 어미조립 토큰 잔존 → 화면에 「있다だな」 ─────────────────
    #    JP=何か話があるそう{01}C{93}. 어간에 붙는 일본어 어미라 한국어로는 못 살린다.
    (DLG, 4120, "뭔가 할 말이 있다{01}C{93}", "뭔가 할 말이 있는 듯합니다"),
    (DLG, 4144, "뭔가 할 말이 있다{01}C{93}", "뭔가 할 말이 있는 듯합니다"),
    (DLG, 4167, "뭔가 할 말이 있다{01}C{93}", "뭔가 할 말이 있는 듯합니다"),

    # ── 5) 줄바꿈 위치 (「짊어지」에서 잘렸다). 글자수 불변, {N} 만 이동 ──
    (TUT, 1210, "모두, 각자가 우리 군의 위신을 짊어지고 있다고{N}생각하라",
                "모두, 각자가 우리 군의 위신을{N}짊어지고 있다고 생각하라"),
]

# ── 6) 「군군」 — {V:xx4e}(세력명 매크로)가 이미 「○○군」까지 출력한다 ────────
#    JP 원문엔 매크로 뒤에 軍이 없다. 매크로 결과가 항상 「군」으로 끝나므로
#    리터럴 「군」만 지우면 뒤 조사(이/은/과/을)는 그대로 맞는다.
GUN_RE = re.compile(r"(\{V:[0-9a-f]{2}4e\})군")


def load(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read().split("\n")


def main(mode):
    files = {}
    for rel in {e[0] for e in EDITS} | {TUT}:
        files[rel] = load(rel)

    ok = fail = 0
    for rel, ln, old, new in EDITS:
        line = files[rel][ln - 1]
        if old not in line:
            print("  ❌ 불일치 %s:%d  %r" % (rel, ln, old[:44])); fail += 1; continue
        files[rel][ln - 1] = line.replace(old, new, 1)
        ok += 1
    print("개별 교정 %d건 성공 / %d건 실패" % (ok, fail))

    gun = 0
    for i, line in enumerate(files[TUT]):
        n = len(GUN_RE.findall(line))
        if n:
            files[TUT][i] = GUN_RE.sub(r"\1", line)
            gun += n
    print("「군군」 리터럴 군 제거 %d곳 (%s)" % (gun, TUT))

    if fail:
        raise SystemExit("실패가 있어 기록하지 않는다")

    if mode == "--write":
        for rel, lines in files.items():
            io.open(os.path.join(REPO, rel), "w", encoding="utf-8",
                    newline="").write("\n".join(lines))
        print("기록 완료")
    else:
        print("드라이런 — 기록 안 함")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
