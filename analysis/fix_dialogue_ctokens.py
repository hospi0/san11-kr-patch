# -*- coding: utf-8 -*-
"""e4_dialogue.tsv kr의 어미형 {01}C 토큰을 한국어 어미로 인라인 완성하고 토큰을 지운다.

fix_tutorial_ctokens.py(세션14)와 완전히 같은 엔진(entry3 조립테이블은 파일 공용이므로
KEEP/DROP/RULE_OF 분류가 그대로 재사용됨) + dialogue 전용으로 새로 나온 인덱스 83종을
entry3.bin 원문 디코드로 추가 분류(세션16).

Usage: python analysis/fix_dialogue_ctokens.py [--dry]
  출력: work/e4_dialogue.tsv (백업 .bak_ctok) + work/dialogue_ctoken_review.txt
"""
import io
import re
import shutil
import sys

sys.path.insert(0, 'tools')
import help_codec  # noqa: E402

TSV = 'work/e4_dialogue.tsv'
REVIEW = 'work/dialogue_ctoken_review.txt'

# ── 토큰 파싱 (fix_tutorial_ctokens.py와 동일) ────────────────────────────────
#   ★세션17: lit는 [^{}]였는데, payload 바이트가 '}' 자체인 매크로(코드 0x7d)가 실전에
#   존재해서(예: {01}C}{01}) 파서가 아예 못 읽고 통째로 건너뛰었다 — 리뷰에도 안 잡히고
#   조용히 원본 그대로 남아 실기에서 일본어(う)가 노출되는 사고로 이어짐(dialogue 74줄).
#   '{'는 hex/nl 대안이 먼저 소비하므로 lit에서는 '}'만 풀어주면 충분하다.
PAT = re.compile(
    r'\{01\}C(?:\{(?P<hex>[0-9a-f]{2})\}|(?P<nl>\{N\})|(?P<lit>[^{]))'
    r'(?P<bank>\{00\}|\{01\})?')
TOK = re.compile(r'\{[^}]*\}')


def tok_index(m):
    if m.group('hex'):
        low = int(m.group('hex'), 16)
    elif m.group('nl'):
        low = 0x0a
    else:
        ch = m.group('lit')
        o = ord(ch)
        if o < 0x80:
            low = o
        else:
            if 0x3041 <= o <= 0x3096:
                ch = chr(o + 0x60)
            low = help_codec._HW.get(ch)
            if low is None:
                return None
    bank = 1 if m.group('bank') == '{01}' else 0
    return bank * 256 + low


# ── 분류: 튜토리얼(세션14) 그대로 ─────────────────────────────────────────────
KEEP = {0, 6, 7, 14, 15, 35, 36, 52, 67, 69, 89, 107,
        182, 183, 200, 201, 202, 203, 215, 236, 281, 282,
        306, 383, 384, 385, 386, 392, 393}
DROP = {263, 264, 267, 268, 361, 363, 408, 409}
REVIEW_ALWAYS = {135, 167, 168, 198, 218, 255, 331, 335, 367, 398, 400, 401}

RULE_OF = {}
for idx in [128, 132, 136, 137, 157, 174, 186, 188, 213, 214, 226, 227, 238,
            259, 260, 271, 272, 297, 298, 303, 311, 312, 321, 322, 323, 324,
            337, 338, 347, 348, 351, 352, 382, 390]:
    RULE_OF[idx] = 'DA'
for idx in [204, 205]:
    RULE_OF[idx] = 'QDA'
for idx in [153, 154, 192, 193, 251, 277, 279, 355, 356, 373, 374, 375, 377]:
    RULE_OF[idx] = 'PAST'
for idx in [147, 148, 149, 150]:
    RULE_OF[idx] = 'NE'
for idx in [151, 152]:
    RULE_OF[idx] = 'GUESS'
for idx in [145, 146, 169]:
    RULE_OF[idx] = 'CONN'
for idx in [155, 156]:
    RULE_OF[idx] = 'QUOTE'
for idx in [224, 225, 309, 310, 319, 320, 343, 344, 345, 406, 407]:
    RULE_OF[idx] = 'VOL'
