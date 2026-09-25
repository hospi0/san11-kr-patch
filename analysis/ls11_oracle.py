"""LS11 해독용 입력/출력 쌍(오라클)을 확보한다.

## 왜 이게 되나
- **입력** = entry4 (디스크, "LS11" 매직, 709,268B) — RAM 0x1cf4400에 **압축된 채로** 올라간다(검증 ✅).
- **출력** = RAM **0x1da1c00~** = entry4를 푼 결과. entry4 끝(0x1cf4400+709268 = 0x1da1854)
  **바로 뒤**에 있다.
- 즉 압축 알고리즘을 모르는 채로도 **정답 출력을 이미 갖고 있다** → 디컴프레서를 짜면 즉시 검증된다.

⚠️「RAM = 0x1BB8400 + 섹터×0x800」 공식은 **idx3·idx4에서만 성립**한다(패치본과 완전 일치로 확인).
  idx2는 76%, idx5는 99% 다르다 = **그 자리엔 다른 게 올라온다**. 공식을 전 엔트리로 일반화하지 말 것.

## 풀의 정체
0x1da7026에 `物資面` + 반각가나 + **ESC K(1b 4b)** + `ﾌﾟﾚ…` = **idx=3 도움말과 같은 코덱**이다
(help_codec.py: ESC K/k = 카타카나 모드, 반각 1B 저장). 전각 `プレイヤー`로 스캔해도 안 잡혔던 이유.
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(__file__)
RAM = os.path.join(HERE, '..', 'work', 'state_cfg', 'eeMemory.bin')
E4_RAM, E4_SIZE = 0x1cf4400, 709268
POOL = 0x1da1c00                      # entry4 끝(0x1da1854) 직후


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    ram = open(RAM, 'rb').read()
    out.write('entry4 RAM 0x%x ~ 0x%x (압축본)\n' % (E4_RAM, E4_RAM + E4_SIZE))
    out.write('풀 후보 0x%x 부터\n\n' % POOL)

    out.write('=== 풀 선두 128B ===\n')
    for b in range(POOL, POOL + 128, 16):
        row = ram[b:b + 16]
        out.write('%08x  %-47s |%s|\n' % (b, ' '.join('%02x' % x for x in row),
                  ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))

    # idx=3과 같은 구조인가? [u16 count][u32 offs × count], offs[0] == 2+4*count
    cnt = struct.unpack('<H', ram[POOL:POOL + 2])[0]
    out.write('\n=== idx=3식 구조 검정 ([u16 개수][u32 오프셋테이블]) ===\n')
    out.write('  u16 @+0 = %d\n' % cnt)
    if 0 < cnt < 20000 and POOL + 2 + 4 * cnt < len(ram):
        offs = list(struct.unpack('<%dI' % cnt, ram[POOL + 2: POOL + 2 + 4 * cnt]))
        ok0 = offs[0] == 2 + 4 * cnt
        asc = all(offs[i] <= offs[i + 1] for i in range(min(cnt, 400) - 1))
        out.write('  offs[0] = 0x%x / 기대 0x%x → %s  ★idx=3의 자기검증 규칙\n'
                  % (offs[0], 2 + 4 * cnt, '일치 ✅' if ok0 else '불일치 ❌'))
        out.write('  오름차순(앞 400개): %s\n' % ('✅' if asc else '❌'))
        out.write('  마지막 오프셋 = 0x%x → 풀 크기 추정 %d B\n' % (offs[-1], offs[-1]))
        out.write('  앞 8개 오프셋: %s\n' % [hex(o) for o in offs[:8]])
        # 物資面 히트가 몇 번 메시지인지
        hit = 0x1da7026 - POOL
        idx = max([i for i, o in enumerate(offs) if o <= hit], default=None)
        out.write('  物資面(pool+0x%x)은 메시지 #%s 안 (그 메시지 시작 0x%x)\n'
                  % (hit, idx, offs[idx] if idx is not None else -1))
    else:
        out.write('  → 개수가 말이 안 됨. 구조가 다르다.\n')

    # 풀의 끝 찾기 — 0이 길게 이어지는 지점
    out.write('\n=== 풀이 어디까지인가 (0 런 탐색) ===\n')
    z = 0
    for i in range(POOL, min(POOL + 0x120000, len(ram))):
        if ram[i] == 0:
            z += 1
            if z >= 4096:
                out.write('  0x%x 부터 0이 4096B 이상 연속 → 풀 끝 추정 0x%x (크기 %d B)\n'
                          % (i - z + 1, i - z + 1, i - z + 1 - POOL))
                break
        else:
            z = 0
    out.close()


if __name__ == '__main__':
    main()
