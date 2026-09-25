# -*- coding: utf-8 -*-
"""e4_tutorial.tsv kr의 어미형 {01}C 토큰을 한국어 어미로 인라인 완성하고 토큰을 지운다.

배경(세션13 해독): {01}C <low> <bank> = entry3 part1 msg[bank*256+low] 삽입 매크로.
  - 단어형(인칭·호칭·감탄사)은 entry3 테이블을 한글화했으므로 **토큰을 남긴다**(KEEP).
  - 어미형(だ/です·ました…)은 테이블을 건드리면 미번역 dialogue가 깨지므로
    **kr 쪽에서 어미를 완성하고 토큰을 제거**한다(자모 재조합).
번역자가 어간을 규칙적으로 써 놨다(하+ㅂ니다→합니다, 알겠+습니다, 오시+ㅂ시오→오십시오).
확신 없는 어간은 건드리지 않고 리뷰 파일로 뽑는다.

Usage: python analysis/fix_tutorial_ctokens.py [--dry]
  출력: work/e4_tutorial.tsv (백업 .bak_ctok) + work/ctoken_review.txt
"""
import io
import re
import shutil
import sys
import unicodedata

sys.path.insert(0, 'tools')
import help_codec  # noqa: E402

TSV = 'work/e4_tutorial.tsv'
REVIEW = 'work/ctoken_review.txt'

# ── 토큰 파싱 ────────────────────────────────────────────────────────────────
#   ★세션17: lit는 [^{}]였는데, payload 바이트가 '}' 자체인 매크로가 파서에 안 걸려
#   조용히 건너뛰던 버그를 fix_dialogue_ctokens.py에서 발견·수정(자세한 내용은 그쪽 참조).
PAT = re.compile(
    r'\{01\}C(?:\{(?P<hex>[0-9a-f]{2})\}|(?P<nl>\{N\})|(?P<lit>[^{]))'
    r'(?P<bank>\{00\}|\{01\})?')
TOK = re.compile(r'\{[^}]*\}')          # 어간 추출용(단순 토큰 제거)


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


# ── 분류 ────────────────────────────────────────────────────────────────────
# 단어형·감탄사 = 토큰 유지(entry3에서 한글 렌더)
KEEP = {0, 6, 7, 14, 15, 35, 36, 52, 67, 69, 89, 107,
        182, 183, 200, 201, 202, 203, 215, 236, 281, 282,
        306, 383, 384, 385, 386, 392, 393}
# 어감 조사·접두(ね/よ/ぞ/ご/お) = 제거만
DROP = {263, 264, 267, 268, 361, 363, 408, 409}
# 항상 리뷰(용례 적고 문형 다양)
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
# 세션17: {01}C}{01}(코드 0x7d) — dialogue와 같은 u단 동사 어미선택 매크로.
# fix_dialogue_ctokens.py에서 파서 버그와 함께 발견·분류(자세한 내용은 그쪽 참조).
RULE_OF[381] = 'VOL'


# ── 자모 도우미 ──────────────────────────────────────────────────────────────
def jong(ch):
    return (ord(ch) - 0xAC00) % 28 if '가' <= ch <= '힣' else None