for idx in [228, 229]:
    RULE_OF[idx] = 'IMPHON'
for idx in [220, 221, 313, 315, 316, 339, 340]:
    RULE_OF[idx] = 'IMP'

# ── 세션16 신규: dialogue 전용 인덱스 83종 중 상위 50종을 entry3 원문 디코드로 분류.
#   word-type(가족·군명 삽입) = KEEP / 대부분 공백(장식 조사) = DROP / 나머지는 문법
#   범주가 뚜렷한 것만 RULE_OF에 추가하고, 애매한 건(부정형 등) REVIEW_ALWAYS로 넘겨
#   자동완성하지 않는다(틀린 활용을 자신있게 박아넣는 게 토큰 노출보다 위험하다).
KEEP |= {59, 64, 65, 66, 87}                  # 변수·가족호칭·군명 삽입(그라마 아님)
DROP |= {209, 261, 269, 293, 388, 389, 412}   # 대부분 공백인 성격별 장식 조사
for idx in [134, 173, 184, 185, 194, 196, 249, 257, 368]:
    RULE_OF[idx] = 'VOL'          # ましょう/よう류 권유·의지형
for idx in [180, 230, 317, 402]:
    RULE_OF[idx] = 'IMPHON'       # ください류 존대 요청형
for idx in [190, 191]:
    RULE_OF[idx] = 'PAST'         # いました/いた류 과거형
for idx in [139, 140, 141, 210, 266, 289]:
    RULE_OF[idx] = 'DA'           # だ/です류 단순 단정
for idx in [211, 295]:
    RULE_OF[idx] = 'QDA'
for idx in [314]:
    RULE_OF[idx] = 'IMP'
REVIEW_ALWAYS |= {234, 245, 274, 275, 285, 326, 330,
                  349, 357, 370, 411}          # 부정형·특수관용구 — 자동완성 위험
# ありません/ない/まい류(271,273,298,325,329) — 대부분 한국어 어간이 이미 없/않/아니로
# 부정을 끝내놨고 계사만 마저 붙이면 되므로, 새 규칙 없이 DA(jong 기반 습니다/입니다
# 완성)를 그대로 재사용한다(세션16). 어간이 조사/공백으로 끊긴 애매한 경우는 DA가
# 알아서 None을 돌려줘 리뷰로 넘어간다 — 안전.
for idx in [271, 273, 298, 325, 329]:
    RULE_OF[idx] = 'DA'
# 위 5종은 어간이 조사/공백에서 끊기면(별도 명사구 뒤에 부정 서술어 전체가 와야 하는
# 경우, 예: 「여유는 」+ありません → 「여유는 없습니다」) DA로는 못 붙인다 — 이때만
# 통째로 '없습니다'를 채운다(세션16, idx=271/273/298에서 확인).
NEGATION_FULL = {271, 273, 298}

# 세션16 2차 병합분(신규 1,018행)에서 새로 나온 인덱스 추가 분류.
for idx in [303]:
    RULE_OF[idx] = 'QUOTE_THINK'   # ~と思います: -다고/-라고 뒤에 " 생각합니다"만 이어붙임
for idx in [351]:
    RULE_OF[idx] = 'HADA'          # ~します(한자어+する): 명사 뒤에 "합니다"
for idx in [153]:
    RULE_OF[idx] = 'PAST'          # ~でした: PAST 로직 재사용(이+었습니다 등)
KEEP |= {104, 105, 106, 108}       # 殿/様 호칭·무장명 word-type 표(그라마 아님)
DROP |= {206, 267, 369}            # 대부분 공백인 성격별 장식 조사(わ/か, ね, 점프전용)
for idx in [239, 272, 300, 330, 358, 391]:
    RULE_OF[idx] = 'DA'
    NEGATION_FULL.add(idx)
for idx in [265]:
    RULE_OF[idx] = 'DA'
for idx in [356]:
    RULE_OF[idx] = 'PAST'
for idx in [322, 346]:
    RULE_OF[idx] = 'VOL'
