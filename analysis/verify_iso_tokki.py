"""빌드된 ISO를 새로 파싱해 특기·기교·능력을 되읽기 검증한다.

빌더 자체검사가 아니라 **ISO를 독립적으로 다시 읽는다**. 세션5에서 이 방식으로
"내 데이터엔 이상 없음"과 "실제로 들어갔음"이 다르다는 걸 여러 번 확인했다.

검사:
  1. 이름 100/36/66이 전부 한글로 되읽히나
  2. 설명이 전부 한글로 되읽히나 (TSV와 문자열 일치)
  3. ★**옆 필드가 안 깨졌나** — 이게 진짜 위험이다:
     기교 +0x53 행번호(0~8이 4번씩) · +0x54 레벨(0~3이 9번씩) · +0x55 금 · +0x57 기교P
     특기 +0x5b 플래그 · 능력 +0x40 플래그
     설명이 필드를 넘치면 여기가 0으로 덮인다.
"""
import io
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from encoding import Codec   # noqa: E402

ISO = "C:/claude/roms/ps2/San11_kr.iso"
S11_SRC = r"C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan)/s11pkres.bin"
S11_OFF, ELF_OFF, ENTRY5, E5SIZE = 0x73e000, 0x105800, 0x1e9800, 0xbab8

SPEC = {
    '특기': (0x5210, 0x5d, 100, 0x00, 0x18),
    '기교': (0x7664, 0x5c, 36, 0x00, 0x2a),
    # 능력 98 = 특기노드 71 + 능력치 15 + 병과적성 12. 0x9e64 + 98*0x4a = 0xbab8 = 파일 끝.
    '능력': (0x9e64, 0x4a, 98, 0x00, 0x09),
}


def dec(codec, buf, off, cap):
    end = buf.find(b'\x00', off, off + cap + 1)
    if end < 0:
        end = off + cap
    out = []
    i = off
    while i < end:
        b = buf[i]
        if b < 0x80:
            out.append(chr(b)); i += 1
        else:
            code = (b << 8) | buf[i + 1]
            out.append(codec.dec.get(code) or bytes([b, buf[i + 1]]).decode('cp932', 'replace'))
            i += 2
    return ''.join(out)


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    r = open(ISO, 'rb')
    r.seek(ELF_OFF); elf = r.read(5242752)
    tmp = os.path.join(HERE, '_e.tmp'); open(tmp, 'wb').write(elf)
    codec = Codec(tmp); os.remove(tmp)
    r.seek(S11_OFF + ENTRY5); e5 = r.read(E5SIZE)
    r.close()
    e5_orig = open(S11_SRC, 'rb').read()[ENTRY5:ENTRY5 + E5SIZE]

    want = {}
    for ln in io.open(os.path.join(HERE, '..', 'work', 'tokki_kr.tsv'), encoding='utf-8'):
        f = ln.rstrip('\n').split('\t')
        if len(f) < 9 or f[0] == 'table' or ln.startswith('#'):
            continue
        want[(f[0], int(f[2], 16))] = (f[4], f[8])

    bad = 0
    for tbl, (base, stride, cnt, n_off, d_off) in SPEC.items():
        mism = 0
        for i in range(cnt):
            off = base + i * stride
            kn, kd = want[(tbl, off)]
            gn = dec(codec, e5, off + n_off, 8)
            gd = dec(codec, e5, off + d_off, 66)
            # 가운뎃점: 한국어 '·'(U+00B7)는 폰트에 없어 '・'(U+30FB)로 인코딩된다
            # (encoding.PUNCT_ALIAS — 의도된 별칭). 되읽으면 '・'로 나오니 정규화해서 본다.
            gn, gd = gn.replace('・', '·'), gd.replace('・', '·')
            if gn != kn or gd != kd:
                mism += 1
                out.write('❌ %s idx%d 0x%04x\n   이름 기대%r 실제%r\n   설명 기대%r 실제%r\n'
                          % (tbl, i, off, kn, gn, kd, gd))
        out.write('%s: %d개, 되읽기 불일치 %d\n' % (tbl, cnt, mism))
        bad += mism

    # ---- 옆 필드 무결성 ----
    out.write('\n===== 옆 필드 무결성 (설명이 넘쳤으면 여기가 깨진다) =====\n')

    def col(base, stride, cnt, c, src):
        return [src[base + i * stride + c] for i in range(cnt)]

    b, s, c = SPEC['기교'][:3]
    row = col(b, s, c, 0x53, e5)
    lvl = col(b, s, c, 0x54, e5)
    ok_row = row == col(b, s, c, 0x53, e5_orig)
    ok_lvl = lvl == col(b, s, c, 0x54, e5_orig)
    out.write('기교 +0x53 행번호 : %s  (분포 %s)\n'
              % ('✅ 원본과 동일' if ok_row else '❌ 깨짐', sorted(Counter(row).items())))
    out.write('기교 +0x54 레벨   : %s  (분포 %s)\n'
              % ('✅ 원본과 동일' if ok_lvl else '❌ 깨짐', sorted(Counter(lvl).items())))
    gold = [struct.unpack('<H', e5[b + i * s + 0x55: b + i * s + 0x57])[0] for i in range(c)]
    pts = [struct.unpack('<H', e5[b + i * s + 0x57: b + i * s + 0x59])[0] for i in range(c)]
    out.write('기교 +0x55 금     : %s  (고유 %s)\n'
              % ('✅' if sorted(set(gold)) == [1000, 2000, 5000, 10000] else '❌', sorted(set(gold))))
    out.write('기교 +0x57 기교P  : %s  (고유 %s)\n'
              % ('✅' if sorted(set(pts)) == [1000, 2000, 3000, 5000] else '❌', sorted(set(pts))))
    bad += (not ok_row) + (not ok_lvl)

    for tbl, c_off in (('특기', 0x5b), ('능력', 0x40)):
        b, s, n = SPEC[tbl][:3]
        same = col(b, s, n, c_off, e5) == col(b, s, n, c_off, e5_orig)
        out.write('%s +0x%02x 플래그 : %s\n' % (tbl, c_off, '✅ 원본과 동일' if same else '❌ 깨짐'))
        bad += (not same)

    # 읽기(카타카나) 필드가 안 밟혔나 — 이름이 늘어나면 여기를 침범한다
    for tbl, r_off in (('특기', 0x05), ('기교', 0x09)):
        b, s, n = SPEC[tbl][:3]
        same = col(b, s, n, r_off, e5) == col(b, s, n, r_off, e5_orig)
        out.write('%s +0x%02x 읽기 첫바이트 : %s\n'
                  % (tbl, r_off, '✅ 원본과 동일(0x83)' if same else '❌ 이름이 읽기를 침범'))
        bad += (not same)

    out.write('\n%s\n' % ('✅✅ ISO 되읽기 전부 통과' if bad == 0 else '❌ 문제 %d건' % bad))
    out.close()


if __name__ == '__main__':
    main()
