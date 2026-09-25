"""특기 구역의 레코드 간격과, 레코드 안에 섞인 '두 번째 카타카나'를 확인한다.

docs/10에서 관직 레코드는 [이름\\0 읽기\\0 연관특기\\0 스탯]이었다. 특기 레코드도
같은 꼴이면 레코드 하나에 카타카나가 둘 이상 들어간다 -- 그러면 "기교 이름이
섞여 있다"가 아니라 "특기 레코드가 기교를 참조한다"가 된다. 둘은 완전히 다른
결론이므로 간격으로 먼저 가른다.
"""
import io
import os
import re
import sys

REGION = (0x5400, 0x6c00)
ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
KATA = re.compile(r'^[ァ-ヶー・]+$')


def sjis_strings(blob, base):
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

    # 앞 글자가 잘린 카타카나(찌꺼기 프리픽스)도 잡으려면 순수-카타카나 필터를
    # 쓰면 안 된다. 꼬리가 카타카나 3자 이상이면 후보로 본다.
    hits = []
    for off, s in sjis_strings(blob, lo):
        m = re.search(r'[ァ-ヶー]{3,}$', s)
        if m:
            hits.append((off + (len(s) - len(m.group())) * 2, m.group(), s, KATA.match(s) is not None))

    out.write('# 카타카나 꼬리를 가진 문자열 %d개 (앞잘림 포함)\n' % len(hits))
    out.write('# off\tdelta\t순수?\t읽기\t원문자열\n')
    prev = None
    for off, kata, whole, pure in hits:
        d = '' if prev is None else '0x%x' % (off - prev)
        out.write('0x%04x\t%s\t%s\t%s\t%s\n' % (off, d, 'Y' if pure else 'N', kata, whole))
        prev = off
    out.close()


if __name__ == '__main__':
    main()
