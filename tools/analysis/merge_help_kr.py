# -*- coding: utf-8 -*-
"""사용자 번역(my files/help_trans{1,2}_kr.txt) + 정정 코덱 + 교정분 → work/help_kr.tsv 정본.

사용자 파일은 에디터가 NFC 정규화해 저장했으므로 비교·병합 전 양쪽 NFC로 맞춘다
(안 맞추면 탁점이 결합문자로 분해돼 526줄이 거짓 diff로 잡힌다).
"""
import io
import sys
import unicodedata as U

sys.path.insert(0, "tools")
from help_codec import load, decode, PART2_START_INDEX      # noqa: E402
from help_fixups import FIXUPS                              # noqa: E402
from help_compress import compress                          # noqa: E402

SRC = ["my files/help_trans1_kr.txt", "my files/help_trans2_kr.txt"]


def N(s):
    """NFC + 한국어 표기 정규화.

    사용자가 일본어 원문의 전각 중점 `・`(U+30FB)를 그대로 둔 곳이 11군데 있다. 한국어
    가운뎃점은 `·`(U+00B7)이고 **둘은 어차피 같은 바이트로 인코딩된다**(encoding.PUNCT_ALIAS가
    ·→・로 되돌리므로). 표기를 여기서 통일해야 되읽기 검증이 자기 자신과 일치한다.
    """
    return U.normalize("NFC", s).replace("・", "·")


def read_user():
    """사용자 번역 → {offset: kr}. **오프셋으로 키를 건다** — 사용자 TSV의 index 열은
    옛 파서의 메시지0 누락 때문에 1 밀려 있지만 offset 열은 처음부터 옳았다."""
    kr = {}
    for f in SRC:
        for ln in io.open(f, encoding="utf-8"):
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 5 and p[0].isdigit():
                kr[int(p[1], 16)] = N(p[4]).strip()
    return kr


def main():
    d, offs, msgs = load()
    part2 = [(i, o, s) for i, o, s in msgs if i >= PART2_START_INDEX]
    kr = read_user()
    n_user = len(kr)
    kr.update({k: N(v) for k, v in FIXUPS.items()})          # 교정분이 우선
    # ★entry3 슬롯이 122,880 B 고정이라 존댓말 번역(22,939B)은 20% 초과 → 간결체 압축.
    #   예산은 줄별이 아니라 총합이다(오프셋 테이블을 새로 쓰므로).
    kr = {o: compress(v) for o, v in kr.items()}

    stray = [o for o in kr if o not in {x[1] for x in part2}]
    todo = [(i, o, s) for i, o, s in part2 if not kr.get(o)]
    with io.open("work/help_kr.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("# idx=3 도움말 번역 정본. help_codec 기준(02 가변길이·ESC k·헤더 재규명 반영).\n")
        f.write("# ⚠️index는 메시지0을 포함한 정정 번호 = 사용자 번역 TSV의 번호 +1. 매칭은 offset으로.\n")
        f.write("# 토큰 {V:...}=변수삽입 {N}=줄바꿈 {BTNxx}=PS버튼 — 반드시 보존.\n")
        f.write("index\toffset\tbytes\tjp\tkr\n")
        for i, o, s in part2:
            f.write("%d\t0x%05x\t%d\t%s\t%s\n" % (i, o, len(s), N(decode(s)), kr.get(o, "")))
    print("work/help_kr.tsv 저장: %d개 (사용자번역 %d + 교정 %d / 미번역 %d)"
          % (len(part2), n_user, len(FIXUPS), len(todo)))
    print("part2에 없는 엉뚱한 오프셋:", ["0x%05x" % o for o in stray] or "없음")
    for i, o, s in todo:
        print("   미번역 idx %d @0x%05x: %r" % (i, o, N(decode(s))))


if __name__ == "__main__":
    main()
