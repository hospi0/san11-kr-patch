# -*- coding: utf-8 -*-
"""SLPM_667.01 UI 문자열 추출 — 진짜 텍스트 구역만.

★ 전수 스캔은 못 믿는다. "널종료 SJIS" 조건만 걸면 **MIPS 코드가 우연히 SJIS로
   디코딩된 것**이 대량으로 잡힌다(`胱.....挽挽s.`, `鍖.(鍖.0鍖K:鍖`, `∽$%b膕`).
   옛 census의 "4,435 문자열"은 그런 오검출이 2,132개 섞인 수였다.

진짜 UI 텍스트는 밀집 런 3곳에만 있다(gap<0x400로 뭉친 구간 + 육안 확인):
    0x443bb0 ~ 0x449c74  1,685개  메인 UI 라벨 (決定 … 話術/登場)
    0x4a07d0 ~ 0x4a1a46    415개  용어사전 표제어 + 가나 색인
    0x4a1e88 ~ 0x4a27ac    203개  무장편집/거점편집
  총 2,303개. 0x4a3334부터는 전부 쓰레기(`澤a膣`, `渓`膠`).
  ※ 용어사전 **설명문**은 SLPM에 없다(`します。`·`できます` 0회) — 아카이브 쪽이다.

예산: in-place라 한국어가 원래 자리에 들어가야 한다. 원문 길이가 아니라
**뒤따르는 널 개수**가 예산이다.
    budget = 원문바이트 + 뒤널   (종료자 1B 포함해서 써야 함)
포인터(VA = 파일오프셋 + 0xFFF00)로 참조되는 문자열은 옮길 수도 있으나
지금은 전부 in-place로 간다.

Usage: python extract_ui.py <SLPM_667.01> [out.tsv]
"""
import struct
import sys

VA_DELTA = 0xFFF00
RUNS = [(0x443bb0, 0x449c74), (0x4a07d0, 0x4a1a46), (0x4a1e88, 0x4a27ac)]


def is_lead(c):
    return 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef


def parse(d, off):
    j, s = off, []
    while j < len(d):
        c = d[j]
        if c == 0:
            break
        if is_lead(c) and j + 1 < len(d):
            try:
                s.append(d[j:j + 2].decode("cp932")); j += 2; continue
            except Exception:
                pass
        if 0x20 <= c < 0x7f:
            s.append(chr(c)); j += 1; continue
        if 0xa1 <= c <= 0xdf:
            # 반각 카타카나. 옛 추출기는 이걸 전부 "."로 치환해서 글자를 잃었다
            # (0xa5 = ･ 가운뎃점이 "."로 둔갑). cp932로 제대로 디코드한다.
            s.append(bytes([c]).decode("cp932")); j += 1; continue
        # ★제어코드 2종은 문자열의 일부다 — 버리면 안 된다(세션5 실기에서 발각).
        #   `\x1b[%dx … \x1b[0x` = 색상 지정/복귀, `\n` = 줄바꿈. 이걸 만나면 통째로
        #   None을 내던 탓에 **printf 서식 문자열 12개를 통째로 놓쳤다** — 그래서 화면엔
        #   「평원(평원) 設置：불가」처럼 리터럴 한자만 일본어로 남았다(사용자 발견).
        #   ⚠️필터를 넓히는 것이므로 이 둘만 허용한다(다른 제어바이트는 여전히 오검출 신호).
        if c == 0x1b:
            s.append("{ESC}"); j += 1; continue
        if c == 0x0a:
            s.append("{N}"); j += 1; continue
        return None
    return ("".join(s), j - off) if s else None


def ptr_table_mask(d):
    """포인터 테이블이 차지한 바이트를 True로 표시.

    ★ 진짜 텍스트 런 안에도 포인터 테이블이 섞여 있고, 그 바이트가 SJIS로
      디코딩된다. 0x4495d0의 `a0 94 54 00 a8 94 54 00 …`는 VA 0x5494a0·0x5494a8
      …(= 本体·ＰＫ·おすすめ·ステージ)를 가리키는 포인터인데, 문자열로 읽으면
      `乃`·`ｨ乃`·`ｰ乃`·`ﾀ乃`가 된다. 여기에 한글을 쓰면 포인터가 깨진다.

    4바이트 정렬 u32가 데이터 구역 VA를 가리키는 게 2개 이상 연속이면 테이블로 본다.
    """
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    lo, hi = 0x440000 + VA_DELTA, 0x4d0000 + VA_DELTA
    mask = bytearray(len(d))
    k = 0
    while k < n:
        if lo <= words[k] < hi:
            j = k
            while j < n and lo <= words[j] < hi:
                j += 1
            if j - k >= 2:
                for x in range(k * 4, j * 4):
                    mask[x] = 1
            k = j
        else:
            k += 1
    return mask


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "work/ui.tsv"
    d = open(path, "rb").read()

    n = len(d) // 4
    ptrset = {}
    for v in struct.unpack("<%dI" % n, d[:n * 4]):
        ptrset[v] = ptrset.get(v, 0) + 1
    pmask = ptr_table_mask(d)

    rows, skipped = [], 0
    for a, b in RUNS:
        i = a
        while i < b:
            if d[i] == 0:
                i += 1; continue
            if pmask[i]:
                i += 1; skipped += 1; continue
            r = parse(d, i)
            if not r:
                i += 1; continue
            s, blen = r
            if any(pmask[i:i + blen]):
                i += blen; skipped += 1; continue
            k = i + blen
            while k < len(d) and d[k] == 0:
                k += 1
            pad = k - (i + blen)
            rows.append((i, i + VA_DELTA, s, blen, pad, blen + pad,
                         ptrset.get(i + VA_DELTA, 0)))
            i += blen

    with open(out, "w", encoding="utf-8") as f:
        f.write("# off\tVA\t원문\t바이트\t뒤널\t예산\t포인터수\n")
        for off, va, s, blen, pad, bud, np_ in rows:
            f.write("0x%06x\t0x%06x\t%s\t%d\t%d\t%d\t%d\n"
                    % (off, va, s, blen, pad, bud, np_))
    print("%s 저장: %d 문자열 (포인터 테이블로 걸러낸 것 %d)" % (out, len(rows), skipped))


main()
