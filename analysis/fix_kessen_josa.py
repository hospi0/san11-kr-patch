# -*- coding: utf-8 -*-
"""e4_kessen.tsv의 "조사+변수 결함"(142줄)을 고정명사 삽입으로 해소한다.

{V:xxxx} 변수는 실행 시 무장/도시/세력 이름으로 치환되는데, 그 이름의 받침
유무를 게임이 미리 알 수 없어 을/를·이/가·은/는·와/과 중 하나로 고정해 쓰면
절반은 문법이 깨진다([[feedback_kr_patch_verification]]). 회피책 = 변수 뒤에
받침이 고정된 명사를 붙여, 조사가 그 명사에 붙게 만드는 것(entry4_sys에서
검증된 방법).

변수 코드별 유형은 실제 jp 문맥(陥落/攻略=지명, 참모/軍중=세력, 殿/様/め=인명)을
전수 대조해 분류했다(analysis 결과는 세션 로그 참고):
  인명 -> "님" (받침 ㅁ)   지명 -> "성" (받침 ㅇ)   세력 -> "군" (받침 ㄴ)
셋 다 받침이 있어 조사 정규화 규칙은 동일하다.

Usage: python analysis/fix_kessen_josa.py [--dry]
"""
import io
import re
import shutil
import sys

TSV = 'work/e4_kessen.tsv'

PERSON = ['0a32', '0b32', '0c32', '0d32', '0e32', '0f32', '1032',
          '0a33', '0a36', '0b33', '0b36', '0c33', '0d33', '0d36', '1132']
PLACE = ['3232', '3332', '3432', '3c32']
FACTION = ['1433', '1533', '2832', '2932', '2a32', '0c38', '0e38']

TYPE_MAP = {}
for c in PERSON:
    TYPE_MAP[c] = '님'
for c in PLACE:
    TYPE_MAP[c] = '성'
for c in FACTION:
    TYPE_MAP[c] = '군'

# 님/성/군 전부 받침 있는 명사 -> 받침형 조사로 정규화
TO_BATCHIM = {'을': '을', '를': '을', '이': '이', '가': '이', '은': '은', '는': '은',
              '으로': '으로', '이라': '이라', '라': '이라', '와': '과', '과': '과'}

PATTERN = re.compile(
    r'\{V:(' + '|'.join(re.escape(c) for c in TYPE_MAP) + r')\}'
    r'(\s*」?\s*)(을|를|이|가|와|과|은|는|으로|이라|라)(?![가-힣])'
)


def fix(kr):
    def repl(m):
        code, mid, particle = m.group(1), m.group(2), m.group(3)
        noun = TYPE_MAP[code]
        return '{V:%s}%s%s%s' % (code, noun, mid, TO_BATCHIM[particle])
    return PATTERN.sub(repl, kr)


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
            p[4] = new
            lines[i] = '\t'.join(p)
            n += 1

    print('%d줄 수정' % n)
    if dry:
        print('(--dry: 쓰지 않음)')
        return
    shutil.copy(TSV, TSV + '.bak5')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s' % TSV)


if __name__ == '__main__':
    main()
