"""특기 구역(0x5400~0x6c00)에서 뽑은 '특기 후보'에 기교가 몇 개 섞였는지 센다.

사용자 지적("기교/능력이 특기 번역에 섞인 것 아니냐")의 정량 확인.
기교 테이블(0x7664 stride 0x5c)의 읽기를 정답지로 삼아 대조한다.
"""
import io
import os
import re
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
KATA = re.compile(r'^[ァ-ヶー・]+$')
REGION = (0x5400, 0x6c00)


def cstr(blob, off):
    end = blob.find(b'\x00', off)
    if end < 0:
        return None, len(blob)
    try:
        return blob[off:end].decode('cp932'), end + 1
    except UnicodeDecodeError:
        return None, end + 1


def gikou_names(blob):
    """기교 36개의 이름 + 읽기를 정답지로 모은다."""
    names, readings = {}, {}
    for i in range(36):
        off = 0x7664 + i * 0x5c
        nm, nxt = cstr(blob, off)
        names[nm] = off
        o = nxt
        while o < off + 0x5c:
            s, n2 = cstr(blob, o)
            if s and len(s) >= 3 and KATA.match(s):
                readings[s] = (nm, off)
                break
            if n2 <= o:
                break
            o = n2
    return names, readings


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    gnames, greadings = gikou_names(blob)

    lo, hi = REGION
    off = lo
    hits, total = [], 0
    while off < hi:
        s, nxt = cstr(blob, off)
        if s and len(s) >= 3 and KATA.match(s):
            total += 1
            # 꼬리 일치도 본다(앞글자가 찌꺼기로 먹힌 경우)
            for r, (nm, goff) in greadings.items():
                if s == r or s.endswith(r) or r.endswith(s):
                    hits.append((off, s, nm, goff))
                    break
        if nxt <= off:
            break
        off = nxt

    out.write('# 특기 구역 0x%x~0x%x 의 카타카나 읽기 %d개 중\n' % (lo, hi, total))
    out.write('# 기교 테이블의 읽기와 일치 = %d개 (= 특기가 아닌데 특기로 잡힌 것)\n\n' % len(hits))
    out.write('특기구역오프셋\t읽기\t실체(기교이름)\t기교테이블위치\n')
    for off, s, nm, goff in hits:
        out.write('0x%04x\t%-14s\t%-6s\t0x%04x\n' % (off, s, nm, goff))
    out.close()


if __name__ == '__main__':
    main()
