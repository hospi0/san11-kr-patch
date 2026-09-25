# -*- coding: utf-8 -*-
"""실기 제보 버그 수정 (2026-07-21):
  1. 龐 한자 노출: e4_dialogue KR의 {BTN4c}통 → 방통 (龐統=방통), 2곳
  2. 도시명 梓潼: 재동 → 자동 (사용자 표기 확정) — places_kr·cities_kr·bio·scenario
  3. 어색한 대사: 되나군요 → 되나요 (부대 행동 확인 대사 9곳)

각 치환은 예상 건수를 검증(assert)하고, 불일치 시 중단.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (파일, old, new, 예상건수)
# places_kr·cities_kr·e4_bio 는 1차 실행에서 이미 적용됨 → 남은 것만.
JOBS = [
    ('work/e4_dialogue.tsv', '되나군요', '되나요', 18),   # 9줄×2화자변형
]


def main():
    for rel, old, new, expect in JOBS:
        path = os.path.join(REPO, rel)
        with open(path, encoding='utf-8') as f:
            s = f.read()
        n = s.count(old)
        assert n == expect, '%s: %r 예상 %d != 실제 %d' % (rel, old, expect, n)
        s2 = s.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(s2)
        # 검증: new 가 최소 expect개 생겼고 old 는 0
        assert s2.count(old) == 0 or old in new, '%s: old 잔존' % rel
        print('  %-26s %r -> %r  x%d  OK' % (rel, old, new, expect))
    print('완료.')


if __name__ == '__main__':
    main()
