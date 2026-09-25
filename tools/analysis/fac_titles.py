# -*- coding: utf-8 -*-
"""관직(官職) 테이블 stride 46 검증 + 전수 추출.

征東将軍(0x45aa)을 앵커로 stride 0x2e로 앞뒤로 걸어가며 각 슬롯의
이름·읽기를 뽑는다. 이름이 깨지는 지점 = 테이블 경계.
관직 테이블이 두 벌(A/B)로 보이므로 각각 확인한다.
"""
import sys

d = open("work/entry5.bin", "rb").read()


def field_str(i):
    """i에서 SJIS 런(첫 0x00 전까지). 가이지 포함."""
    out, j = [], i
    while j < len(d) - 1:
        hi, lo = d[j], d[j + 1]
        if hi == 0:
            break
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); j += 2; continue
        try:
            ch = bytes([hi, lo]).decode("cp932")
            if len(ch) != 1:
                out.append("?"); j += 1; continue
            out.append(ch); j += 2
        except Exception:
            out.append("."); j += 1
    return "".join(out), j - i


def walk(anchor, stride, lo_lim, hi_lim):
    """anchor에서 stride 간격으로 양방향. 각 슬롯 [name\\0 ... reading]."""
    slots = {}
    # 앞으로
    off = anchor
    while lo_lim <= off < hi_lim:
        nm, nb = field_str(off)
        slots[off] = (nm, nb)
        off += stride
    # 뒤로
    off = anchor - stride
    while lo_lim <= off < hi_lim:
        nm, nb = field_str(off)
        slots[off] = (nm, nb)
        off -= stride
    return slots


def dump_record(off, stride):
    """레코드 전체를 필드 추정으로 쪼갠다: 이름\\0 [바이너리] 읽기\\0 [바이너리]."""
    rec = d[off:off + stride]
    return " ".join("%02x" % x for x in rec)


def main():
    anchor = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x45aa
    stride = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x2e
    slots = walk(anchor, stride, 0x2000, 0x5800)
    print("anchor 0x%04x stride 0x%02x(%d) — %d 슬롯\n" % (anchor, stride, stride, len(slots)))
    for off in sorted(slots):
        nm, nb = slots[off]
        # 이름 뒤 읽기 찾기: name\0 다음부터 첫 카타카나
        rp = off + nb + 1
        rd, _ = field_str(rp) if rp < len(d) else ("", 0)
        flag = "" if (nb and all(('一' <= c <= '鿿') or c.startswith('[') or c in '？' for c in nm.replace('[','').replace(']',''))) else "  ??"
        print("  0x%04x  %-12s (%dB)%s" % (off, nm[:12], nb, flag))


main()
