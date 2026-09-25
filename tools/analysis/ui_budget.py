# -*- coding: utf-8 -*-
"""UI 문자열의 **실제 예산**을 잰다. 번역 가능 여부를 가르는 유일한 숫자.

in-place 편집이면 한국어가 원래 자리에 들어가야 한다. 그래서 원문 길이가 아니라
**뒤따르는 널 패딩이 얼마나 되는가**가 예산이다. 그리고 포인터로 참조되는
문자열이면 여유 공간으로 옮기고 포인터만 고치면 되므로 예산 제약이 사라진다.

  budget = 원문 바이트 + 뒤따르는 널 개수   (종료자 1B 포함해서 써야 함)
  ptr    = 그 문자열의 VA(파일오프셋+0xFFF00)를 가리키는 u32가 ELF에 있는가

Usage: python ui_budget.py <SLPM_667.01> [out.tsv]
"""
import struct
import sys
from collections import Counter

VA_DELTA = 0xFFF00


def is_lead(c):
    return 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef


def parse(d, off):
    """off부터 널까지. (문자열, 바이트길이, 일본어글자수) 또는 None."""
    j, s, jp = off, [], 0
    while j < len(d):
        c = d[j]
        if c == 0:
            break
        if is_lead(c) and j + 1 < len(d):
            try:
                s.append(d[j:j + 2].decode("cp932")); jp += 1; j += 2; continue
            except Exception:
                pass
        if 0x20 <= c < 0x7f or 0xa1 <= c <= 0xdf:
            s.append(chr(c) if c < 0x7f else "."); j += 1; continue
        return None
    return ("".join(s), j - off, jp) if s else None


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "work/ui_budget.tsv"
    d = open(path, "rb").read()

    # ELF 안 모든 4바이트정렬 u32 → 포인터 후보 집합
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    ptrset = Counter(words)

    strings = []
    i = 0
    while i < len(d) - 2:
        if is_lead(d[i]):
            r = parse(d, i)
            if r and r[2] >= 2 and r[1] >= 4:
                s, blen, jp = r
                # 뒤따르는 널 개수
                k = i + blen
                while k < len(d) and d[k] == 0:
                    k += 1
                pad = k - (i + blen)
                va = i + VA_DELTA
                strings.append((i, va, s, blen, jp, pad, ptrset.get(va, 0)))
                i += blen
                continue
        i += 1

    with open(out, "w", encoding="utf-8") as f:
        f.write("# off\tVA\t원문\t바이트\t일본어자\t뒤널\t예산\t포인터수\n")
        for off, va, s, blen, jp, pad, np_ in strings:
            f.write("0x%06x\t0x%06x\t%s\t%d\t%d\t%d\t%d\t%d\n"
                    % (off, va, s, blen, jp, pad, blen + pad, np_))

    print("%s 저장: %d 문자열" % (out, len(strings)))
    print()
    withp = [x for x in strings if x[6] > 0]
    print("포인터로 참조되는 문자열: %d / %d (%.1f%%)"
          % (len(withp), len(strings), 100.0 * len(withp) / len(strings)))
    print()
    # 예산 분포: 한국어는 보통 원문 일본어보다 짧거나 비슷하다.
    # 한글 1음절 = 2B. 원문 일본어 글자수만큼 한글이 필요하다고 보면 필요치 = jp*2 + 1
    tight = [x for x in strings if x[3] + x[5] < x[4] * 2 + 1]
    print("예산 < (원문 일본어 글자수 x 2 + 1) 인 문자열: %d (%.1f%%)"
          % (len(tight), 100.0 * len(tight) / len(strings)))
    print()
    print("=== 예산 여유 분포 (예산 - 원문바이트) ===")
    h = Counter()
    for off, va, s, blen, jp, pad, np_ in strings:
        h[min(pad, 20)] += 1
    for k in sorted(h):
        print("  뒤널 %2d%s : %5d" % (k, "+" if k == 20 else " ", h[k]))


main()
