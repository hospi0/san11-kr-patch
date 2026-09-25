# -*- coding: utf-8 -*-
"""idx=3 (entry3.bin) 도움말 코퍼스 코덱 — 디코드/토큰화 단일 진실.

★세션5 정정 (옛 extract_help/dump_help_tsv는 아래 2건이 틀렸다):
  1. **0x02 = 변수 삽입코드. 길이가 파라미터에 따라 다르다.**
       param >= 0x80 → `02 XX`    (2B)
       param <  0x80 → `02 XX YY` (3B, YY는 ASCII로 보이지만 텍스트가 아니다)
     옛 코덱은 02를 1B로 봐서 파라미터가 다음 한자의 리드바이트와 합쳐져 엉뚱한 글자가 됐다.
       `02 8c | 8c6f 8cb1`(経験) → 옛: {C02} + 血('8c8c') + 'o'(6f) + 験 = "血o験"
     사용자가 mojibake 6줄(424·425·494~497·529)을 지적해 발견.
     ★근거 3중 (31곳 전수, 예외 0):
       ① part2에 남는 제어바이트가 0x0a(줄바꿈) 하나뿐으로 깔끔히 떨어진다
          (옛 파싱은 0a 44개, 그중 6개가 실은 02의 파라미터였다)
       ② param>=0x80은 항상 텍스트가 뒤따르고(番に·)·を·経験), param<0x80은 항상
          ASCII 1자('2','3','9','N')가 뒤따른다 — 파라미터값으로 완전히 갈린다
       ③ ★YY를 코드로 흡수해야 모든 메시지가 문법적 일본어가 된다:
          `02 3c 33`+の金が0に → "3の金が0に"(비문) vs "[都市名]の金が0に"(정상)
          `02 0c 32`+が覚える  → "2が覚える"(비문) vs "[武将名]が覚える"(정상)
     파라미터 의미(문맥 추정): 0a·0c=武将名 / 14·28=勢力名 / 1e=군단·세력 / 3c=都市·施設名
                              82=수치 / 83=수치(변경후) / 8c=명칭(兵種·特技·能力)
  2. **ESC k(1b 6b) = 카타카나 모드**(ESC K 0x4b와 동일). 옛 코덱은 4b만 카타카나로 보고
     나머지를 히라가나로 처리 → `ソート`(정렬)를 `そーと`라는 뜻없는 글자로 냈다(12곳).

★구조 (세션5 재규명 — 옛 기록의 "헤더 `9b046e12` 매직 + u32 테이블@0x06"은 오독이다):
      0x00  u16 LE  = 메시지 개수 (1179). 옛 기록의 `9b 04`가 이것이다.
      0x02  u32 LE × count = 오프셋 테이블(오름차순). 옛 기록의 `6e 12 00 00`은
            매직의 뒷부분이 아니라 **offs[0] = 0x126e** 이다.
      message[i] = d[offs[i] : offs[i+1]]  (마지막은 EOF까지)
  ★자기검증: offs[0] == 2 + 4*count (테이블 끝 = 메시지0 시작). 정확히 일치한다.
  ⚠️옛 파서는 테이블을 0x06에서 읽어 **메시지 0(0x126e~0x1453, 485B)을 통째로 누락**하고
    인덱스를 1씩 당겨 놨다. 텍스트 내용은 같지만(경계가 같음) 그대로 리빌드했으면
    메시지 0이 사라져 깨졌다. 평문 시작 인덱스도 415가 아니라 416이다.
인코딩: 한자 = 전각 SJIS 2B / 가나 = 반각 카타카나 1B(기본 히라가나로 렌더)
        ESC K(1b4b)·ESC k(1b6b) … ESC H(1b48) 구간만 카타카나로 렌더 = 외래어
토큰: {N}=0a 줄바꿈 · {BTNxx}=f0xx PS버튼 가이지 · {V:...}=02 변수 삽입코드(원바이트 hex)
"""
import struct
import unicodedata

from encoding import REV_ALIAS      # 가운뎃점 ・→· 등 한국어 표기 복원

PART2_START_INDEX = 416          # 0~415 = 호칭·어미 조립 테이블(번역 금지·보존)
                                 # (옛 기록의 415는 메시지0 누락으로 1 밀렸던 값)

ESC_KATA = (0x4b, 0x6b)          # ESC K / ESC k → 카타카나
ESC_HIRA = (0x48,)               # ESC H → 히라가나(기본)

# ★`01 XX` 매크로 중 **뒤 2바이트가 인수**인 것. 전 30블록 9,873메시지로 확정했다.
#   C(0x43)=어미·호칭 조립, J(0x4a)=점프라벨.  S(0x53)는 인수가 아니라 실제 식(`{V:c9}%3`)이 온다.
MACRO_ARG2 = (0x43, 0x4a)

