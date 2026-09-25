# -*- coding: utf-8 -*-
"""e4_tutorial.tsv의 조사+변수 결함을 고정명사 삽입으로 해소(kessen 도구 확장).

변수 뒤 받침의존 조사(을/를·이/가·은/는·와/과)는 런타임 이름 받침을 몰라
절반이 깨진다([[feedback_kr_patch_verification]]). 회피 = 받침 고정 명사 삽입.
  인명 -> "님"(ㅁ)  지명 -> "성"(ㅇ)  세력 -> "군"(ㄴ)  국호 -> "나라"(받침없음)
튜토리얼 신규 변수코드(jp 문맥 대조):
  4e·0d38·1138 = 세력 -> 군 / 36·1232 = 인명(字) -> 님 / 53 = 국호 -> 나라
  82·83 = 금액/수량(백·천 단위 아라비아 숫자, 발음상 받침 有) -> 건드리지 않음

Usage: python analysis/fix_tutorial_josa.py [--dry]
"""
import io, re, shutil, sys

TSV = 'work/e4_tutorial.tsv'

PERSON = ['0a32', '0b32', '0c32', '0d32', '0e32', '0f32', '1032', '1132', '1232',
          '0a33', '0b33', '0c33', '0d33',
          '0a36', '0b36', '0c36', '0d36', '0e36', '0f36']
PLACE = ['3232', '3332', '3432', '3c32']
FACTION = ['1433', '1533', '2832', '2932', '2a32',
           '0c38', '0d38', '0e38', '1138',
           '0b4e', '0c4e', '0d4e', '0e4e']
KOKUGO = ['0a53', '0c53']

TYPE_MAP = {}
for c in PERSON:
    TYPE_MAP[c] = '님'
for c in PLACE:
    TYPE_MAP[c] = '성'
for c in FACTION:
    TYPE_MAP[c] = '군'

# 받침 있는 명사(님/성/군) -> 받침형 조사
TO_BATCHIM = {'을': '을', '를': '을', '이': '이', '가': '이', '은': '은', '는': '은',
              '으로': '으로', '이라': '이라', '라': '이라', '와': '과', '과': '과'}
# 받침 없는 명사(나라) -> 받침없음형 조사
TO_VOWEL = {'을': '를', '를': '를', '이': '가', '가': '가', '은': '는', '는': '는',
            '으로': '로', '이라': '라', '라': '라', '와': '와', '과': '와'}

P_NOUN = re.compile(
    r'\{V:(' + '|'.join(re.escape(c) for c in TYPE_MAP) + r')\}'
    r'(\s*」?\s*)(을|를|이|가|와|과|은|는|으로|이라|라)(?![가-힣])')
# 국호: 「로 감싼 명명(「{V}」…)은 제외 — {V} 바로 뒤 조사만
P_KOKU = re.compile(
    r'\{V:(' + '|'.join(KOKUGO) + r')\}'
    r'(\s*)(을|를|이|가|와|과|은|는|으로|이라|라)(?![가-힣])')


def fix(kr):
    def rn(m):
        code, mid, particle = m.group(1), m.group(2), m.group(3)
        return '{V:%s}%s%s%s' % (code, TYPE_MAP[code], mid, TO_BATCHIM[particle])

    def rk(m):
        code, mid, particle = m.group(1), m.group(2), m.group(3)
        return '{V:%s} 나라%s%s' % (code, mid, TO_VOWEL[particle])
    kr = P_NOUN.sub(rn, kr)
    kr = P_KOKU.sub(rk, kr)
    return kr


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
            continue
        new = fix(p[4])
        if new != p[4]:
            n += (len(P_NOUN.findall(p[4])) + len(P_KOKU.findall(p[4])))
            p[4] = new
            lines[i] = '\t'.join(p)
    print('조사 정규화 %d건 적용' % n)
    if dry:
        print('(--dry: 저장 안 함)')
        return
    shutil.copy(TSV, TSV + '.bak_josa')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('저장 완료 (백업 %s.bak_josa)' % TSV)


if __name__ == '__main__':
    main()