# ★세션16 재검증: 토큰 자체의 의미가 부정(ない/ません류)인 인덱스를 DA(긍정 계사)에
# 태우면 어간에 이미 없/않/아니가 없을 때 극성이 뒤집히거나("하지"+DA→"하집니다")
# 말이 안 되는 활용이 나온다("礼は言わない"가"말은 합니다"로 반전된 사례 실제 발견).
# → 이 인덱스들은 어간이 명시적으로 부정어로 끝날 때만 완성하고, 그 외엔 리뷰로 보낸다.
NEGATION_TOKENS = {271, 273, 298, 325, 329, 239, 272, 300, 330, 358, 391}
# idx=296(の/のか/のですか)은 어간이 "-느"(고어체 -느냐) 등으로 끝나는 경우 QDA의
# ㅂ니까 완성이 안 맞는다(실제로 "없느"+QDA→"느입니까" 오생성 확인) — 완전 보류로 되돌림.
REVIEW_ALWAYS.add(296)
for idx in [334, 360]:
    RULE_OF[idx] = 'IMP'
# 세션17: {01}C}{01}(코드 0x7d, 리터럴 '}' 페이로드) — う/います를 고르는 u단 동사
# 어미선택 매크로(entry3 원문 디코드로 확인, personality branch 대부분 정중형います).
# dialogue 12곳 + tutorial 8곳, 전부 동사/형용사 어간에 직접 붙는다.
RULE_OF[381] = 'VOL'


# ── 자모 도우미 (fix_tutorial_ctokens.py와 동일) ──────────────────────────────
def jong(ch):
    return (ord(ch) - 0xAC00) % 28 if '가' <= ch <= '힣' else None


