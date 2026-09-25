"""엔트리별 RAM 슬롯 테이블을 찾는다 — entry4를 키울 수 있는지 판정용.

## 왜 먼저 해야 하나
무압축 테스트는 entry4를 **709,268 → 741,765 B**로 키운다(블록0만 무압축: 42,721→75,218).
그런데 RAM에서 entry4는 0x1cf4400, 풀은 0x1da1c00 — **틈이 0x56c(1,388B)뿐**이다.
32,497B를 키우면 풀을 깔아뭉갠다.

세션5에 **RAM 0x1cd5188 = `[0001e000][01cd6400]` = (슬롯크기, 주소)** 를 찾았고, 그래서
**entry3는 0x1E000 고정 슬롯**이고 넘기면 부팅이 죽는다는 걸 실기 이분 실험으로 확정했다(docs/11).
→ **같은 슬롯 테이블에 entry4 항목이 있을 것이다. 그 크기가 entry4의 한계다.**

## 찾는 법
`[u32 슬롯크기][u32 주소]` 형태를 가정하고 **주소 = 0x1cf4400(entry4 RAM)**로 역검색한다.
LE/BE 둘 다 본다. 찾으면 그 앞뒤로 다른 엔트리 슬롯도 줄줄이 나올 것이다(테이블이니까).
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(__file__)
RAM = os.path.join(HERE, '..', 'work', 'state_cfg', 'eeMemory.bin')

KNOWN = {
    0x1c01c00: 'entry2 아틀라스',
    0x1cd6400: 'entry3 도움말 (슬롯 0x1E000 확정)',
    0x1cf4400: 'entry4 LS11 ★이번 관심사',
    0x1da1c00: '풀(entry4 블록0 해제본)',
}


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    ram = open(RAM, 'rb').read()

    out.write('=== 세션5가 찾은 앵커 재확인: RAM 0x1cd5188 ===\n')
    a = ram[0x1cd5188:0x1cd5188 + 16]
    out.write('  바이트: %s\n' % a.hex(' '))
    out.write('  LE u32: %s\n' % [hex(x) for x in struct.unpack('<4I', a)])
    out.write('  BE u32: %s\n' % [hex(x) for x in struct.unpack('>4I', a)])

    out.write('\n=== 각 엔트리 RAM 주소를 RAM 전체에서 역검색 ===\n')
    for addr, label in KNOWN.items():
        for tag, packed in (('LE', struct.pack('<I', addr)), ('BE', struct.pack('>I', addr))):
            hits, i = [], ram.find(packed)
            while i >= 0 and len(hits) < 6:
                hits.append(i)
                i = ram.find(packed, i + 1)
            if hits:
                out.write('  0x%08x %-28s %s: %d곳 %s\n'
                          % (addr, label, tag, len(hits), ' '.join('0x%x' % h for h in hits)))

    out.write('\n=== 0x1cd5188 주변 = 슬롯 테이블인가 (LE [크기][주소] 쌍으로 읽기) ===\n')
    base = 0x1cd5188 - 0x40
    for k in range(24):
        o = base + k * 8
        sz, ad = struct.unpack('<II', ram[o:o + 8])
        note = KNOWN.get(ad, '')
        plaus = (0 < sz < 0x400000) and (0x1000000 < ad < 0x2000000)
        out.write('  0x%07x  크기 0x%-8x 주소 0x%-9x %s%s\n'
                  % (o, sz, ad, '← 그럴듯' if plaus else '', ('  ★' + note) if note else ''))
    out.close()


if __name__ == '__main__':
    main()
