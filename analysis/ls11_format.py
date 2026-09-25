"""LS11 컨테이너 포맷 해독 (2026-07-17 세션7).

## 포맷 (오프셋 체인으로 자기검증됨)
```
0x000  "LS11" + 0패딩 12B
0x010  256B = 0~255의 **순열** (허프만 심볼 테이블)     ★고유 256/256 확인
0x110  블록 테이블: (압축크기 u32BE, 원본크기 u32BE, 데이터오프셋 u32BE) × N
0x27c~ 블록 데이터 (첫 블록 오프셋 = 636 = 0x27c)
```
★**엔디안은 빅엔디안**(PS2는 LE지만 이 데이터는 BE다).
★**자기검증**: off[k+1] == off[k] + comp[k] 가 전 블록에서 성립해야 한다.
★**앵커**: 블록0의 원본크기 = **75,218 = 환경설정 텍스트 풀 크기와 정확히 일치**
  (RAM 0x1da1c00에서 뜬 749개 메시지 풀. idx=3 코덱으로 749/749 디코드 성공).

## 압축 알고리즘
비트스트림(1비율 0.641, 0xff가 평균의 16배) + 256 심볼 순열 = **허프만 계열**로 추정.
아직 **미해독**. 다만 블록0의 (입력, 정답출력) 쌍을 확보했으므로 디코더를 짜면 즉시 검증된다.
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(__file__)
E4 = os.path.join(HERE, '..', 'work', 'entry4.bin')
POOL = os.path.join(HERE, '..', 'work', 'entry4_pool.bin')
TAB = 0x110


def parse(d):
    """(심볼순열, [(압축크기, 원본크기, 오프셋)]) — 체인이 안 맞으면 예외."""
    assert d[:4] == b'LS11', 'LS11 매직 아님'
    perm = d[0x10:0x110]
    assert sorted(perm) == list(range(256)), '0x10의 256B가 순열이 아님'
    blocks, i = [], 0
    while True:
        o = TAB + i * 12
        c, u, p = struct.unpack('>III', d[o:o + 12])
        if not blocks:
            first = p
        if p >= len(d) or c == 0 or c > len(d):
            break
        blocks.append((c, u, p))
        # 체인 검증: 다음 블록 오프셋 == 현재 오프셋 + 압축크기
        if TAB + (i + 1) * 12 + 12 > first:
            break
        nc, nu, np_ = struct.unpack('>III', d[o + 12:o + 24])
        if np_ != p + c:
            break
        i += 1
    return perm, blocks, first


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    d = open(E4, 'rb').read()
    pool = open(POOL, 'rb').read()
    perm, blocks, first = parse(d)

    out.write('entry4 %d B / 심볼 순열 256/256 ✅ / 첫 블록 오프셋 0x%x(%d)\n' % (len(d), first, first))
    out.write('블록 테이블 0x%x ~ 0x%x → %d블록 (12B × %d = %d B)\n\n'
              % (TAB, TAB + len(blocks) * 12, len(blocks), len(blocks), len(blocks) * 12))

    out.write('idx  압축크기   원본크기   오프셋      체인검증\n')
    tot_c = tot_u = 0
    ok = True
    for k, (c, u, p) in enumerate(blocks):
        exp = first if k == 0 else blocks[k - 1][2] + blocks[k - 1][0]
        good = (p == exp)
        ok &= good
        mark = '✅' if good else '❌ 기대 %d' % exp
        if u == len(pool):
            mark += '  ★원본크기가 풀(%d)과 일치' % len(pool)
        out.write('%3d  %8d  %8d  %8d  %s\n' % (k, c, u, p, mark))
        tot_c += c
        tot_u += u
    last = blocks[-1]
    end = last[2] + last[0]
    out.write('\n압축 합계 %d B (+헤더 %d = %d)  / entry4 %d B → %s\n'
              % (tot_c, first, tot_c + first, len(d),
                 '딱 맞음 ✅' if tot_c + first == len(d) else '남는 %d B' % (len(d) - tot_c - first)))
    out.write('마지막 블록 끝 0x%x(%d) / entry4 0x%x(%d)\n' % (end, end, len(d), len(d)))
    out.write('원본 합계 %d B (압축 %d B → %.2fx)\n' % (tot_u, tot_c, tot_u / tot_c))
    out.write('체인 전부 일치: %s\n' % ('✅✅' if ok else '❌'))

    out.write('\n=== 블록0 = 환경설정 풀인가 ===\n')
    c, u, p = blocks[0]
    out.write('  블록0: 압축 %d B @0x%x → 원본 %d B\n' % (c, p, u))
    out.write('  풀 크기 %d → %s\n' % (len(pool), '일치 ✅★' if u == len(pool) else '불일치'))
    out.write('  → 디코더를 짜면 e4[0x%x : 0x%x] 가 work/entry4_pool.bin 과 같아야 한다.\n'
              % (p, p + c))
    out.close()


if __name__ == '__main__':
    main()
