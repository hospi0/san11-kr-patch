# -*- coding: utf-8 -*-
"""idx=3 평문 구간(index 415~) 번역용 TSV 생성.

특수코드를 토큰으로 표시해 번역자가 보존하기 쉽게:
  {N}    = 0x0a 줄바꿈
  {BTNxx}= 0xf0xx PS 버튼 가이지 아이콘
  {C02}  = 0x02 삽입/제어 코드
  ···    = 05 05 05 메시지 구분(같은 오프셋 블록 안 다중 메시지) — 실제로는 각 행이 1메시지
외래어(ESC K…H 구간)는 카타카나 그대로 표시 → 번역 시 한글로 쓰면 됨(ESC는 빌더가 처리).
조립코드(0x04/0b/0c ESC M/K) 포함 메시지는 [ASM] 표시하고 번역 제외.
"""
import struct

d = open("work/entry3.bin", "rb").read()
offs = []
p = 6
while p + 4 <= len(d):
    v = struct.unpack("<I", d[p:p + 4])[0]
    if v < 6 or v >= len(d) or (offs and v < offs[-1]):
        break
    offs.append(v); p += 4
offs.append(len(d))


def tok(b):
    import unicodedata
    out, k, asm, mode = [], 0, False, "hira"
    while k < len(b):
        c = b[k]
        if c == 0x1b and k + 1 < len(b):
            mode = "kata" if b[k + 1] == 0x4b else "hira"   # ESC K=카타카나, ESC H=히라가나
            k += 2; continue
        if c == 0x0a:
            out.append("{N}"); k += 1; continue
        if c == 0x05:
            out.append("·"); k += 1; continue
        if 0xf0 <= c <= 0xf1 and k + 1 < len(b):
            out.append("{BTN%02x}" % b[k + 1]); k += 2; continue
        if c == 0x02:
            out.append("{C02}"); k += 1; continue
        if c in (0x04, 0x0b, 0x0c):
            asm = True; out.append("{ASM%02x}" % c); k += 1; continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
            try:
                out.append(bytes(b[k:k + 2]).decode("cp932")); k += 2; continue
            except Exception:
                pass
        if 0xa1 <= c <= 0xdf:
            ch = unicodedata.normalize("NFKC", bytes([c]).decode("cp932"))
            # 기본 렌더 = 히라가나. ESC K 구간(외래어)만 카타카나 유지.
            if mode == "hira" and len(ch) == 1 and 0x30a1 <= ord(ch) <= 0x30f6:
                ch = chr(ord(ch) - 0x60)
            out.append(ch); k += 1; continue
        out.append(chr(c) if 0x20 <= c < 0x7f else "{%02x}" % c); k += 1
    return "".join(out), asm


def main():
    with open("work/help_jp.tsv", "w", encoding="utf-8") as f:
        f.write("# idx=3 평문 도움말 번역용. jp열을 한글로 번역, {BTN}·{N}·{C02} 토큰은 그대로 두기.\n")
        f.write("# 외래어(カタカナ)는 한글로 쓰면 됨. kr열 비워두면 미번역.\n")
        f.write("index\toffset\tbytes\tjp\tkr\n")
        cnt = 0
        for i in range(415, len(offs) - 1):
            seg = d[offs[i]:offs[i + 1]].strip(b"\x05\x00")
            if not seg:
                continue
            s, asm = tok(seg)
            if asm:
                continue                            # 조립코드 메시지 제외
            f.write("%d\t0x%05x\t%d\t%s\t\n" % (i, offs[i], len(seg), s))
            cnt += 1
    print("work/help_jp.tsv 저장: %d개 평문 메시지" % cnt)


main()
