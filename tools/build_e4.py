"""e4_*.tsv 번역 -> entry4_kr.bin (LS11 재압축).

  work/e4_*.tsv --help_codec.encode--> 메시지 --> 블록 풀 --ls11.build--> entry4_kr.bin
                                                              --poke_e4.py--> ISO

★★**예산 = entry4 RAM 슬롯 710,656 B**
  = (idx5 섹터 979 − idx4 섹터 632) × 0x800. entry3의 122,880을 정확히 맞힌 것과 같은 논리다
  (entry3는 이걸 넘겨 **부팅 직후 검은화면**이 났다. docs/11). ⚠️단 entry4 슬롯 자체는 **미검증**.
  0x1da1c00부터 풀이 풀려 들어가므로 넘기면 그 버퍼를 깔아뭉갠다.
  - 709,268 이하  = LINK 엔트리 그대로, 순수 제자리 패치(poke_e4.py가 0패딩) ← **안전지대**
  - 710,656 이하  = LINK 크기 필드만 수정 필요(디스크 섹터는 이미 347개 잡혀 있음)
  - 초과          = 빌드 거부

★예산 실측(출하된 entry3 한글본 기준): 한글은 raw +0.7% / **LS11 압축 후 +2.1%**.
  ⚠️그 수치는 `help_compress.py` 규칙압축으로 22,939 B를 깎은 뒤의 것이다. 존댓말을 다 살리면 훨씬 커진다.

★번역 안 한 줄(kr 비어있음)은 **원본 세그먼트를 그대로** 쓴다 — 빈 값이 원본을 지우지 않게.

Usage:
  python build_e4.py [--only sys,dict,...] [--roundtrip]
"""
import io
import os
import struct
import sys
import unicodedata as U

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ls11                                                    # noqa: E402
from help_codec import parse_offsets, segments, decode, encode  # noqa: E402
from build_help import split_pad                                # noqa: E402
from encoding import Codec                                       # noqa: E402

# idx20은 실제 대사 3줄 + 점프테이블 라벨 5개(`{01}J<kanji>`)가 한 메시지풀에 섞여 있다.
# 라벨 한자는 한글 운반체로 재도색된 코드라 codec.code_for가 못 찾아 KeyError가 나는데,
# 애초에 cp932 원바이트를 그대로 디코드한 것이라 jp_passthrough로 그 바이트 그대로
# 복원된다(플레이어에게 노출되는 텍스트가 아니므로 안전 — 실기 검증 전까지는 이 줄 하나만
# 예외 처리하고 나머지 748줄의 "한자 잔존 = 번역누락" 안전망은 그대로 둔다).
JP_PASSTHROUGH_ROWS = {(23, 20)}

E4 = 'work/entry4.bin'
ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
OUT = 'work/entry4_kr.bin'
# ★2026-07-29 세션28: entry4 슬롯은 코드 상수가 아니라 **LINK 크기 필드의 섹터 올림값**임이
#   규명돼(e4_reloc 참조), 더 넓은 자리로 이사시켜 예산을 늘렸다. 옛 값은 아래 주석.
#     옛: SLOT_MAX 710656 (=(979-632)*0x800, 이웃 idx5 가 막던 한계) / INPLACE_MAX 709268
import e4_reloc                                                # noqa: E402
SLOT_MAX = e4_reloc.SLOT_MAX          # 778,240 = 380섹터
INPLACE_MAX = e4_reloc.SLOT_MAX       # 이사 후엔 슬롯 전체가 쓸 수 있는 자리다


def read_kr(only=None):
    """work/e4_*.tsv -> {(block, index): kr}"""
    kr = {}
    for f in sorted(os.listdir('work')):
        if not (f.startswith('e4_') and f.endswith('.tsv')):
            continue
        if only and f[3:-4] not in only:
            continue
        for ln in io.open(os.path.join('work', f), encoding='utf-8'):
            p = ln.rstrip('\n').split('\t')
            if len(p) >= 5 and p[0].isdigit() and p[4].strip():
                kr[(int(p[0]), int(p[1]))] = U.normalize('NFC', p[4]).strip()
    return kr


def build_pool(bodies):
    """[세그먼트] -> 메시지 풀 (u16 개수 + u32 오프셋테이블 + 본문)."""
    n = len(bodies)
    base = 2 + 4 * n
    out, offs, p = bytearray(), [], base
    for b in bodies:
        offs.append(p)
        out += b
        p += len(b)
    head = struct.pack('<H', n) + b''.join(struct.pack('<I', o) for o in offs)
    assert len(head) == base
    return head + bytes(out)