def set_jong(ch, j):
    base = ord(ch) - 0xAC00
    return chr(0xAC00 + (base // 28) * 28 + j)


PB = 17   # ㅂ 종성
SS = 20   # ㅆ 종성

# ㅂ니다 재조합을 허용하는 「용언 어간」 모음끝 글자(명사 끝이면 입니다가 맞아 오적용 방지)
VERB_VOWEL = set('이하되지리내보두가오serve서채우쓰떠')


def _ni(stem, q=False):
    """「니」로 끝나는 어간의 완성 — 옵니/습니→다, 느니→라(고어), 나이→다, 아니→ㅂ니다."""
    if stem.endswith('느니'):
        return '라'
    if stem.endswith('나이'):
        return '다'
    if stem.endswith('아니'):
        return ('R', '닙', '니까' if q else '니다')
    if len(stem) >= 2 and stem[-2] in '옵습':
        return '까' if q else '다'
    return None


INTERROG = ('무엇', '무슨', '누구', '어디', '어찌', '어떠', '어떻', '왜 ')
NOUN_JONG = {4, 16, 17, 21}      # ㄴ·ㅁ·ㅂ·ㅇ 받침 — 용언 어간엔 거의 없다 = 명사 추정


def _interrog(stem):
    tail = stem[-8:]
    return any(w in tail for w in INTERROG)


def _da(stem, q=False):
    """polite 평서(ㅂ니다/습니다) 완성. q=True면 의문(ㅂ니까/습니까)."""
    nida, sumnida = ('니까', '습니까') if q else ('니다', '습니다')
    ipnida = '입니까' if q else '입니다'
    ch = stem[-1]
    if stem.endswith('니다') or stem.endswith('요'):
        return ''                                  # 이미 완결 — 토큰만 제거
    if not q and _interrog(stem):
        return None                                # 의문사+평서 어미 = 오적용 위험
    if stem.endswith('나이'):
        return '까' if q else '다'                 # 청하옵나이+다 (고어체)
    if ch == '니':
        return _ni(stem, q)
    if ch in '는은':
        return None                                # 관형사형/조사 — 리뷰
    if ch == '옵':
        return nida
    if ch == '것':
        return ipnida
    if ch == '사' and len(stem) >= 2 and stem[-2] in '있하':
        return '옵니다'                            # 있사옵니다 (의문형도 동일 취급)
    j = jong(ch)
    if j is None:
        return None
    if j == 0:
        if ch == '오':
            return None                            # 불러오+だ 등 명령조 혼재 — 리뷰
        if ch == '이' and (len(stem) < 2 or stem[-2] in ' 의'):
            return ipnida                          # 명사 「이」 — 계사 온전히 붙임
        if ch == '이' or ch in VERB_VOWEL:
            return ('R', set_jong(ch, PB), nida)   # 마지막 글자에 ㅂ 붙임
        return None                                # 모음끝 명사 추정 — 리뷰
    if j == 8:                                     # ㄹ받침 — 용언(열)만 ㄹ탈락, 명사(사실·일)는 계사
        return ('R', set_jong(ch, PB), nida) if ch == '열' else ipnida
    if j in NOUN_JONG:
        return ipnida                              # 만단·낭인·법·안정 등 명사 추정
    return sumnida


def complete(rule, stem):
    """어간 끝에 붙일 완성문자열. ('R', 대체글자, 꼬리)=마지막 글자 교체, None=리뷰."""
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
        if ch == '니':
            return _ni(stem)
        return None
    if rule == 'NE':
        if ch in '다님':
            return None
        if _interrog(stem):
            return None
        if ch in '되하리이오우':
            return '는군요'                        # 동사 어간 — 가면 되는군요
        j = jong(ch)
        if j in NOUN_JONG or j == 8:
            return '이군요'                        # 명사 추정 — 성장이군요
        return '군요'
    if rule == 'GUESS':
        if _interrog(stem):
            return None
        if ch == '겠':
            return '지요'
        if ch == '니':
            return _ni(stem)
        if ch in '하리이되없않좋늦있크':
            return '겠지요'
        j = jong(ch)
        if j in NOUN_JONG or j in (1, 8):
            return '이겠지요'                      # 명사 추정 — 위덕이겠지요
        return None
    if rule == 'CONN':
        if ch == '겠' or jong(ch) == SS:
            return '지만'
        return None
    if rule == 'QUOTE':
        j = jong(ch)
        if j is None:
            return None
        return '라니' if j == 0 else '이라니'
    if rule == 'VOL':
        if _interrog(stem):
            return None
        # 세션17: 「하지 마{VOL}!」류 부정명령 어간 — 겠습니다를 붙이면 깨진다(dialogue와 동일).
        if ch == '마':
            return ''
        if ch == '겠':
            return '습니다'
        if ch == '시':
            return '지요'
        if ch == '사':
            return '옵니다'
        if ch == '니':
            return _ni(stem)
        if ch == '리':
            return '라'
        if ch in '하두보가오':
            return '겠습니다'
        return None
    if rule == 'IMPHON':
        if ch == '시':
            return ('R', set_jong(ch, PB), '시오')
        if ch == '주':
            return '십시오'
        if ch == '해':
            return ' 주십시오'
        return None
    if rule == 'IMP':
        if ch == '하':
            return '라'
        if ch == '다':
            return '오'
        if ch in '치오내':
            return '거라'
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
            # ★토큰 바로 뒤에 한글이 이어지면 번역자가 어미를 뒷문장에 이미 녹인 것
            #   (예: 「겸손하[토큰]지 마」= するな 금지형) → 완성하지 말고 토큰만 제거
            nxt = kr[m.end():m.end() + 1]
            if '가' <= nxt <= '힣':
                changed = True
                n_drop += 1
                continue
            # 토큰·문장부호가 어간과 토큰 사이를 끊으면 리뷰(어미가 붙을 곳이 없다)
            attached = cur and ('가' <= cur[-1] <= '힣')
            rule = RULE_OF.get(idx)
            comp = None
            if idx not in REVIEW_ALWAYS and rule and attached:
                comp = complete(rule, stem)
            if comp is None:
                out.append(m.group(0))             # 보류 — 토큰 유지한 채 리뷰로
                n_flag += 1
                review.append('[%s] idx=%d rule=%s\n  jp=%s\n  kr=%s'
                              % (key, idx, rule, p[3], kr))
                continue
            if isinstance(comp, tuple):
                _, rep, tail = comp
                out[-1] = out[-1][:-1] + rep       # 마지막 글자 교체(ㅂ 붙임 등)
                out.append(tail)
            else:
                out.append(comp)
            changed = True
            n_inline += 1
            applied.append('[%s] idx=%d %s | …%s -> …%s'
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
