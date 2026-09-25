# -*- coding: utf-8 -*-
"""idx=3 (entry3.bin) 하단바 도움말·UI 프롬프트 추출.

구조: 헤더 `9b046e12` + `0000` + u32 LE 오프셋 테이블(@0x06, 오름차순).
     message[i] = d[offs[i] : offs[i+1]] (앞뒤 05 제어코드 스트립).
인코딩: 한자 전각 SJIS + 가나 반각 카타카나(기본 히라가나 렌더) +
       ESC K(1b4b)…ESC H(1b48) 구간만 카타카나 + 05 제어 + f0xx 버튼 가이지.

디코드는 읽기용으로 반각→적절한 가나로 변환해 실제 일본어를 복원한다.
"""
import struct
import sys

# 반각 카타카나(0xa1-0xdf) → 전각 카타카나
HALF2FULL = {}
_han = "｡｢｣､･ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"


def decode(b, kana="hira"):
    """b 디코드. kana='hira'면 반각카타카나→히라가나(기본렌더), ESC K구간은 카타카나."""
    import unicodedata
    out, k, mode = [], 0, "hira"
    while k < len(b):
        c = b[k]
        if c == 0x1b and k + 1 < len(b):
            mode = "kata" if b[k + 1] == 0x4b else "hira"
            k += 2; continue
        if c == 0x05:
            out.append("·"); k += 1; continue
        if 0xf0 <= c <= 0xf1 and k + 1 < len(b):
            out.append("{btn%02x}" % b[k + 1]); k += 2; continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
            if k + 1 < len(b):
                try:
                    out.append(bytes(b[k:k + 2]).decode("cp932")); k += 2; continue
                except Exception:
                    pass
        if 0xa1 <= c <= 0xdf:
            try:
                ch = bytes([c]).decode("cp932")   # 전각 카타카나(+반각→? cp932는 반각 반환)
                # 반각 → 전각 카타카나
                full = unicodedata.normalize("NFKC", ch)
                if mode == "hira" and len(full) == 1 and 0x30a1 <= ord(full) <= 0x30f6:
                    full = chr(ord(full) - 0x60)   # 카타카나→히라가나
                out.append(full); k += 1; continue
            except Exception:
                pass
        out.append(chr(c) if 0x20 <= c < 0x7f else "."); k += 1
    return "".join(out)


def parse_offsets(d):
    offs, p = [], 6
    while p + 4 <= len(d):
        v = struct.unpack("<I", d[p:p + 4])[0]
        if v < 6 or v >= len(d):
            break
        if offs and v < offs[-1]:
            break
        offs.append(v); p += 4
    return offs


def main():
    d = open("work/entry3.bin", "rb").read()
    offs = parse_offsets(d)
    offs.append(len(d))
    msgs = []
    for i in range(len(offs) - 1):
        seg = d[offs[i]:offs[i + 1]].strip(b"\x05\x00")
        if not seg:
            continue
        msgs.append((offs[i], seg))
    print("메시지 %d개, 총 %d바이트\n" % (len(msgs), sum(len(s) for _, s in msgs)))
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    for off, seg in msgs[lo:hi]:
        print("  0x%05x %3dB  %s" % (off, len(seg), decode(seg)))


if __name__ == "__main__":
    main()