# 반각 1B 중 NFKC로 펴면 전각 2B가 되어 **왕복이 깨지는** 것들: ｡｢｣､･ 과 장음 ｰ.
# 탁점 ﾞ(de)·반탁점 ﾟ(df)는 여기 넣지 말 것 — 앞 가나와 NFC 결합해 정상 왕복한다(が = ｶ+ﾞ).
HW_NO_ROUNDTRIP = frozenset({0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xb0})

_ARG_SAFE = None                 # {바이트: 1바이트로 되돌아가는 표시용 글자}


def _arg_repr(x):
    """매크로 인수 1바이트 → 표시 토큰. **왕복이 보장될 때만** 글자로, 아니면 생 hex."""
    global _ARG_SAFE
    if _ARG_SAFE is None:
        _ARG_SAFE = {}
        for v in range(0x100):
            if 0x20 <= v < 0x7f and v not in (0x7b, 0x7d):   # {,} 는 토큰과 헷갈린다
                ch = chr(v)
            elif 0xa1 <= v <= 0xdf:
                ch = unicodedata.normalize("NFKC", bytes([v]).decode("cp932"))
                if len(ch) == 1 and 0x30a1 <= ord(ch) <= 0x30f6:
                    ch = chr(ord(ch) - 0x60)                 # 기본 렌더는 히라가나
            else:
                continue
            try:
                if encode(ch, None) == bytes([v]):
                    _ARG_SAFE[v] = ch
            except Exception:
                pass
    return _ARG_SAFE.get(x, "{%02x}" % x)

# 관측된 02 파라미터(part2 전수 31곳). 새 값이 나오면 길이 규칙이 틀렸다는 신호 → 검토할 것.
KNOWN_V_PARAMS = {0x0a, 0x0c, 0x14, 0x1e, 0x28, 0x3c, 0x82, 0x83, 0x8c}


def var_len(param):
    """02 삽입코드의 총 길이. param>=0x80 → 2B, 아니면 3B."""
    return 2 if param >= 0x80 else 3


def parse_offsets(d):
    """[u16 count]@0x00 + [u32 offsets]@0x02 파싱. 구조 가정을 전부 어서션으로 건다."""
    n = struct.unpack("<H", d[0:2])[0]
    offs = list(struct.unpack("<%dI" % n, d[2:2 + 4 * n]))
    assert offs[0] == 2 + 4 * n, "offs[0]=0x%x != 테이블끝 0x%x" % (offs[0], 2 + 4 * n)
    assert all(offs[i] <= offs[i + 1] for i in range(n - 1)), "오프셋이 오름차순이 아니다"
    assert offs[-1] <= len(d), "오프셋이 파일 밖을 가리킨다"
    return offs


def segments(d, offs):
    """원본 세그먼트 그대로(strip 안 함) — 리빌드는 이걸 써야 바이트 동일이 된다."""
    b = offs + [len(d)]
    return [d[b[i]:b[i + 1]] for i in range(len(offs))]


def load(path="work/entry3.bin"):
    """(d, offs, msgs) 반환. msgs[i] = (index, offset, 표시용 raw_bytes(05/00 스트립))."""
    d = open(path, "rb").read()
    offs = parse_offsets(d)
    msgs = []
    for i, seg in enumerate(segments(d, offs)):
        s = seg.strip(b"\x05\x00")
        if s:
            msgs.append((i, offs[i], s))
    return d, offs, msgs


