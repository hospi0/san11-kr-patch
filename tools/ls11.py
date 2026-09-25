"""LS11 컨테이너 코덱 (entry4 = 환경설정 도움말).

알고리즘 출처: tzengyuxio/kaodata `dekoei/ls11.py` (2026-07-17 세션8, 사용자 제보).
여기선 의존성 없이 재구현하고 **오라클로 검증**한다.

★★**허프만이 아니다.** 구조는 「보편부호(Elias-gamma 변형) + LZ77」이다:

  코드 읽기 = 1비트씩 읽어 **0이 나올 때까지 센다**(len). 그 다음 len 비트를 MSB-first로 읽어 factor.
              code = (1<<len) - 2 + factor
      len=1 -> code 0..1     len=2 -> 2..5      len=3 -> 6..13
      len=4 -> 14..29        len=5 -> 30..61    len=6 -> 62..125 ...

  코드 해석:
      code < 256   -> **리터럴** = dictionary[code]      ← 0x10의 256B 순열이 바로 이 사전
      code >= 256  -> **매치 거리** delta = code - 256, 그리고 **다음 코드**가 길이 = 3 + code
  (매치는 코드 2개로 표현된다. 그래서 리터럴 8비트 고정이라는 내 LZSS 가정이 안 맞았다.)

사전이 **빈도순**이라 자주 쓰는 바이트가 작은 code → 짧은 부호가 된다. 이 엔트로피 코딩 +
LZ 매치가 합쳐져 order-0 엔트로피(6.71)보다 낮은 4.54 bit/symbol이 나온다.

컨테이너:
  0x000 "LS11"(또는 "Ls12") + 0패딩 12B
  0x010 256B 사전
  0x110 (압축크기, 원본크기, 오프셋) × N, 전부 **u32 빅엔디안**, `00000000` 4바이트로 종료
  그 뒤 블록 데이터
★**블록별 무압축 통과가 있다**: `압축크기 == 원본크기`면 그 블록은 그대로 복사된다(전역 플래그 아님).
"""
import struct

MAGIC = (b'LS11', b'Ls12')


def _bits(data):
    for byte in data:
        for k in range(7, -1, -1):
            yield (byte >> k) & 1


def get_codes(data):
    """비트스트림 -> 코드 리스트."""
    out = []
    it = _bits(data)
    while True:
        n = 0
        for bit in it:                       # 0이 나올 때까지 1을 센다
            n += 1
            if not bit:
                break
        else:
            break                            # 스트림 끝
        factor, got = 0, 0
        for bit in it:
            factor = (factor << 1) | bit
            got += 1
            if got == n:
                break
        if got < n:
            break
        out.append((1 << n) - 2 + factor)
    return out


def recover(codes, dictionary):
    """코드 -> 원본 바이트."""
    out = bytearray()
    delta = 0
    for code in codes:
        if delta > 0:
            for _ in range(3 + code):
                out.append(out[len(out) - delta])
            delta = 0
        elif code < 256:
            out.append(dictionary[code])
        else:
            delta = code - 256
    return bytes(out)


def parse_blocks(data):
    """[(압축크기, 원본크기, 오프셋)] 반환."""
    if data[:4] not in MAGIC:
        raise ValueError('LS11 매직 아님: %r' % data[:4])
    pos, infos = 16 + 256, []
    while data[pos:pos + 4] != b'\x00\x00\x00\x00':
        infos.append(struct.unpack('>III', data[pos:pos + 12]))
        pos += 12
    return infos


def decode_block(data, index):
    dic = data[16:16 + 256]
    comp, orig, off = parse_blocks(data)[index]
    raw = data[off:off + comp]
    if comp == orig:                          # ★블록별 무압축 통과
        return raw
    return recover(get_codes(raw), dic)[:orig]


def decode_all(data):
    return [decode_block(data, i) for i in range(len(parse_blocks(data)))]


