"""테이블 하나를 세로로 세워 필드 경계를 통계로 잡는다(특기/기교/능력 공용).

tokki_columns.py를 세 테이블에 쓰도록 일반화한 것. 널을 따라 걷는 파서는 필드의
남는 꼬리에 있는 옛 찌꺼기를 문자열 시작으로 오인해 2바이트 어긋난다
(특기에서 이걸로 데였다). 그래서 **필드 오프셋을 전수 통계로 먼저 확정**한다.

읽는 법:
  널 100% 열      = 고정길이 필드의 종료자
  0x83 100% 열    = 카타카나 리드바이트 = 읽기 필드 시작
  널 0% + 짝수열만 값종류 적음 = SJIS 본문(2바이트 정렬) = 설명 필드
  값 종류 몇 개뿐 = 바이너리 플래그/수치
"""
import io
import os
import sys
from collections import Counter

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')

TABLES = {
    '특기': (0x5210, 0x5d, 100),
    '기교': (0x7664, 0x5c, 36),
    '능력': (0x9e64, 0x4a, 98),
}


def report(blob, name, base, stride, count, out):
    recs = [blob[base + i * stride: base + (i + 1) * stride] for i in range(count)]
    out.write('\n===== %s: base 0x%x stride 0x%x count %d =====\n' % (name, base, stride, count))
    out.write('off   널%%  0x83%%  값종류  가장흔한값  판정\n')
    for c in range(stride):
        col = [r[c] for r in recs]
        nulls = 100 * col.count(0) // count
        lead83 = 100 * col.count(0x83) // count
        cnt = Counter(col)
        top, n = cnt.most_common(1)[0]
        verdict = ''
        if nulls >= 95:
            verdict = '← 항상 널 = 필드 경계'
        elif lead83 >= 95:
            verdict = '← 항상 0x83 = 카타카나'
        elif len(cnt) <= 4:
            verdict = '← 값 %d종 = 바이너리 필드' % len(cnt)
        elif nulls == 0 and len(cnt) <= 24 and c % 2 == 0:
            verdict = '← 널0%% & 종류적음 = SJIS 리드'
        out.write('+0x%02x  %3d  %4d  %5d   0x%02x(%d)  %s\n'
                  % (c, nulls, lead83, len(cnt), top, n, verdict))


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    for name in sys.argv[2:] or TABLES:
        base, stride, count = TABLES[name]
        report(blob, name, base, stride, count, out)
    out.close()


if __name__ == '__main__':
    main()
