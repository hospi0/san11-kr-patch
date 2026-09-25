# -*- coding: utf-8 -*-
"""고아 인수 바이트 제거 — 본문 **맨 끝**의 어미 매크로를 KR에 되살린다.

2026-07-29 「동맹파기 사신 이벤트가 대사 도중 끊긴다」의 수정.

배경:
  `extract_e4` 는 `split_pad` 로 세그먼트 앞뒤의 `05/00` 패딩을 떼어 TSV에 본문만 담고,
  빌더가 `pre + encode(kr) + suf` 로 다시 붙인다. 그런데 어미 매크로 `01 43 xx 00` 이
  **본문 맨 끝**에 오면 마지막 `00`(bank 인수)이 **suf 로 떨어져 나간다**.
  번역문이 어미를 한국어에 녹여 매크로를 지우면 그 `00` 만 남는다:

      원본   : 用件を聞 | 01 43 e0 | 00 | 05 05 05     ← 00 은 매크로의 인수
      빌드본 : 듣겠습니다 |          | 00 | 05 05 05     ← **고아 00**

  파서가 고아 00 에서 멈춰 뒤의 분기 종결자(05 05 05)를 못 읽는다(RAM 0x1db4b9b 실측).

대책:
  KR 본문 끝에 매크로를 **되살려** 바이트 구조를 원본과 같게 만들고,
  그 매크로가 뱉을 일본어는 `build_help.PART1_BLANK_LITERALS` 로 비운다.
  → 화면엔 한국어만 남고 구조는 원본과 동일.

⚠️본문 **중간**의 매크로는 인수 `{00}` 까지 본문에 들어 있어 함께 지워졌다 = 고아가 없다.
   그래서 대상은 「TSV 의 JP 가 그 토큰으로 **끝나는**」 줄뿐이다.

  python tools/fix_orphan_bank.py --dry
  python tools/fix_orphan_bank.py --write
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
sys.path.insert(0, os.path.join(REPO, "tools"))
import ls11                                         # noqa: E402
import help_codec                                   # noqa: E402
from build_help import split_pad, PART1_BLANK_LITERALS   # noqa: E402

# 되살릴 토큰. **build_help.PART1_BLANK_LITERALS 에 그 msg 가 등록돼 있어야** 한다
# (안 그러면 화면에 일본어 어미가 그대로 뜬다).
TOKENS = ["{01}C{e0}"]       # msg[224] = きましょう / こう


def _msg_index(tok):
    m = re.fullmatch(r"\{01\}C\{([0-9a-f]{2})\}", tok)
    return int(m.group(1), 16)


def main(mode):
    for tok in TOKENS:
        idx = _msg_index(tok)
        if idx not in PART1_BLANK_LITERALS:
            raise SystemExit("%s → msg[%d] 가 PART1_BLANK_LITERALS 에 없다 "
                             "(비우지 않으면 일본어 어미가 화면에 뜬다)" % (tok, idx))

    # 원본 세그먼트의 suf 를 실측해 「bank 가 suf 로 넘어간」 줄만 고른다
    orig = {}
    d = open(os.path.join(REPO, "work/entry4.bin"), "rb").read()
    for bi, b in enumerate(ls11.decode_all(d)):
        try:
            orig[bi] = help_codec.segments(b, help_codec.parse_offsets(b))
        except Exception:
            pass

    total = 0
    for path in sorted(glob.glob(os.path.join(REPO, "work/e4_*.tsv"))):
        if ".bak" in path:
            continue
        out, n = [], 0
        for ln in io.open(path, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if ln.startswith("#") or len(p) < 5 or not p[0].isdigit() or not p[4].strip():
                out.append(ln); continue
            hit = None
            for tok in TOKENS:
                if p[3].endswith(tok) and not p[4].endswith(tok):
                    hit = tok; break
            if hit:
                seg = orig[int(p[0])][int(p[1])]
                body = split_pad(seg)[1]
                raw = bytes([0x01, 0x43, _msg_index(hit)])
                if not body.endswith(raw):          # 게이트: 정말 본문 끝인가
                    print("  ⚠️ 건너뜀(본문 끝 아님) %s idx%s" % (os.path.basename(path), p[1]))
                    out.append(ln); continue
                print("  %s blk%s idx%-4s  …%s  +%s"
                      % (os.path.basename(path), p[0], p[1], p[4][-26:], hit))
                p[4] = p[4] + hit
                ln = "\t".join(p) + "\n"
                n += 1
            out.append(ln)
        if n and mode == "--write":
            io.open(path, "w", encoding="utf-8", newline="").writelines(out)
        total += n
    print("\n%d줄 %s" % (total, "기록" if mode == "--write" else "드라이런"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "--dry")
