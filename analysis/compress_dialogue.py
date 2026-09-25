# -*- coding: utf-8 -*-
"""e4_dialogue.tsv 번역문에 help_compress.py의 존댓말→명사형 규칙을 적용해 entry4 예산을 줄인다.

★세션17 확정: entry4는 dict·tutorial·bio를 빼도(=`build_all.py`의 기본 E4_ONLY=
'dialogue,kessen,sys') dialogue 분량만으로 안전 한계(709,268B, 순수 제자리 패치)를
넘길 수 있다. 이 스크립트가 그 여유를 만든다.

적용 범위(2026-07-19 확정, 이 두 개만 — 그 이상은 말투가 눈에 띄게 거칠어진다):
  ① help_compress.RULES의 `$`(문자열 끝) 앵커 규칙 그대로 재사용
     (겠습니다→겠음, 없습니다→없음, 입니다→ 등 — 존댓말 문장을 딱딱한 보고체 명사형으로).
  ② ①이 대사 특성상 대부분 `！？…!?` 뒤에 와서 `$` 앵커가 못 걸리던 문제를 기계적으로
     뚫음(문장부호를 별도 조각으로 쪼개 규칙이 그 앞 어미에 걸리게 함 — punctuation 자체는
     그대로 보존, 새 문장부호를 추가하지 않는다).

★★일부러 안 넣은 것(2026-07-19 사용자 판단, 다시 넣으려면 먼저 상의할 것):
  - 의문형 축약("겠습니까→겠나" 등) — 말투가 눈에 띄게 거칠어짐.
  - "！！"→"！", "……"→"…" 중복 문장부호 통합 — 대사 30%에 스타일 변화.
  두 옵션 다 시도해서 측정까지 했었다(각각 -1,062 / -1,919 raw). 필요해지면 재현 가능.

Usage: python analysis/compress_dialogue.py [--dry]
  출력: work/e4_dialogue.tsv (백업 .bak_compress)
"""
import io
import re
import shutil
import sys

sys.path.insert(0, 'tools')
import help_compress as HC  # noqa: E402

TSV = 'work/e4_dialogue.tsv'
PIECE_RE = re.compile(r'(\.\s*|\(|[！？!?…]+)')
TOKEN_RE = re.compile(r'(\{[^}]+\})')


def compress_line(s):
    """help_compress._apply()를 토큰·문장부호 경계마다 적용. 최종 strip은 전체 1회만."""
    out = []
    for part in TOKEN_RE.split(s):
        if part.startswith('{') or not part:
            out.append(part)
            continue
        pieces = PIECE_RE.split(part)
        out.append(''.join(p if i % 2 else HC._apply(p) for i, p in enumerate(pieces)))
    return re.sub(r' +', ' ', ''.join(out)).strip()


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')

    n = 0
    total_before = total_after = 0
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit() and p[4].strip():
            kr = p[4]
            c = compress_line(kr)
            total_before += HC.body_bytes(kr)
            total_after += HC.body_bytes(c)
            if c != kr:
                p[4] = c
                lines[i] = '\t'.join(p)
                n += 1

    print('압축 적용 %d줄 / 원시바이트 %d -> %d (delta %d)'
          % (n, total_before, total_after, total_after - total_before))
    if dry:
        print('(--dry: 저장 안 함)')
        return
    shutil.copy(TSV, TSV + '.bak_compress')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s (백업 %s.bak_compress)' % (TSV, TSV))


if __name__ == '__main__':
    main()