def decode(b, codec=None):
    """raw → 토큰화 문자열(사람이 읽는 일본어 + 토큰).

    codec을 주면 한글 운반체(한자 코드)를 한글로 되돌린다 — 한국어를 되읽어 검증할 때 쓴다.
    안 주면 원문 그대로(운반체는 한자로 보인다). 게임은 늘 '한자'를 그린다고 믿고 있고
    우리는 그 슬롯의 그림만 한글로 칠하므로, 바이트만 보면 한자인 게 정상이다.
    """
    out, k, mode = [], 0, "hira"
    while k < len(b):
        c = b[k]
        if c == 0x1b and k + 1 < len(b):
            n = b[k + 1]
            if n in ESC_KATA:
                mode = "kata"
            elif n in ESC_HIRA:
                mode = "hira"
            else:
                out.append("{ESC%02x}" % n)
            k += 2
            continue
        if c == 0x01 and k + 1 < len(b) and b[k + 1] in MACRO_ARG2:
            # ★★`01 43`(C=어미조립) / `01 4a`(J=점프라벨) 뒤의 **2바이트는 인수**다 — 텍스트가 아니다.
            #   이걸 텍스트로 디코드하면 조용히 깨진다(세션26에 실기 「미번역」 7종의 진범으로 확정):
            #     01 43 b0 00 → b0(반각 ｰ)을 장음 ー로 읽어 인코드하면 전각 2B 81 5b = 바이트 불일치
            #     01 43 de .. → 반각 탁점 ﾞ(U+3099) → encode에서 KeyError
            #     01 4a 02 10 → 02를 변수코드로 착각해 {V:1005}로 삼킴
            #   → 추출기의 라운드트립 게이트가 그 152줄을 통째로 버렸고, 그래서 번역될 기회조차 없었다.
            #   ⚠️인수는 **1바이트 왕복이 보장되는 값만** 사람이 읽는 글자로 두고, 나머지는 생 hex로 낸다.
            #     (`{01}Cし{00}` 같은 기존 TSV 표기를 그대로 유지하기 위한 것 — 형식이 바뀌면
            #      build_e4의 되읽기 검증이 기존 번역 수천 줄을 전부 되돌려버린다.)
            out.append("{01}" + chr(b[k + 1]))
            k += 2
            for _ in range(2):
                if k >= len(b):                   # split_pad가 종료바이트까지 떼어간 초단문
                    break
                out.append(_arg_repr(b[k]))
                k += 1
            continue
        if c == 0x02 and k + 1 < len(b):          # ★ 변수 삽입코드(길이는 파라미터가 결정)
            n = var_len(b[k + 1])
            out.append("{V:%s}" % bytes(b[k + 1:k + n]).hex())
            k += n
            continue
        if c == 0x0a:
            out.append("{N}")
            k += 1
            continue
        if 0xf0 <= c <= 0xf1 and k + 1 < len(b):  # PS 버튼 가이지
            out.append("{BTN%02x}" % b[k + 1])
            k += 2
            continue
        if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef) and k + 1 < len(b):
            if codec is not None:
                code = struct.unpack(">H", bytes(b[k:k + 2]))[0]
                if code in codec.dec:                 # 한자 운반체 → 한글
                    out.append(codec.dec[code])
                    k += 2
                    continue
            try:
                ch = bytes(b[k:k + 2]).decode("cp932")
                out.append(REV_ALIAS.get(ch, ch) if codec is not None else ch)
                k += 2
                continue
            except Exception:
                pass
        if 0xa1 <= c <= 0xdf:                     # 반각 카타카나 1B
            if c in HW_NO_ROUNDTRIP:
                # ★1바이트로 되돌아가지 않는 반각(구두점 ｡｢｣､･ · 장음 ｰ)은 생 hex로.
                #   NFKC로 펴면 전각 2B가 되어 조용히 바이트가 늘어난다.
                #   ⚠️탁점 ﾞﾟ(de/df)는 **제외** — 앞 가나와 NFC로 합쳐져 정상 왕복한다(が=ｶ+ﾞ).
                out.append("{%02x}" % c)
                k += 1
                continue
            ch = unicodedata.normalize("NFKC", bytes([c]).decode("cp932"))
            if mode == "hira" and len(ch) == 1 and 0x30a1 <= ord(ch) <= 0x30f6:
                ch = chr(ord(ch) - 0x60)          # 카타카나 → 히라가나(기본 렌더)
            out.append(ch)
            k += 1
            continue
        out.append(chr(c) if 0x20 <= c < 0x7f else "{%02x}" % c)
        k += 1
    return "".join(out)


# ── 인코더 ──────────────────────────────────────────────────────────────────
# 반각 카타카나 1B(0xa1-0xdf) ↔ 전각 카타카나/기호. 탁점은 별도 1B(ﾞ=0xde, ﾟ=0xdf)라
# 「が」는 ｶ+ﾞ = 2B가 된다 → NFD로 분해해서 조각마다 매핑한다.
# ★반각 1B로 쓰는 건 가나(ｱ-ﾝ·ｦ·소문자)와 탁점·반탁점뿐이다. 구두점(｡｢｣､･)은 part2에서
#   0회 = 「」、。・는 항상 전각 2B다. 장음 ー도 전각(81 5b) 56회가 정본이고, 반각 ｰ(b0)은
#   12회뿐인데 전부 ESC k(=12회) 구간, 즉 버튼바 「ソート」 전용 변종이다 → 기본은 전각.
_HW = {}
for _b in range(0xa1, 0xe0):
    _ch = unicodedata.normalize("NFKC", bytes([_b]).decode("cp932"))
    if 0x30a1 <= ord(_ch) <= 0x30f6 or ord(_ch) in (0x3099, 0x309a):
        _HW[_ch] = _b

TOKEN_RE = None                  # 지연 컴파일(re import 최소화)


