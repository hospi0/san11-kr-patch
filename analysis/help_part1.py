"""idx=3 메시지 0~415 ('파트1 조립테이블')을 실제로 디코드해 본다.

세션5에 `PART2_START_INDEX = 416 # 0~415 = 호칭·어미 조립 테이블(번역 금지·보존)`이라고
적어놨는데, **디코드해서 확인한 적이 없다.** 그런데 이 구간이 entry3의 **80%(97,417B)**다.
환경설정 도움말(「必ずプレイヤーが一騎討ちを見た上で操作を担当します」)이 s11pkres 전
엔트리·SLPM·Overlay 어디에도 평문으로 없으니, 여기에 있을 가능성이 크다.
(idx=3 코덱은 ESC K 반각 카타카나 모드를 쓴다 → 전각 `プレイヤー` 스캔으로는 안 잡힌다.)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import help_codec                                  # noqa: E402
from encoding import Codec                         # noqa: E402

ELF = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"
NEEDLES = ['プレイヤー', '一騎討ち', '操作', '担当', '見た上で', '物資面', '優遇',
           '難易度', '舌戦', 'メッセージ', 'カーソル', 'スクロール']


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    codec = Codec(ELF)
    d, offs, _ = help_codec.load(os.path.join(HERE, '..', 'work', 'entry3.bin'))
    segs = help_codec.segments(d, offs)
    out.write('# entry3 메시지 %d개 (평문 시작 인덱스 = %d)\n'
              % (len(segs), help_codec.PART2_START_INDEX))

    texts, fails = {}, 0
    for i, seg in enumerate(segs):
        try:
            texts[i] = help_codec.decode(seg, codec)
        except Exception as e:
            fails += 1
            texts[i] = '<디코드실패: %s>' % e
    out.write('# 디코드 실패 %d개\n\n' % fails)

    out.write('===== 크립 검색 (메시지 0~415 = "조립테이블"이라 불렀던 구간) =====\n')
    for nd in NEEDLES:
        hits = [i for i, t in texts.items() if nd in t]
        p1 = [i for i in hits if i < help_codec.PART2_START_INDEX]
        p2 = [i for i in hits if i >= help_codec.PART2_START_INDEX]
        out.write('  %-12s 총 %3d개  | 0~415: %-28s | 416~: %s\n'
                  % (nd, len(hits), str(p1[:8]) if p1 else '없음',
                     str(p2[:6]) if p2 else '없음'))

    out.write('\n===== 메시지 0~415 실물 (앞 40개) =====\n')
    for i in range(min(40, help_codec.PART2_START_INDEX)):
        out.write('%3d  %s\n' % (i, texts[i][:90]))

    out.write('\n===== 0~415 중 길이 20자 이상 (문장다운 것) =====\n')
    longs = [(i, t) for i, t in texts.items()
             if i < help_codec.PART2_START_INDEX and len(t) >= 20]
    out.write('%d개\n' % len(longs))
    for i, t in longs[:40]:
        out.write('%3d  %s\n' % (i, t[:90]))
    out.close()


if __name__ == '__main__':
    main()
