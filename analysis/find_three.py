"""아이템 이름 · 작위 · 환경설정 도움말의 위치를 찾는다 (2026-07-17 세션7 말, 사용자 지목).

s11pkres.bin 전체(517MB) + SLPM을 리터럴로 훑는다. 엔트리별로 어디에 걸리는지 같이 찍어야
"어느 엔트리를 패치할지"가 나온다.

⚠️세션6에 환경설정 도움말을 「SLPM/e3/e5/e94에 `物資面`·`プレイヤー` 없음 = 위치 미특정」으로
남겼는데, **그건 4개 엔트리만 본 것**이다([[feedback_scan_coverage_and_detectors]] — 샘플을
전수로 기록하지 말 것). 이번엔 s11pkres **전 엔트리**를 본다.
★가설: 카타카나가 **반각**으로 저장돼 있어 전각 `プレイヤー`로는 안 잡혔을 수 있다
  (idx=3 도움말이 ESC K 반각 카타카나 모드를 쓴다 — help_codec.py 참조). 둘 다 찾는다.
"""
import io
import os
import struct
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')
ELF = os.path.join(ROM, 'SLPM_667.01')

NEEDLES = {
    '환경설정 도움말': ['操作を担当', '一騎討ち', '見た上で', '必ずプレイヤー', 'プレイヤー',
                   '物資面', '優遇'],
    '아이템 이름': ['倚天の剣', '七星宝刀', '青龍偃月刀', '赤兎馬', '爪黄飛電', '青釭の剣',
                '孫子の兵法書', '手戟'],
    '작위': ['大司馬', '州刺史', '州牧', '大将軍'],
}
# 반각 카타카나(ｱｲｳ…) 판본 — 전각으로 못 찾을 때의 대비
HALFWIDTH = {'プレイヤー': 'ﾌﾟﾚｲﾔｰ', '一騎討ち': None}


def entry_of(off, table, sec):
    """파일 오프셋 → LINK 엔트리 번호."""
    for i, (o, b) in enumerate(table):
        if o * sec <= off < o * sec + b:
            return i, off - o * sec
    return None, None


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    s11 = open(S11, 'rb').read()
    # ⚠️LINK 헤더 = 0x00 "LINK" / **0x04 엔트리수** / **0x08 섹터크기** (docs/01, tools/link.py).
    #   처음에 개수를 0x0c에서 읽어 "엔트리 0개"가 나왔다.
    assert s11[:4] == b'LINK'
    n, sec = struct.unpack('<II', s11[4:12])
    table = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]
    out.write('# s11pkres: 엔트리 %d개, 섹터크기 %d\n' % (n, sec))

    others = {'SLPM': open(ELF, 'rb').read()}
    for f in ('Overlay1.bin', 'Overlay2.bin'):        # ⚠️세션6엔 이 둘을 안 봤다
        others[f] = open(os.path.join(ROM, f), 'rb').read()

    for group, needles in NEEDLES.items():
        out.write('\n########## %s ##########\n' % group)
        for s in needles:
            variants = [(s, s.encode('cp932'))]
            hw = HALFWIDTH.get(s)
            if hw:
                variants.append((hw + '(반각)', hw.encode('cp932')))
            for label, b in variants:
                hits = []
                i = s11.find(b)
                while i >= 0 and len(hits) < 6:
                    e, rel = entry_of(i, table, sec)
                    hits.append('e%s+0x%x' % (e, rel) if e is not None else '0x%x(밖)' % i)
                    i = s11.find(b, i + 1)
                oth = ' '.join('%s@0x%x' % (k, v.find(b)) for k, v in others.items()
                               if v.find(b) >= 0)
                out.write('  %-16s s11pkres %d개 %-46s %s\n'
                          % (label, len(hits), ' '.join(hits), oth))
    out.close()


if __name__ == '__main__':
    main()
