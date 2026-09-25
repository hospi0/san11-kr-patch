# -*- coding: utf-8 -*-
"""시나리오·스테이지 설명칸 22개를 **폭 안전선에 맞춰** 다시 줄바꿈한다 (세션26).

실기 증상
  「넘침」 4장 = 추천선택 설명칸의 줄이 **가로로 잘려 나갔다**(스크롤도 워드랩도 없다).
  「줄바꿈어색」 = 스테이지선택 설명칸은 워드랩은 되지만 **낱말 한가운데서 끊긴다**.
  두 화면은 실패 방식이 다르다 — 섞어서 판단하면 안 된다.

안전선 = 15.0 전각
  원본 일본어가 이 22줄을 전부 **한 줄 15.0전각으로 하드랩**해 두었다(세션26 실측:
  #609 열 줄이 정확히 15.0). 「원본이 쓰는 최대 = 증명된 안전선」 원칙 그대로 15.0을 쓴다.
  잘린 우리 줄들은 16.0~28.0이었다.
  폭 단위: 한글·한자·전각기호 = 1.0 / ASCII·공백 = 0.5.

줄 수 — **제한 없음(자동 스크롤)**
  ⚠️처음에 "원본 줄 수를 넘지 말 것"이라는 제약을 스스로 만들어 문장을 깎았는데, **근거가 없었다.**
  실기 스크린샷의 상자는 7~8줄만 보이는데 원본 일본어는 9~10줄이다. 즉 **원본 자신이 이미
  상자를 넘긴다** — 상용 게임이 설명 마지막 문장을 못 보여줄 리 없으니 자동 스크롤이 맞다.
  (세션9 교훈 재확인: 「추정치로 번역을 미리 깎지 말 것」·「모순이 나오면 내 모델을 의심하라」)
  그래서 줄 수는 참고로만 출력하고 제약하지 않는다. **가로 폭만이 진짜 한계다.**

Usage: python tools/rewrap_descriptions.py [--write]
"""
import io
import json
import os
import re
import sys
import unicodedata as U

MAXW = 15.0
TOK = re.compile(r"\{(?:V:[0-9a-f]{2,6}|N|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")


def width(s):
    s = U.normalize('NFC', TOK.sub('', s))
    w = 0.0
    for ch in s:
        if U.combining(ch):
            continue
        w += 1.0 if (U.east_asian_width(ch) in 'WF' or ch == '　') else 0.5
    return w


def wrap(text, maxw=MAXW):
    """어절 단위 그리디 줄바꿈. **낱말 중간에서는 절대 자르지 않는다.**"""
    lines, cur = [], ''
    for word in text.split(' '):
        cand = word if not cur else cur + ' ' + word
        if width(cand) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def main():
    write = '--write' in sys.argv
    data = json.load(io.open(os.path.join(os.path.dirname(__file__),
                                          'description_texts.json'), encoding='utf-8'))
    edits, bad = {}, []
    for key, para in data.items():
        fname, blk, idx = key.split('/')
        lines = wrap(' '.join(para.split()))
        edits.setdefault(fname, {})[(blk, idx)] = '{N}'.join(lines)
        over = [l for l in lines if width(l) > MAXW]
        if over:
            bad.append((key, '폭초과', over))

    total = 0
    for fname, table in edits.items():
        path = os.path.join('work', fname)
        raw = io.open(path, encoding='utf-8', newline='').read()
        out = raw.split('\n')
        for i, ln in enumerate(out):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit():
                continue
            k = (p[0], p[1])
            if k not in table:
                continue
            njp = len(re.split(r'\{N\}', p[3]))
            new = table[k]
            nkr = len(re.split(r'\{N\}', new))
            print('%s blk%s #%-4s %d줄(원본%d) 최대폭 %.1f'
                  % (fname, p[0], p[1], nkr, njp,
                     max(width(x) for x in new.split('{N}'))))
            for x in new.split('{N}'):
                print('      %5.1f %s' % (width(x), x))
            p[4] = new
            out[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            total += 1
        if write:
            bak = path + '.bak_rewrap'
            if not os.path.exists(bak):
                io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(out))

    print()
    if bad:
        print('★문제 %d건:' % len(bad))
        for b in bad:
            print('   ', b)
    print('%d줄 %s' % (total, '재줄바꿈 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
