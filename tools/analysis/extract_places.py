# -*- coding: utf-8 -*-
"""도시·관·항 테이블 재추출 (고정 stride, 전진 파싱).

옛 work/cities.txt는 못 쓴다. 카타카나 읽기를 찾은 뒤 **뒤로** 걸어가며 SJIS를
욕심껏 주워담아서, 앞 레코드의 바이너리 꼬리가 우연히 SJIS로 디코딩되면 그대로
이름에 붙었다(李高唐港·東胡官渡港·養由基の綿竹関·兵法書虎林港·塔陸口港).
게다가 1글자 도시(薊·鄴·宛·呉)를 통째로 놓쳤다.

레코드는 고정 stride이고 이름은 레코드 맨 앞의 고정폭 필드다. **전진** 파싱하면
경계가 모호할 여지가 없다.

    都市  base 0x005a  stride 25(0x19)  이름 [0:5]  읽기 @5   42개
    関    base 0x0474  stride 26(0x1a)  이름 [0:7]  읽기 @7   10개
    港    base 0x0578  stride 26(0x1a)  이름 [0:7]  읽기 @7   35개
    州    base 0x0906  stride 44(0x2c)  이름 [0:5]  읽기 @5   12개
    地方  base 0x0b16  stride 18(0x12)  이름 [0:5]  읽기 @5    6개

교차검증:
  · 옛 추출의 0x32 간격 = 정확히 stride 2배 = 누락 1건. 계산한 누락 위치
    0x1ea에 실제로 宛이 있고, 0x55e에 綿竹関이 있다.
  · 都市 42개 = 삼국지11 도시 수, 関 10개(壺関 포함) = 관 수와 일치.
  · 테이블 경계가 서로 정확히 맞물린다: 0x5a+25*42 = 0x474(관 시작),
    0x474+26*10 = 0x578(항 시작), 0x578+26*35 = 0x906(주 시작),
    0x906+44*12 = 0xb16(지방 시작), 0xb16+18*6 = 0xb82(그 다음 테이블).
  · 都市 42 = 삼국지11 도시 수, 関 10(壺関 포함) = 관 수와 일치.

⚠️ 州 레코드(44B)는 이름·읽기 뒤에 소속 州 목록 같은 문자열을 더 품는다
   (青徐 안에 青州徐州가 2번, 兗予 안에 兗州予州·司隷). 널종료가 아니고
   오프셋도 가변이라 여기선 건드리지 않는다 — 이름 필드 [0:5]만 다룬다.
   그 문자열들이 화면에 뜨는지는 미확인(뜬다면 별도 과제).

사용: python tools/analysis/extract_places.py work/entry5.bin work/places.tsv
"""
import sys

# (라벨, base, stride, 이름필드폭, 개수)
TABLES = [
    ("都市", 0x005a, 25, 5, 42),
    ("関",   0x0474, 26, 7, 10),
    ("港",   0x0578, 26, 7, 35),
    ("州",   0x0906, 44, 5, 12),
    ("地方", 0x0b16, 18, 5, 6),
]


def decode_name(b):
    """이름 필드: 첫 0x00까지 SJIS 2바이트 + 가이지."""
    out, i = [], 0
    while i < len(b) - 1:
        if b[i] == 0:
            break
        hi, lo = b[i], b[i + 1]
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo)); i += 2; continue
        try:
            out.append(bytes([hi, lo]).decode("cp932")); i += 2
        except Exception:
            return None, i
    return "".join(out), i


def read_str(b, start):
    j = start
    while j < len(b) and b[j] != 0:
        j += 1
    try:
        return b[start:j].decode("cp932")
    except Exception:
        return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "work/entry5.bin"
    dst = sys.argv[2] if len(sys.argv) > 2 else "work/places.tsv"
    d = open(src, "rb").read()

    rows, warn = [], []
    for label, base, stride, nw, count in TABLES:
        for k in range(count):
            off = base + k * stride
            rec = d[off:off + stride]
            name, nlen = decode_name(rec[:nw])
            yomi = read_str(rec, nw)
            note = ""
            if not name:
                note = "이름 파싱 실패"
            elif not yomi:
                note = "읽기 없음"
            elif not all(0x30a0 <= ord(c) <= 0x30ff for c in yomi):
                note = "읽기 비카타카나: %r" % yomi
            if note:
                warn.append((label, "0x%04x" % off, name, yomi, note))
            rows.append((label, "0x%04x" % off, str(nw), name or "", yomi or "", note))
        print("%-4s base 0x%04x stride %2d 이름폭 %d -> %d 레코드 (끝 0x%04x)"
              % (label, base, stride, nw, count, base + count * stride))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("# 종류\toffset\t이름필드폭\t원문\t読み\t비고\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print("\n%s 저장: %d개, 경고 %d건" % (dst, len(rows), len(warn)))
    for w in warn:
        print("   ", w)


main()
