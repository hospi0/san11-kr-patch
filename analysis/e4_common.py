# -*- coding: utf-8 -*-
r"""entry4 번역 배치 공용 로직 — merge_batch / check_e4 가 함께 쓴다.

★모든 e4_*.tsv(sys·dict·bio·tutorial·kessen·dialogue)는 형식이 같다:
  컬럼 = block, index, bytes, jp, kr.  파일별 고유 규칙(dict의 하이퍼링크 등)만
  달라서, 공통 검사는 여기 한 곳에 두고 도구는 얇게 유지한다.

★토크나이저는 반드시 help_codec.TOKEN_RE(인코더 정본)를 쓴다 — 자체 정규식 `\{[^}]*\}`는
  `{04}{%20`의 리터럴 `{`를 토큰 시작으로 오인해 거짓 불일치를 낸다
  ([[feedback_kr_patch_verification]] 검사기↔인코더 불일치).

★★토큰은 두 부류다:
  - **구조 토큰**({05}분기·{V:}변수·{1c}링크·{BTN}버튼·{04}{06}·ESC·생제어) = 어긋나면
    분기/변수/링크가 깨진다 → **정확히 일치해야 한다(치명).**
  - **{N} 줄바꿈** = 자동 스크롤·워드랩 화면(결전·시나리오·특기 산문)에선 번역자가 재배치하는 게
    정상(세션9 결정) → 개수 차이는 **경고**일 뿐. 단 가로 잘림 화면(환경설정)에선 사람이 판단.
"""
import io
import os
import re
import unicodedata as U

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, 'tools'))
import help_codec                                    # noqa: E402
from gaiji_map import GAIJI_MAP                      # noqa: E402

# TOKEN_RE 지연 컴파일 강제(없으면 동일 정규식으로 채운다)
if help_codec.TOKEN_RE is None:
    help_codec.TOKEN_RE = re.compile(
        r"\{(?:V:[0-9a-f]{2,6}|N|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")
TOK = help_codec.TOKEN_RE

JP = re.compile(r'[぀-ヿ㐀-䶿一-鿿]')            # 가나 + CJK 확장A + CJK 통합한자
# {01}C·{01}J 참조 = entry3 part1 삽입/점프 매크로. TOKEN_RE는 이걸 {01}·{88}·{00}
# 개별 토큰으로 쪼개고 하위바이트 가나(ふ/し/か…)를 리터럴로 남긴다. 구조토큰 비교와
# 잔존일본어 검사 전에 통째로 제거해야 거짓 불일치·거짓양성이 안 난다(세션14 태스크8).
# 하위바이트 리터럴은 `}`(0x7d, idx 381 등)도 될 수 있어 [^{]로 받는다([^{}]면 {01}C}를 놓침).
CJ_REF = re.compile(r'\{01\}[CJ](?:\{[0-9a-f]{2}\}|\{N\}|[^{])(?:\{00\}|\{01\})?')
BRANCH = re.compile(r'(?:\{05\})+')
LINK_ID = re.compile(r'\{1c\}\[\{1c\}I([0-9A-Fa-f]{8})')
# 이름·지명·세력 변수(4자리+)만 조사 결함 대상. 2자리는 수치변수({V:82}=금액,{V:ca}=년)라
# 아라비아 숫자로 렌더돼 조사가 그 발음을 따르므로 제외한다(세션14).
JOSA = re.compile(r'\{V:[0-9a-f]{4,6}\}\s*[」]?\s*(을|를|이|가|와|과|은|는|으로|이라|라)(?![가-힣])')
NAKAGURO = set('・ー')      # 카타카나 중점·장음 = 구두점(원문 사용). 잔존일본어에서 제외.

_CODEC = None


def codec():
    """한자 운반체 코덱(인코딩 검증용). SLPM 경로는 프로젝트 고정."""
    global _CODEC
    if _CODEC is None:
        from encoding import Codec
        _CODEC = Codec(r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01')
    return _CODEC


def strip_cj(s):
    """{01}C·{01}J 참조 매크로를 통째로 제거(어미형이 kr에서 사라진 뒤 구조 비교용)."""
    return CJ_REF.sub('', s)


def toks(s):
    return TOK.findall(s)


def allowed_tokens(jp):
    """jp 토큰에서 가이지 {BTNxx}(한글로 풀어써 사라질 것)를 뺀 '기대 토큰열'(전체)."""
    return [x for x in toks(jp)
            if not (re.fullmatch(r'\{BTN([0-9a-f]{2})\}', x)
                    and 0xf000 + int(x[4:6], 16) in GAIJI_MAP)]


def structural_tokens(s):
    """구조 토큰만(= allowed_tokens에서 {N} 제외). {01}C·{01}J 참조는 먼저 스트립한다
    (어미형은 kr에서 제거·단어형은 양쪽 유지 → 스트립하면 양쪽 대칭). 치명 비교용."""
    return [x for x in allowed_tokens(strip_cj(s)) if x != '{N}']


def residual_jp(kr):
    """kr에서 토큰 제거 후 남은 일본어(가나·한자) 문자 집합. 없으면 ''.
    {01}C·{01}J 참조 하위바이트 가나는 진짜 일본어가 아니므로 먼저 스트립한다.
    나열 중점 ・·장음 ー은 구두점이라 잔존 판정에서 뺀다."""
    return ''.join(sorted(set(JP.findall(TOK.sub('', strip_cj(kr)))) - NAKAGURO))


def link_ids(s):
    return LINK_ID.findall(s)


def josa_defect(kr):
    """{V:..} 뒤 받침 의존 조사. match 객체 또는 None."""
    return JOSA.search(kr)


def gaiji_left(kr):
    """kr에 남은 가이지 {BTNxx}(한글로 풀어써야 하는 것) 목록."""
    return [x for x in toks(kr)
            if re.fullmatch(r'\{BTN([0-9a-f]{2})\}', x)
            and 0xf000 + int(x[4:6], 16) in GAIJI_MAP]


def encode_ok(kr):
    """인코딩 가능 여부(한자 운반체 KeyError = 한자 잔존 안전망). (ok, err)."""
    try:
        help_codec.encode(U.normalize('NFC', kr), codec())
        return True, None
    except Exception as e:
        return False, repr(e)[:60]


def width(s):
    """전각=1, 반각=0.5 (토큰 제거 후)."""
    s = TOK.sub('', s)
    return sum(1.0 if U.east_asian_width(c) in 'WF' else 0.5 for c in s)


def screen_lines(s):
    """분기({05}런)와 줄바꿈({N})으로 쪼갠 '한 화면 한 줄'들."""
    out = []
    for br in BRANCH.split(s):
        out += br.split('{N}')
    return out


def read_tsv(path):
    """e4_*.tsv -> [(block, index, bytes, jp, kr)] (헤더·주석 제외)."""
    rows = []
    for ln in io.open(path, encoding='utf-8'):
        if ln.startswith('#'):
            continue
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            rows.append(p)
    return rows