# ── 인코더 ────────────────────────────────────────────────────────────────────
# 코드 c의 버킷 n = (c+2).bit_length()-1  (디코더의 code=(1<<n)-2+factor 를 뒤집은 것).
# 출력 = (n-1)개의 1 + 0 + factor n비트(MSB-first)  =>  **비용은 항상 2n 비트**.
#   n=1: code 0..1     (2비트)   n=2: 2..5    (4비트)   n=3: 6..13   (6비트)
#   n=4: 14..29        (8비트)   n=5: 30..61 (10비트)   ...   n=8: 254..509 (16비트)
# 리터럴 = 사전 순위(rank)라 **흔한 바이트일수록 싸다**(rank 0~1은 2비트).
# 매치 = 코드 2개 (256+delta, len-3) 라 거리가 조금만 멀어도 16+ 비트로 비싸다
#   -> 짧은 매치는 리터럴보다 손해일 수 있어서 **비용 비교로 판단**해야 한다.

def _n_of(code):
    return (code + 2).bit_length() - 1


def _cost(code):
    return 2 * _n_of(code)


class _BW:
    def __init__(s):
        s.buf = bytearray()
        s.acc = 0
        s.nb = 0

    def put(s, bit):
        s.acc = (s.acc << 1) | bit
        s.nb += 1
        if s.nb == 8:
            s.buf.append(s.acc)
            s.acc, s.nb = 0, 0

    def code(s, c):
        n = _n_of(c)
        for _ in range(n - 1):
            s.put(1)
        s.put(0)
        f = c - ((1 << n) - 2)
        for k in range(n - 1, -1, -1):
            s.put((f >> k) & 1)

    def done(s):
        while s.nb:                      # 0으로 패딩 -> 잉여 코드는 리터럴이라 무해
            s.put(0)                     # (어차피 [:orig]로 잘려나간다)
        return bytes(s.buf)


# ★★안전 상한 = **원본(코에이 인코더)이 실제로 쓰는 범위**를 30블록 전수 측정해서 정했다.
#   거리 1..8191 (= 2^13-1 → 게임 디코더의 링버퍼가 **8KB**일 것) · 길이 3..512.
#   ⚠️이걸 안 걸면 내 인코더는 거리 70,235 · 길이 1,801까지 뿜는다. 우리 디코더는 받아주지만
#   **게임 디코더는 링버퍼를 넘겨 조용히 깨진다.** 실기에서 원인 찾기 지옥이 될 종류의 버그다.
#   [[feedback_kr_patch_verification]] "안전선 = 통과가 확인된 최대값".
MIN_MATCH = 3
MAX_DELTA = 8191
MAX_MATCH = 512


def _find_best(raw, i, n, heads, lit_cost, max_chain):
    """위치 i의 최적 매치 (gain, len, delta). 없으면 (0,0,0). gain = 리터럴 대비 절감 비트."""
    best_len, best_delta, best_gain = 0, 0, 0
    if i + MIN_MATCH <= n:
        lst = heads.get(raw[i:i + 3])
        if lst:
            for p in reversed(lst[-max_chain:]):
                delta = i - p
                if delta <= 0:
                    continue
                if delta > MAX_DELTA:
                    break                    # reversed라 delta 증가 → 이후 전부 초과
                l = 0
                lim = min(MAX_MATCH, n - i)
                while l < lim and raw[p + l] == raw[i + l]:
                    l += 1
                if l < MIN_MATCH:
                    continue
                c = _cost(256 + delta) + _cost(l - MIN_MATCH)
                lit = sum(lit_cost[b] for b in raw[i:i + l])
                if lit - c > best_gain:
                    best_gain, best_len, best_delta = lit - c, l, delta
    return best_gain, best_len, best_delta


