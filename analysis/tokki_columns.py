"""특기 레코드 100개를 세로로 세워 필드 경계를 통계로 잡는다.

레코드 안에서 문자열이 2바이트씩 어긋나 보이는 이유를 추측으로 때우지 않고,
"널 종료자가 고정 위치에 오는가"를 100개 전수로 센다.
- 널 비율이 높은 열 = 고정 길이 필드의 종료자
- 널 비율이 0인 열 = 항상 데이터
[[feedback_scan_coverage_and_detectors]]: 검출기엔 양성(널)·음성(비널)·분포를 같이 본다.
"""
import io
import os
import sys
from collections import Counter

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
BASE, STRIDE, COUNT = 0x5210, 0x5d, 100


def main():
    blob = open(ENTRY5, 'rb').read()
    recs = [blob[BASE + i * STRIDE: BASE + (i + 1) * STRIDE] for i in range(COUNT)]
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    out.write('# 특기 레코드 %d개, base 0x%x stride 0x%x\n' % (COUNT, BASE, STRIDE))
    out.write('# 열별 널(0x00) 비율 — 높으면 고정 필드 종료자\n\n')
    out.write('off   널%   가장흔한값(횟수)   서로다른값수\n')
    for c in range(STRIDE):
        col = [r[c] for r in recs]
        nulls = col.count(0)
        cnt = Counter(col)
        top, n = cnt.most_common(1)[0]
        mark = ''
        if nulls >= COUNT * 0.9:
            mark = '  ← 거의 항상 널 = 필드 경계'
        elif nulls >= COUNT * 0.4:
            mark = '  ← 자주 널'
        out.write('+0x%02x  %3d%%  0x%02x (%3d)        %3d%s\n'
                  % (c, 100 * nulls // COUNT, top, n, len(cnt), mark))
    out.close()


if __name__ == '__main__':
    main()
