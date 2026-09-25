"""SLPM의 특기/기교 이름 구역(0x4a0000대)을 덤프한다.

entry5 특기 레코드는 문자열이 2바이트씩 어긋나 보인다(찌꺼기 프리픽스). 정답 설명문을
따로 확보하면 그걸 크립으로 entry5 안 진짜 오프셋을 잡을 수 있다.
find_gikou 결과: SLPM 0x4a0898~0x4a1888에 특기·기교 이름이 몰려 있다.
"""
import io
import os
import sys

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"


def main():
    lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
    d = open(os.path.join(ROM, 'SLPM_667.01'), 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    off = lo
    while off < hi:
        end = d.find(b'\x00', off)
        if end < 0 or end >= hi:
            break
        chunk = d[off:end]
        if chunk:
            try:
                s = chunk.decode('cp932')
                out.write('0x%06x  (%3d)  %s\n' % (off, len(chunk), s))
            except UnicodeDecodeError:
                out.write('0x%06x  (%3d)  <bin> %s\n'
                          % (off, len(chunk), chunk[:24].hex(' ')))
        off = end + 1
    out.close()


if __name__ == '__main__':
    main()
