"""entry4(LS11) 텍스트를 종류별 TSV로 추출 — 번역용.

entry4 = 게임 최대의 텍스트 저장소(9,873 메시지 / 676,884자). 세션8에 LS11을 풀어서 열렸다.
각 블록은 idx=3와 **같은 코덱**의 메시지 풀이다(u16 개수 + u32 오프셋테이블 + 본문).

  파이프라인:  entry4.bin --ls11--> 블록 --help_codec--> 토큰화 텍스트 --> TSV
               TSV(번역) --help_codec.encode--> 블록 --ls11.build--> entry4_kr.bin

★★**앞뒤 05/00 패딩은 번역 대상이 아니다** — `build_help.split_pad`와 **같은 방식**으로 떼어내고
  본문만 TSV에 넣는다. 빌더가 `pre + encode(kr) + suf`로 다시 붙인다.
  (`help_codec.encode`는 `{05}` 같은 생 제어토큰을 모른다 — 리터럴 ASCII `7b 30 35 7d`로 나가버린다.
   출하된 idx=3 파이프라인이 이 버그를 안 밟은 건 순전히 split_pad가 먼저 떼어냈기 때문이다.)

★추출 전에 **라운드트립 게이트**를 통과해야 한다: pre + encode(decode(body)) + suf == 원본 세그먼트.
  깨지면 그 메시지는 번역해도 원문이 조용히 망가진다. **게이트를 통과 못한 줄은 TSV에서 뺀다.**

Usage: python extract_e4.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ls11                                                    # noqa: E402
from help_codec import parse_offsets, segments, decode, encode  # noqa: E402
from build_help import split_pad                                # noqa: E402

E4 = 'work/entry4.bin'
OUT = 'work'

# 세션8 census로 확정한 분류. 블록 = 종류별로 깔끔히 갈린다.
GROUPS = [
    ('sys',      [23],                    '시스템 메시지 (결전목표·옵션·다이얼로그 + 환경설정 500~511)'),
    ('dict',     [21, 22],                '용어사전 설명문 (표제어는 SLPM에 있고 이미 한글)'),
    ('bio',      list(range(5, 21)),      '무장 열전 약 794명분'),
    ('tutorial', [25, 26, 28],            '튜토리얼 + 이벤트 내레이션'),
    ('kessen',   [27, 29],                '결전 목표 + 결전 진행 대사'),
    ('dialogue', [0, 1, 2, 3, 4, 24],     '무장 대사 (성격별 분기·전법·설전). ⚠️제어코드 복잡'),
]

HEADER = """\
# entry4 %s — %s
# 블록 %s. 총 %d개 / %d자
# 토큰 {V:...}=변수삽입 {N}=줄바꿈 {BTNxx}=PS버튼 {05}{04}등=제어코드 — **반드시 그대로 보존**
# ⚠️kr을 비우면 원본이 널로 지워진다. 번역 안 할 줄은 kr을 비우고 두되 빌더가 원문을 쓰게 한다.
# ⚠️번역문에 한자를 남기지 말 것(한자 코드는 한글 운반체라 엉뚱한 글자가 뜬다).
block\tindex\tbytes\tjp\tkr
"""


_ESC = (b'\x1bH', b'\x1bK', b'\x1bh', b'\x1bk')


def _strip_esc(b):
    for e in _ESC:
        b = b.replace(e, b'')
    return b


def _same(got, want):
    """게이트. ★ESC 차이만은 봐준다.

    ESC(1b 48/4b)는 **반각 카타카나의 렌더 모드 스위치**라, 한국어 번역문엔 가나가 없어서
    애초에 안 나온다(help_codec 설계. idx=3 763개가 이 상태로 실기 통과했다).
    그래서 "일본어 원문을 그대로 재현하나"로 보면 실패지만 "한국어를 옳게 쓰나"엔 무해하다.
    ⚠️ESC **외의** 차이는 봐주지 않는다 — 그건 진짜로 바이트가 깨진다는 뜻이다.
    """
    return got == want or _strip_esc(got) == _strip_esc(want)


def main():
    e4 = open(E4, 'rb').read()
    blocks = {i: ls11.decode_block(e4, i) for i in range(30)}

    rt_fail = []
    total_msgs = total_ch = total_skip = 0
    for name, idxs, desc in GROUPS:
        rows, nch, skip = [], 0, 0
        for bi in idxs:
            d = blocks[bi]
            for k, seg in enumerate(segments(d, parse_offsets(d))):
                pre, body, suf = split_pad(seg)        # ★패딩은 번역 대상 아님
                if not body:
                    skip += 1                          # 패딩뿐인 슬롯
                    continue
                try:
                    jp = decode(body)
                    ok = _same(pre + encode(jp, None, jp_passthrough=True) + suf, seg)
                except Exception as ex:
                    rt_fail.append((bi, k, repr(ex)[:60]))
                    skip += 1
                    continue
                if not ok:                             # ★게이트 실패 = TSV에서 뺀다
                    rt_fail.append((bi, k, 'roundtrip mismatch'))
                    skip += 1
                    continue
                rows.append((bi, k, len(seg), jp))
                nch += len(jp)
        path = os.path.join(OUT, 'e4_%s.tsv' % name)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(HEADER % (name, desc, idxs, len(rows), nch))
            for bi, k, n, jp in rows:
                f.write('%d\t%d\t%d\t%s\t\n' % (bi, k, n, jp.replace('\t', ' ')))
        total_msgs += len(rows); total_ch += nch; total_skip += skip
        print('  %-9s %-26s %5d개 %7d자   (제외 %d)' % (name, os.path.basename(path), len(rows), nch, skip))

    print()
    print('합계 %d개 / %d자 (제외 %d)' % (total_msgs, total_ch, total_skip))
    print('라운드트립 실패: %d' % len(rt_fail))
    for x in rt_fail[:10]:
        print('   ', x)


if __name__ == '__main__':
    main()
