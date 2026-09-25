"""RAM 매핑 공식을 **패치된 ISO**와 대조해 진짜인지 확정한다.

앞선 검증은 **원본 s11pkres**와 비교했는데, 스테이트는 **패치된 빌드**에서 뜬 것이라
"불일치 = 내가 패치한 엔트리"라고 해석했다. 그 해석이 맞다면 **패치된 ISO와는 완전 일치**해야 한다.
안 맞으면 공식이 틀렸거나 런타임에 덮어써진 것이고, 그러면 "환경설정 = entry4" 추론도 무너진다.

모순 관측: `物資面`이 RAM 0x1da7026(= entry5 + 0x5426)에 있는데 **entry5 디스크엔 없다**.
"""
import io
import os
import struct
import sys

ISO = "C:/claude/roms/ps2/San11_kr.iso"
S11_OFF = 0x73e000            # ISO 안 S11PKRES.BIN 위치
RB = 0x1BB8400                # RAM = RB + 섹터*0x800 (세션5 실측, 엔트리3·4)
RAM = os.path.join(os.path.dirname(__file__), '..', 'work', 'state_cfg', 'eeMemory.bin')


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    ram = open(RAM, 'rb').read()
    f = open(ISO, 'rb')
    f.seek(S11_OFF)
    s11 = f.read(517752832)
    f.close()

    n, sec = struct.unpack('<II', s11[4:12])
    tab = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]

    out.write('=== 패치된 ISO의 엔트리 vs 스테이트 RAM ===\n')
    out.write('(스테이트가 이 빌드에서 떴다면 **완전 일치**해야 한다)\n\n')
    for i in (2, 3, 4, 5):
        o, b = tab[i]
        disc = s11[o * sec: o * sec + b]
        r0 = RB + o * 0x800
        live = ram[r0: r0 + b]
        same = disc == live
        nd = sum(1 for x, y in zip(disc, live) if x != y)
        out.write('  idx%-2d 섹터%-5d 크기%-8d RAM 0x%x  일치=%s  다른바이트 %d (%.2f%%)\n'
                  % (i, o, b, r0, '✅' if same else '❌', nd, 100.0 * nd / max(1, b)))

    out.write('\n=== 모순 지점: 物資面 @RAM 0x1da7026 ===\n')
    hit = 0x1da7026
    o5, b5 = tab[5]
    r5 = RB + o5 * 0x800
    rel = hit - r5
    out.write('  entry5 RAM base 0x%x, 크기 %d → 히트는 rel 0x%x (%s)\n'
              % (r5, b5, rel, '범위 안' if 0 <= rel < b5 else '범위 밖!'))
    out.write('  같은 자리 디스크(패치본) 바이트: %s\n' % s11[o5 * sec + rel: o5 * sec + rel + 16].hex(' '))
    out.write('  같은 자리 RAM          바이트: %s\n' % ram[hit: hit + 16].hex(' '))
    out.write('  → %s\n' % ('같다 = 디스크에 있다' if s11[o5 * sec + rel:o5 * sec + rel + 16] == ram[hit:hit + 16]
                            else '다르다 = **런타임에 덮어써졌다** = 매핑을 그대로 믿으면 안 됨'))
    out.close()


if __name__ == '__main__':
    main()
