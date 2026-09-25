"""entry5 특기 구역의 카타카나 '읽기' 앵커를 순서대로 뽑는다.

레코드 포맷이 아직 미해독이라 이름/설명은 경계가 흔들리지만, 카타카나 읽기는
항목당 정확히 하나씩 있고 순수 카타카나라 오검출이 적다(docs/10). 그래서 읽기를
목록의 뼈대로 삼아 "이 구역에 무엇이 들어 있나"를 먼저 센다.
"""
import io
import os
import re
import sys

REGION = (0x5400, 0x6c00)
ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')

# 전각 카타카나 + 장음 + 중점
KATA = re.compile(r'^[ァ-ヶー・]+$')


def sjis_strings(blob, base):
    """널종료 SJIS 문자열을 (오프셋, 텍스트)로 흘려보낸다."""
    i = 0
    while i < len(blob):
        j = blob.find(b'\x00', i)
        if j < 0:
            break
        chunk = blob[i:j]
        if chunk:
            try:
                yield base + i, chunk.decode('cp932')
            except UnicodeDecodeError:
                pass
        i = j + 1


def main():
    lo, hi = REGION
    blob = open(ENTRY5, 'rb').read()[lo:hi]
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    n = 0
    for off, s in sjis_strings(blob, lo):
        # 3글자 미만은 연관특기 조각·노이즈(docs/10: ガン/イ/レン/カル)
        if len(s) >= 3 and KATA.match(s):
            n += 1
            out.write('%d\t0x%04x\t%s\n' % (n, off, s))
    out.write('# 카타카나 읽기 후보 %d개\n' % n)
    out.close()


if __name__ == '__main__':
    main()
