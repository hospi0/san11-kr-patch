# -*- coding: utf-8 -*-
"""entry4 번역 게이트 — 임의의 e4_*.tsv에 대해 번역된 kr 줄을 검사한다 (통합판).

검사(공용 로직은 e4_common):
  1. 토큰 시퀀스 보존 — jp의 {N}{V:..}{1c}{05}{BTNxx} 순서·개수가 kr과 일치
     (가이지 {BTNxx}는 한글로 풀어써 사라지는 것만 예외 허용).
  2. 하이퍼링크 id 보존 — {1c}[{1c}I<8hex>...{1c}] id 목록이 jp와 동일(링크 없으면 자동 통과).
  3. 잔존 일본어 0 — kr에 가나·CJK 한자 있으면 실패(운반체 오염).
  4. 조사+변수 결함 — {V:..} 뒤 받침 의존 조사(을/를/이/가/…).
  5. 가이지 잔존 — kr의 {BTNxx} 중 GAIJI_MAP에 있는 것.
  6. 인코딩 가능 — 한자 운반체 KeyError = 한자 잔존 안전망.
  --width 주면 화면폭 증가도 리포트(자동 스크롤 화면은 무의미하니 기본 off).

Usage:
  python analysis/check_e4.py work/e4_dict.tsv [--only-block 21] [--width]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e4_common as C  # noqa: E402


def main():
    tsv = sys.argv[1]
    only = None
    for i, a in enumerate(sys.argv):
        if a == '--only-block':
            only = sys.argv[i + 1]
    do_width = '--width' in sys.argv

    rows = C.read_tsv(tsv)
    checked, hard, warn = 0, 0, 0
    base = 0.0
    if do_width:
        base = max((max(C.width(x) for x in C.screen_lines(r[4]))
                    for r in rows if r[4].strip()), default=0.0)
        print('기존 번역이 쓰는 최대 화면폭 = %.1f 전각 (참고 기준선)\n' % base)

    for p in rows:
        blk, idx, jp, kr = p[0], p[1], p[3], p[4]
        if not kr.strip() or (only and blk != only):
            continue
        checked += 1
        key = '%s:%s' % (blk, idx)

        # 구조 토큰(비-{N})은 정확히 일치해야 함 = 치명
        # ({01}C·{01}J 참조는 structural_tokens가 양쪽에서 스트립한다)
        exp = C.structural_tokens(jp)
        got = C.structural_tokens(kr)
        if got != exp:
            print('[%s] ★구조 토큰 불일치 (기대 %d -> 번역 %d)' % (key, len(exp), len(got)))
            for i, (a, b) in enumerate(zip(exp, got)):
                if a != b:
                    print('     첫 차이 #%d: 기대 %s -> 번역 %s' % (i, a, b))
                    break
            hard += 1
        # {N} 개수 차이 = 경고(자동스크롤 산문은 재줄바꿈 정상 / 잘림 화면은 사람이 판단)
        nj, nk = C.toks(jp).count('{N}'), C.toks(kr).count('{N}')
        if nj != nk:
            print('·[%s] {N} 개수 %d -> %d (자동스크롤이면 무해)' % (key, nj, nk))
            warn += 1
        if C.link_ids(jp) != C.link_ids(kr):
            print('[%s] ★링크 id 불일치 jp=%s kr=%s' % (key, C.link_ids(jp), C.link_ids(kr)))
            hard += 1
        left = C.residual_jp(kr)
        if left:
            print('[%s] ★일본어 잔존: %s' % (key, left))
            hard += 1
        m = C.josa_defect(kr)
        if m:
            print('[%s] ★조사+변수 결함: ...%s...' % (key, kr[max(0, m.start() - 4):m.end() + 2]))
            hard += 1
        g = C.gaiji_left(kr)
        if g:
            print('[%s] ★가이지 잔존 %s — 한글로 풀어쓸 것' % (key, g))
            hard += 1
        ok, err = C.encode_ok(kr)
        if not ok:
            print('[%s] ★인코딩 실패: %s' % (key, err))
            hard += 1
        if do_width:
            wj = max(C.width(x) for x in C.screen_lines(jp))
            wk = max(C.width(x) for x in C.screen_lines(kr))
            if wk > wj:
                over = wk > base
                print('%s[%s] 폭: 원본 %.1f -> 번역 %.1f 전각%s'
                      % ('★' if over else '·', key, wj, wk, ' (기존 관행 초과!)' if over else ''))
                warn += 1

    print('\n검사 %d줄 / 치명 %d건 / 경고 %d건' % (checked, hard, warn))
    if hard:
        sys.exit(1)
    print('✓ 게이트 통과 (치명 0)')


if __name__ == '__main__':
    main()