def encode_tokens(raw, dictionary, max_chain=1024, lazy=True):
    """raw -> 토큰 리스트 [('L', byte) | ('M', delta, len)].

    ★max_chain = 매치 후보를 몇 개까지 훑을지. 64->1024로 entry4 −2,085 B(1024에서 포화).
    ★lazy = 1-step lazy matching. i의 매치보다 i+1의 매치가 이득이 크면 리터럴 하나를
      먼저 내보내고 매치 판단을 미룬다(i+1 검색 결과는 캐시해 재사용). entry4 −9,384 B.
    """
    rank = [0] * 256
    for i, v in enumerate(dictionary):
        rank[v] = i
    lit_cost = [_cost(rank[b]) for b in range(256)]

    heads = {}
    tokens = []
    raw = bytes(raw)
    i, n = 0, len(raw)
    cached = None                            # (pos, gain, len, delta)

    def add_heads(lo, hi):
        for j in range(lo, hi):
            if j + 3 <= n:
                heads.setdefault(raw[j:j + 3], []).append(j)

    while i < n:
        if cached is not None and cached[0] == i:
            gain, blen, bdelta = cached[1], cached[2], cached[3]
        else:
            gain, blen, bdelta = _find_best(raw, i, n, heads, lit_cost, max_chain)
        cached = None

        if blen and lazy and i + 1 < n:
            add_heads(i, i + 1)              # i+1 검색 전에 i를 후보에 넣는다
            g2, l2, d2 = _find_best(raw, i + 1, n, heads, lit_cost, max_chain)
            if g2 > gain:                    # 다음 위치가 더 이득 → 매치를 미룬다
                tokens.append(('L', raw[i]))
                cached = (i + 1, g2, l2, d2)
                i += 1
                continue
            tokens.append(('M', bdelta, blen))
            add_heads(i + 1, i + blen)       # i는 이미 넣었다
            i += blen
            continue

        if blen:
            tokens.append(('M', bdelta, blen))
            add_heads(i, i + blen)
            i += blen
        else:
            tokens.append(('L', raw[i]))
            add_heads(i, i + 1)
            i += 1
    return tokens


def tokens_to_bits(tokens, dictionary):
    rank = [0] * 256
    for i, v in enumerate(dictionary):
        rank[v] = i
    out = _BW()
    for t in tokens:
        if t[0] == 'L':
            out.code(rank[t[1]])
        else:
            out.code(256 + t[1])
            out.code(t[2] - MIN_MATCH)
    return out.done()


def compress(raw, dictionary, max_chain=1024, lazy=True):
    """raw -> LS11 블록 비트스트림."""
    return tokens_to_bits(encode_tokens(raw, dictionary, max_chain, lazy), dictionary)


def resort_dict(tokens_per_block, old_dict):
    """리터럴 방출 빈도 내림차순으로 사전 재정렬. 동률·미방출 바이트는 원본 순서 유지.

    ★★사전은 파일 헤더(0x10)에 저장되고 디코더가 파일에서 읽는다 — 우리가 바꿀 수 있는 값.
      코에이 원본 사전은 일본어 코퍼스 빈도순이라, 한글 운반체가 대량인 번역 코퍼스에선
      분포가 어긋나 있었다. 재정렬 + lazy로 entry4 708,743 -> **676,443 B** (−32,300).
    """
    cnt = {}
    for toks in tokens_per_block:
        for t in toks:
            if t[0] == 'L':
                cnt[t[1]] = cnt.get(t[1], 0) + 1
    old_pos = {v: i for i, v in enumerate(old_dict)}
    new = sorted(range(256), key=lambda b: (-cnt.get(b, 0), old_pos[b]))
    assert len(set(new)) == 256
    return bytes(new)


def build(blocks, dictionary, magic=b'LS11', resort=True):
    """블록 리스트 -> LS11 파일 전체. 압축본이 원본보다 크면 그 블록은 무압축으로 둔다.

    resort=True면 사전을 코퍼스 빈도로 재정렬(2회 반복 수렴)한 뒤 인코딩한다.
    ⚠️재정렬 사전은 '디코더가 파일 사전을 읽는다'는 가정 위에 있다(PC KOR판이 심볼테이블
      0으로도 동작 = 방증). **실기 이분 확인 전까진 미검증** — 확인 전 배포 금지."""
    dic = bytes(dictionary)
    if resort:
        toks = [encode_tokens(b, dic) for b in blocks]
        dic = resort_dict(toks, dic)
        toks = [encode_tokens(b, dic) for b in blocks]
        dic = resort_dict(toks, dic)
    packed = []
    for b in blocks:
        c = compress(b, dic)
        packed.append(c if len(c) < len(b) else bytes(b))
    head = bytearray(magic + b'\x00' * 12 + dic)
    off = 16 + 256 + 12 * len(packed) + 4
    for c, b in zip(packed, blocks):
        head += struct.pack('>III', len(c), len(b), off)
        off += len(c)
    head += b'\x00\x00\x00\x00'
    return bytes(head) + b''.join(packed)