def main():
    only = None
    for i, a in enumerate(sys.argv):
        if a == '--only':
            only = set(sys.argv[i + 1].split(','))
    roundtrip = '--roundtrip' in sys.argv

    e4 = open(E4, 'rb').read()
    dic = e4[0x10:0x110]
    codec = Codec(ELF)
    kr = {} if roundtrip else read_kr(only)
    print('번역 %d줄 로드' % len(kr))

    blocks, n_tr, errs = [], 0, []
    for bi in range(30):
        d = ls11.decode_block(e4, bi)
        segs = segments(d, parse_offsets(d))
        bodies = []
        for k, seg in enumerate(segs):
            t = kr.get((bi, k))
            if not t:
                bodies.append(seg)                  # ★미번역 = 원본 그대로
                continue
            pre, body, suf = split_pad(seg)
            try:
                enc = encode(t, codec, jp_passthrough=(bi, k) in JP_PASSTHROUGH_ROWS)
            except Exception as e:
                errs.append((bi, k, t[:30], repr(e)[:50]))
                bodies.append(seg)
                continue
            new = pre + enc + suf
            if U.normalize('NFC', decode(enc, codec)) != t:   # 되읽기 검증
                errs.append((bi, k, t[:30], '되읽기 불일치'))
                bodies.append(seg)
                continue
            bodies.append(new)
            n_tr += 1
        pool = build_pool(bodies)
        if not kr and pool != d:
            print('  ⚠️block%d 구조 라운드트립 불일치 (%d vs %d)' % (bi, len(pool), len(d)))
        blocks.append(pool)

    out = ls11.build(blocks, dic)
    print('번역 적용 %d개 / 오류 %d개' % (n_tr, len(errs)))
    for e in errs[:8]:
        print('   ', e)
    print()
    print('entry4_kr: %d B   (원본 %d / 제자리한계 %d / 슬롯 %d)'
          % (len(out), len(e4), INPLACE_MAX, SLOT_MAX))
    if len(out) > SLOT_MAX:
        raise SystemExit('★★슬롯 초과 %d B — 빌드 거부. 번역을 줄이거나 압축 규칙을 적용하라.'
                         % (len(out) - SLOT_MAX))
    if len(out) > INPLACE_MAX:
        print('  ⚠️제자리 한계 초과 %d B — LINK 크기 필드 수정이 필요하다(디스크 섹터는 여유 있음).'
              % (len(out) - INPLACE_MAX))
    else:
        print('  ✓ 제자리 패치 가능 (여유 %d B)' % (INPLACE_MAX - len(out)))

    # ★해제 버퍼 게이트 — 압축 후 크기(위)와 **완전히 별개의 예산 축**이다.
    #   블록이 버퍼를 넘으면 넘긴 오프셋의 메시지가 조용히 안 나온다(크래시 아님).
    #   2026-07-29: 원인은 「할당 안 된 땅에 써서 보호를 못 받음」. e4_buffer 참조.
    import e4_buffer                                                   # noqa: E402
    sizes = [b[1] for b in ls11.parse_blocks(out)]
    budget = e4_buffer.NEW_SIZE if e4_buffer.ENABLED else e4_buffer.OLD_SIZE
    over = [(i, s) for i, s in enumerate(sizes) if s > budget]
    print('해제 버퍼 %d B  최대 블록 %d B (blk%d)  여유 %d B'
          % (budget, max(sizes), sizes.index(max(sizes)), budget - max(sizes)))
    if over:
        raise SystemExit('★★해제 버퍼 초과 %d개 — 빌드 거부: %s'
                         % (len(over), ', '.join('blk%d %d B(+%d)' % (i, s, s - budget)
                                                 for i, s in over)))

    back = ls11.decode_all(out)                     # ★빌더 밖 검증
    src = [ls11.decode_block(e4, i) for i in range(30)]
    same = sum(1 for a, b in zip(back, blocks) if a == b)
    print('  되읽기: %d/30 블록 일치' % same)
    if roundtrip:
        print('  ★구조 라운드트립(번역 0건): 30블록 내용 원본과 동일 = %s' % (back == src))
    open(OUT, 'wb').write(out)
    print('-> %s' % OUT)


if __name__ == '__main__':
    main()