def _kana_bytes(ch):
    """가나 1자 → (반각 바이트열, 필요한 렌더 모드). 가나가 아니면 None.

    탁점은 별도 1B라 「が」= ｶ+ﾞ 2B → NFD로 분해해 조각마다 매핑한다.
    """
    o = ord(ch)
    if 0x30a1 <= o <= 0x30f6:
        need = "kata"
    elif 0x3041 <= o <= 0x3096:
        need = "hira"
    else:
        return None                             # ー(30fc)·구두점은 전각 2B 경로로
    out = bytearray()
    for p in unicodedata.normalize("NFD", ch):
        if 0x3041 <= ord(p) <= 0x3096:          # 히라가나 → 카타카나(반각은 카타카나뿐)
            p = chr(ord(p) + 0x60)
        if p not in _HW:
            return None
        out.append(_HW[p])
    return bytes(out), need


def encode(text, codec, mode0="hira", jp_passthrough=False):
    """토큰화 텍스트 → idx=3 바이트.

    한글 = 2B 한자 운반체(codec) · ASCII = 1B 반각 · 가나 = 반각 1B + ESC 모드스위치 ·
    {V:hex} = 02+파라미터 · {N} = 0a · {BTNxx} = f0 xx.
    ★한국어 번역문엔 가나가 없으므로 ESC는 아예 안 나온다(ESC는 반각 카타카나의
      렌더 모드만 바꾸므로 생략해도 무해 — 원문도 ESC 구간을 반각 가나에만 딱 붙여 쓴다).
    ★한자는 매핑이 없어 KeyError가 난다 = 한국어 번역문에 한자가 남으면 잡아내는 안전망
      (한자 코드는 한글 운반체로 쓰이므로 '자기 자신'으로 인코딩될 수 없다).
      jp_passthrough=True면 cp932 원바이트로 통과 — **라운드트립 검증 전용**이다.
    """
    global TOKEN_RE
    if TOKEN_RE is None:
        import re
        # ★생 제어바이트 {xx}와 {ESCxx}도 반드시 넣어야 한다 — decode가 이 둘을 뱉는데
        #   여기 없으면 리터럴 ASCII "{05}"(7b 30 35 7d)로 나가 문자열이 조용히 망가진다.
        #   idx=3가 이 버그를 안 밟은 건 build_help.split_pad가 앞뒤 05/00을 먼저 떼어냈고
        #   번역 구역엔 중간 제어코드가 없었던 덕(=운). entry4엔 {01}{04}{05}가 문장 중간에 널렸다.
        #   대소문자로 구분된다: BTN/ESC는 대문자, 생바이트는 %02x 소문자.
        TOKEN_RE = re.compile(
            r"\{(?:V:[0-9a-f]{2,6}|N|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")

    out, mode, pos = bytearray(), mode0, 0
    text = unicodedata.normalize("NFC", text)

    def close():
        """카타카나 런이 끝나면 즉시 ESC H로 닫는다 — 원문이 그렇게 쓴다:
        `ESC K デ ESC H ー ESC K タ ESC H を`(전각 ー조차 구간 밖으로 밀어낸다)."""
        nonlocal mode
        if mode != "hira":
            out.extend(b"\x1bH")
            mode = "hira"

    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if m:
            close()
            t = m.group(0)[1:-1]
            if t == "N":
                out += b"\x0a"
            elif t.startswith("V:"):
                out += b"\x02" + bytes.fromhex(t[2:])
            elif t.startswith("BTN"):
                out += bytes([0xf0, int(t[3:], 16)])
            elif t.startswith("ESC"):
                out += bytes([0x1b, int(t[3:], 16)])
            else:
                out += bytes([int(t, 16)])          # 생 제어바이트 {05} 등
            pos = m.end()
            continue
        ch = text[pos]
        pos += 1
        kb = _kana_bytes(ch)
        if kb is not None:
            b, need = kb
            if need != mode:                            # ESC 모드 스위치
                out += b"\x1b" + (b"K" if need == "kata" else b"H")
                mode = need
            out += b
            continue
        close()                                         # 가나가 아니면 먼저 구간을 닫는다
        if ch == " ":
            out += b"\x20"
            continue
        if 0x21 <= ord(ch) <= 0x7e:                     # 반각 ASCII 1B
            out += bytes([ord(ch)])
            continue
        code = codec.code_for(ch) if codec else None     # 한글 → 한자 운반체 / 기호 보존
        if code is None and jp_passthrough:
            try:
                out += ch.encode("cp932")
                continue
            except Exception:
                pass
        if code is None:
            raise KeyError("no mapping for %r (U+%04X)" % (ch, ord(ch)))
        out += struct.pack(">H", code)
    return bytes(out)
