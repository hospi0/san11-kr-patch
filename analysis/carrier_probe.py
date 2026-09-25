"""화면에 보인 깨진 글자 -> 원래 한자 역추적.

운반체 방식이라 한자 슬롯 위에 한글이 덧칠돼 있다. 미번역 일본어 문자열이
화면에 뜨면 그 한자 자리에 한글 음절이 대신 그려진다. 이 스크립트는 그 대응을
양방향으로 찍어, 스크린샷의 「쳐」「짓」 같은 글자가 원래 무슨 한자였는지 확인한다.
"""
import io
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from encoding import Codec

ELF = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"

# 스크린샷 2장에 보이는(또는 후보로 의심되는) 한자
PROBE = "鍛錬訓練増加政精鋭屈金剛鉄壁待伏築城繁殖名声槍兵水軍戟弩騎器奇襲矢盾大応射強不低武統知育帰討"


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    c = Codec(ELF)
    for ch in dict.fromkeys(PROBE):
        sj = struct.unpack('>H', ch.encode('cp932'))[0]
        syl = c.dec.get(sj)
        out.write('%s SJIS=%04x -> %s\n' % (ch, sj, syl if syl else '(여분한자: 안 덧칠됨)'))
    out.close()


if __name__ == '__main__':
    main()