def set_jong(ch, j):
    base = ord(ch) - 0xAC00
    return chr(0xAC00 + (base // 28) * 28 + j)


PB = 17
SS = 20
VERB_VOWEL = set('이하되지리내보두가오serve서채우쓰떠쁘르')


def _ni(stem, q=False):
    if stem.endswith('느니'):
        return '라'
    if stem.endswith('나이'):
        return '다'
    if stem.endswith('아니'):
        return ('R', '닙', '니까' if q else '니다')
    if len(stem) >= 2 and stem[-2] in '옵습':
        return '까' if q else '다'
    # 나머지 「~니」는 대개 「~하였으니/~하다니」류 연결어미로 번역자가 이미 완결
    # 지어놓은 경우다(申す=말하다 토큰이 「~하였으니」에 이미 녹아든 사례, 세션16).
    return ''


INTERROG = ('무엇', '무슨', '누구', '어디', '어찌', '어떠', '어떻', '왜 ')
NOUN_JONG = {4, 16, 17, 21}
# 동사 어간과 겹치지 않는 순수 조사(체언 뒤에만 붙는다) — 이 글자로 어간이 끝나면
# VOL/GUESS의 '겠습니다/겠지요' 보편 완성을 걸지 않는다(세션16, 「항복 권고를겠습니다」
# 오적용 발견 후 추가). 가/이/은/는/도 등은 용언 어간과 동형이라 여기 넣지 않는다.
PARTICLE_ONLY = set('를을와과의만로에랑')


def _interrog(stem):
    tail = stem[-8:]
    return any(w in tail for w in INTERROG)


def _da(stem, q=False):
    nida, sumnida = ('니까', '습니까') if q else ('니다', '습니다')
    ipnida = '입니까' if q else '입니다'
    ch = stem[-1]
    if stem.endswith('니다') or stem.endswith('요'):
        return ''
    if not q and _interrog(stem):
        return None
    if stem.endswith('나이'):
        return '까' if q else '다'
    if ch == '니':
        return _ni(stem, q)
    if ch in '는은':
        return None
    if ch == '옵':
        return nida
    if ch == '것':
        return ipnida
    if ch == '사' and len(stem) >= 2 and stem[-2] in '있하':
        return '옵니다'
    j = jong(ch)
    if j is None:
        return None
    if j == 0:
        if ch == '오':
            return None
        if ch == '이' and (len(stem) < 2 or stem[-2] in ' 의'):
            return ipnida
        if ch == '이' or ch in VERB_VOWEL:
            return ('R', set_jong(ch, PB), nida)
        # ⚠️세션16: 여기서 한때 "남은 모음끝은 대개 체언+계사"로 보고 무조건
        # ipnida를 반환했으나, 물러나/바뀌/생기/좁히 같은 **동사** 어간에 붙어
        # "물러나입니다"류 오적용을 다수 발생시켰다(실기 배포 전 자체 발견·수정).
        # 노운/용언 구분이 안 되는 미분류 모음끝은 안전하게 리뷰로 넘긴다.
        return None
    if j == 8:
        return ('R', set_jong(ch, PB), nida) if ch == '열' else ipnida
    if j in NOUN_JONG:
        return ipnida
    return sumnida


def complete(rule, stem):
    if not stem:
        return None
    ch = stem[-1]
    if rule == 'DA':
        return _da(stem)
    if rule == 'QDA':
        return _da(stem, q=True)
    if rule == 'PAST':
        if ch == '겠' or jong(ch) == SS:
            return '습니다'
        if ch == '시':
            return ('R', '셨', '습니다')
        if ch == '하':
            return ('R', '했', '습니다')
        if ch == '오':
            return ('R', '왔', '습니다')
        if ch == '되':
            return ('R', '됐', '습니다')
        if ch == '있':
            return '었습니다'
        if ch == '주':
            return '었습니다'
        if ch == '내':
            return ('R', '냈', '습니다')
        if ch == '니':
            return _ni(stem)
        return None
    if rule == 'NE':
        if ch in '다님':
            return None
        if _interrog(stem):
            return None
        if ch in '되하리이오우':
            return '는군요'
        j = jong(ch)
        if j in NOUN_JONG or j == 8:
            return '이군요'
        return '군요'
    if rule == 'GUESS':
        if _interrog(stem):
            return None
        if ch == '겠':
            return '지요'
        if ch == '니':
            return _ni(stem)
        if ch in '는은' or ch in PARTICLE_ONLY:
            return None
        # -겠지요는 사실상 모든 동사·형용사 어간에 보편적으로 붙는다(세션16 확장).
        return '겠지요'
    if rule == 'CONN':
        if stem.endswith('지만') or stem.endswith('지만요'):
            return ''                # 번역자가 이미 "-지만"을 써놓은 중복 토큰
        if ch in '는은' or ch in PARTICLE_ONLY:
            return None
        return '지만'
    if rule == 'QUOTE':
        j = jong(ch)
        if j is None:
            return None
        return '라니' if j == 0 else '이라니'
    if rule == 'VOL':
        if _interrog(stem):
            return None
        # 세션17: 「하지 마{VOL}!」류 부정명령 어간(마) — 겠습니다를 붙이면 "마겠습니다"로
        # 깨진다. 「하지 마」자체로 이미 완결된 문장이라 토큰은 그냥 지운다.
        if ch == '마':
            return ''
        if ch == '겠':
            return '습니다'
        if ch == '사':
            return '옵니다'
        if ch == '니':
            return _ni(stem)
        if ch == '리':
            # 드리다·버리다·기다리다·빠뜨리다류(어간 끝 리) vs 고어체 -으리라(하리·없으리 등)
            # 구별 — 전자는 '겠습니다', 후자만 '라'(세션16, 「감사드리라」 오적용 발견 후 수정).
            if stem.endswith(('드리', '버리', '기다리', '빠뜨리', '날리', '놀리', '알리')):
                return '겠습니다'
            return '라'
        if ch in '는은' or ch in PARTICLE_ONLY:
            return None
        # -겠습니다는 사실상 모든 동사 어간에 보편적으로 붙는다(세션16 확장, 기존엔
        # '하두보가오'만 허용해 대부분이 리뷰로 새 나갔다).
        return '겠습니다'
    if rule == 'IMPHON':
        if ch == '시':
            return ('R', set_jong(ch, PB), '시오')
        if ch == '주':
            return '십시오'
        if ch == '해':
            return ' 주십시오'
        if ch == '겠':
            return '습니다'          # ください가 이미 겠-완결형 뒤에 온 경우
        if ch == '십':
            return '시오'            # 주십+ください → 주십시오(세션16, 절단된 경우)
        if ch in '는은' or ch in PARTICLE_ONLY:
            return None
        # -십시오는 사실상 모든 동사 어간에 보편적으로 붙는다(세션16 2차 확장,
        # 기존엔 시/주/해/겠/십/보만 허용해 대부분이 리뷰로 새 나갔다).
        return '십시오'
    if rule == 'QUOTE_THINK':
        if ch == '고':
            return ' 생각합니다'
        return None
    if rule == 'HADA':
        if ch in '는은' or ch in PARTICLE_ONLY:
            return None
        return '합니다'
    if rule == 'IMP':
        if ch == '하':
            return '라'
        if ch == '다':
            return '오'
        if ch in '치오내':
            return '거라'
        if ch == '시':
            return ('R', set_jong(ch, PB), '시오')   # なさい 존대명령(-십시오)
        if ch == '보':
            return '십시오'          # 보 + なさい → 보십시오
        j = jong(ch)
        if j not in (None, 0):
            return '으십시오'        # 받침 있는 어간 + なさい → -으십시오
        return None
    return None


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')
    n_inline = n_drop = n_keep = n_flag = 0
    review, applied = [], []

    for li, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
            continue
        kr = p[4]
        out, pos, changed = [], 0, False
        for m in PAT.finditer(kr):
            idx = tok_index(m)
            out.append(kr[pos:m.start()])
            pos = m.end()
            key = '%s:%s' % (p[0], p[1])
            if idx is None or idx in KEEP:
                out.append(m.group(0))
                n_keep += 1
                continue
            if idx in DROP:
                changed = True
                n_drop += 1
                continue
            cur = ''.join(out)
            stem = TOK.sub('', cur)
            nxt = kr[m.end():m.end() + 1]
            if '가' <= nxt <= '힣':
                changed = True
                n_drop += 1
                continue
            attached = cur and ('가' <= cur[-1] <= '힣')
            rule = RULE_OF.get(idx)
            # 토큰 바로 뒤가 물음표면 실제로는 의문형(어떻겠습니까？)이라 GUESS/DA의
            # 평서 완성이 아니라 QDA(-습니까) 완성을 써야 한다(세션16, idx=151 다수 발견).
            if nxt in '？?' and rule in ('GUESS', 'DA'):
                rule = 'QDA'
            neg_ok = (idx not in NEGATION_TOKENS
                      or stem.endswith(('없', '않', '아니')))
            comp = None
            if idx not in REVIEW_ALWAYS and rule and attached and neg_ok:
                comp = complete(rule, stem)
            if comp is None and idx in NEGATION_FULL and stem and stem[-1] == ' ':
                comp = '없습니까' if rule == 'QDA' else '없습니다'
            if comp is None:
                out.append(m.group(0))
                n_flag += 1
                review.append('[%s] idx=%d rule=%s\n  jp=%s\n  kr=%s'
                              % (key, idx, rule, p[3], kr))
                continue
            if isinstance(comp, tuple):
                _, rep, tail = comp
                out[-1] = out[-1][:-1] + rep
                out.append(tail)
            else:
                out.append(comp)
            changed = True
            n_inline += 1
            applied.append('[%s] idx=%d %s | ...%s -> ...%s'
                           % (key, idx, rule, stem[-6:] + '+' + m.group(0),
                              (TOK.sub('', ''.join(out)))[-12:]))
        out.append(kr[pos:])
        new = ''.join(out)
        if new != kr:
            p[4] = new
            lines[li] = '\t'.join(p)

    print('인라인 완성 %d / 제거 %d / 토큰 유지(단어형) %d / 리뷰 보류 %d'
          % (n_inline, n_drop, n_keep, n_flag))
    io.open(REVIEW, 'w', encoding='utf-8').write(
        '# 보류(토큰 유지, 수동 처리 필요) %d건\n' % n_flag
        + '\n'.join(review)
        + '\n\n# 자동 적용 %d건 (검수용)\n' % n_inline
        + '\n'.join(applied))
    print('-> %s' % REVIEW)
    if dry:
        print('(--dry: TSV 쓰지 않음)')
        return
    shutil.copy(TSV, TSV + '.bak_ctok')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s (백업 %s.bak_ctok)' % (TSV, TSV))


if __name__ == '__main__':
    main()
