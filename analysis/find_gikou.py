"""스크린샷의 기교/능력 이름 원문이 어느 파일·어느 오프셋에 있는지 찾는다.

"특기 구역에 기교가 섞였나?"를 추측이 아니라 리터럴 문자열 위치로 판정한다.
entry5뿐 아니라 SLPM과 s11pkres 다른 엔트리도 같이 훑어야 "여기 없다"가 의미를 가진다
([[feedback_scan_coverage_and_detectors]]: 커버리지 없는 '배제 완료'는 무효).
"""
import io
import os
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
HERE = os.path.dirname(__file__)

# 스크린샷 2장에서 눈으로 읽은 것들
GIKOU = [  # 기교표
    '槍兵鍛錬', '戟兵鍛錬', '弩兵鍛錬', '騎兵鍛錬',
    '兵糧襲撃', '奇襲', '精鋭槍兵',
    '矢盾', '大盾', '精鋭戟兵',
    '応射', '強弩', '精鋭弩兵',
    '良馬産出', '技巧Ｐ', '必要技巧Ｐ', '関与能力',
]
NOURYOKU = [  # 능력표(연구)
    '金剛', '不屈', '鉄壁', '待伏', '築城', '繁殖', '名声',
    '槍兵', '水軍', '戟兵', '弩兵', '騎兵', '兵器',
]


def scan(path, needles, out, label):
    d = open(path, 'rb').read()
    out.write('\n=== %s (%s, %d B) ===\n' % (label, os.path.basename(path), len(d)))
    for s in needles:
        b = s.encode('cp932')
        hits = []
        i = d.find(b)
        while i >= 0 and len(hits) < 8:
            hits.append(i)
            i = d.find(b, i + 1)
        if hits:
            out.write('  %-8s %2d개: %s\n' % (s, len(hits), ' '.join('0x%x' % h for h in hits)))
        else:
            out.write('  %-8s  없음\n' % s)


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    for label, needles in (('기교표', GIKOU), ('능력표', NOURYOKU)):
        out.write('\n########## %s ##########\n' % label)
        scan(os.path.join(HERE, '..', 'work', 'entry5.bin'), needles, out, 'entry5')
        scan(os.path.join(ROM, 'SLPM_667.01'), needles, out, 'SLPM')
    out.close()


if __name__ == '__main__':
    main()
