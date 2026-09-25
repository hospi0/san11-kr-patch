"""환경설정 도움말의 RAM 이웃을 보고 디스크 출처를 역추적한다.

RAM 0x1cd4554 에 「必ずプレイヤーが一騎討ちを見た上で操作を担当します」가 있는데
디스크(s11pkres 전 9,383엔트리 + SLPM + Overlay + modules/pkres)엔 평문이 없다.
= [[feedback_compressed_corpus_scan]]의 "디스크엔 없는데 RAM엔 있다" = **압축 소스 신호**.

검정 방법:
 1. RAM 청크를 디스크에서 찾아본다 — **일부라도 그대로 있으면 비압축**, 하나도 없으면 압축.
    (한 문자열이 아니라 여러 길이의 청크로 봐야 한다. 짧으면 노이즈로 우연히 맞는다.)
 2. RAM 이웃 문자열을 훑어 **어느 화면/엔트리인지** 정체를 파악한다.
 3. ★기존 앵커: entry3 = RAM 0x1cd6400 (디스크 섹터 572). 우리 문자열 0x1cd4554는
    그보다 **0x1eac 앞** = entry3 바로 앞에 로드된 무언가다.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(__file__)
RAM = os.path.join(HERE, '..', 'work', 'state_cfg', 'eeMemory.bin')
S11 = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\s11pkres.bin"
HIT = 0x1cd4554
E3_RAM = 0x1cd6400          # 세션5 실측: entry3가 여기에 통째로 올라온다


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    ram = open(RAM, 'rb').read()
    s11 = open(S11, 'rb').read()

    out.write('# RAM 히트 0x%x / entry3 RAM base 0x%x → 차이 -0x%x\n\n' % (HIT, E3_RAM, E3_RAM - HIT))

    out.write('===== 1. RAM 청크가 디스크에 있나 (압축 여부 판정) =====\n')
    for ln in (8, 16, 24, 32, 48, 64, 96, 128):
        chunk = ram[HIT:HIT + ln]
        n = 0
        i = s11.find(chunk)
        while i >= 0 and n < 3:
            n += 1
            i = s11.find(chunk, i + 1)
        out.write('  RAM[0x%x : +%3d] → s11pkres에서 %d개  %s\n'
                  % (HIT, ln, n, chunk[:16].hex(' ')))
    out.write('  (짧은 청크만 맞고 길어지면 0 → 노이즈. 긴 청크가 맞아야 비압축이다.)\n')

    out.write('\n===== 2. RAM 이웃 문자열 (이 블록의 정체) =====\n')
    lo, hi = HIT - 0x1200, HIT + 0x1200
    off = lo
    while off < hi:
        e = ram.find(b'\x00', off)
        if e < 0 or e > hi:
            break
        if e > off + 3:
            try:
                t = ram[off:e].decode('cp932')
                if len(t) >= 3 and not re.search(r'[\x00-\x1f]', t):
                    mark = '  ★히트' if off == HIT else ''
                    out.write('0x%07x (%3d)  %s%s\n' % (off, e - off, t[:70], mark))
            except UnicodeDecodeError:
                pass
        off = e + 1
    out.close()


if __name__ == '__main__':
    main()
