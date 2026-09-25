"""entry4_kr.bin을 **빌더와 무관하게 새로 파싱**해 block23을 검증한다.

빌더 자체검사는 자기가 만든 것과 자기를 비교하므로 통과해도 의미가 약하다
(세션7에 기교 이름 36개가 널로 날아갔는데 빌더 검사는 전부 통과했다).
여기서는 산출물 바이트만 읽어서:
  ① 번역한 줄  = TSV의 kr과 글자단위 일치하는가
  ② 번역 안 한 줄 = 원본 entry4와 **바이트 동일**한가 (빈 값이 원본을 지우지 않았는가)
  ③ 메시지 개수 = 736개 그대로인가

Usage: python analysis/verify_e4_sys.py
"""
import io
import os
import sys
import unicodedata as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import ls11                                              # noqa: E402
from help_codec import parse_offsets, segments, decode   # noqa: E402
from encoding import Codec                               # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
BLOCK = 23


def main():
    src = open('work/entry4.bin', 'rb').read()
    new = open('work/entry4_kr.bin', 'rb').read()
    codec = Codec(ELF)

    d_old = ls11.decode_block(src, BLOCK)
    d_new = ls11.decode_block(new, BLOCK)
    s_old = segments(d_old, parse_offsets(d_old))
    s_new = segments(d_new, parse_offsets(d_new))
    print('메시지 개수: 원본 %d -> 빌드 %d  %s'
          % (len(s_old), len(s_new), 'OK' if len(s_old) == len(s_new) else '★불일치'))

    kr = {}
    for ln in io.open('work/e4_sys.tsv', encoding='utf-8'):
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit() and p[4].strip():
            kr[int(p[1])] = U.normalize('NFC', p[4]).strip()

    ok_tr = bad_tr = ok_keep = bad_keep = 0
    for i, (a, b) in enumerate(zip(s_old, s_new)):
        if i in kr:
            got = U.normalize('NFC', decode(b, codec))
            # split_pad가 앞뒤 05/00 패딩을 따로 붙이므로 양끝 제어바이트는 무시하고 비교
            want = kr[i]
            if want in got:
                ok_tr += 1
            else:
                bad_tr += 1
                if bad_tr <= 5:
                    print('★[%d] 되읽기 불일치\n   기대: %s\n   실제: %s' % (i, want[:70], got[:70]))
        else:
            if a == b:
                ok_keep += 1
            else:
                bad_keep += 1
                if bad_keep <= 5:
                    print('★[%d] 미번역인데 바이트가 바뀌었다 (%d B -> %d B)' % (i, len(a), len(b)))

    print('번역줄  : %d 일치 / %d 불일치' % (ok_tr, bad_tr))
    print('미번역줄: %d 원본유지 / %d 오염' % (ok_keep, bad_keep))

    other = sum(1 for i in range(30) if i != BLOCK
                and ls11.decode_block(src, i) != ls11.decode_block(new, i))
    print('block23 외 29블록 중 내용이 바뀐 것: %d개 (0이어야 정상)' % other)
    return 1 if (bad_tr or bad_keep or other) else 0


if __name__ == '__main__':
    sys.exit(main())
