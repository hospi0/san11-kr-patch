# -*- coding: utf-8 -*-
"""이벤트 알림 로그(dialogue block 0·1·2)의 **이름변수 뒤 조사**를 간결체로 정리.

## 문제
`{V:...}` = 무장·세력·도시 이름이 런타임에 들어오는 변수. 받침을 알 수 없으므로
홑조사를 붙이면 절반이 틀린다(「관우이」「장비을」「하후돈로」). 전체 1,332곳인데
**병기(이(가))로 바꾸면 +5,328 B** — entry4 여유 702 B로는 불가능하다.

## 접근 (2026-07-20 사용자 선택)
그중 **895곳이 block 0·1 = 한 줄짜리 이벤트 알림 로그**다. 이런 로그는 한국어에서
**조사를 생략한 간결체가 오히려 자연스럽고**(도움말 UI에서 이미 쓰는 문체),
조사를 지우면 **바이트가 줄어** 나머지를 병기로 처리할 여유가 생긴다.

  주격 가/이 · 목적격 를/을 · 주제 는/은  → 생략 (-2B)
  와/과  → 이름 나열이면 `·` (원문에 이미 쓰는 기호) / 그 밖엔 `와(과)` 병기 (+4B)
  로     → `(으)로` 병기 (+4B). 이건 생략이 불가능하다.

## 범위
dialogue block 0·1·2 만. block 3·4·24(대사)와 tutorial/kessen 산문은 문장이라
간결체가 안 어울린다 → 손대지 않는다.

사용: python analysis/fix_name_josa_log.py --dry   # 표본 출력만
      python analysis/fix_name_josa_log.py
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(REPO, 'work', 'e4_dialogue.tsv')
BLOCKS = {'0', '1', '2'}

V = r'\{V:(?!96\}0x)[0-9a-f]{2,4}\}'
NEXT_VAR = re.compile(r'^\s*\{V:')


def convert(s):
    out, i, n = [], 0, 0
    while i < len(s):
        m = re.compile(V).match(s, i)
        if not m:
            out.append(s[i])
            i += 1
            continue
        out.append(m.group(0))
        i = m.end()
        if i >= len(s):
            break
        ch = s[i]
        rest = s[i + 1:]
        if ch in '가이를을는은':
            # 생략. ⚠️뒤에 또 변수가 올 때 `, `로 끊는 안도 만들었으나
            #   로그 전체가 헤드라인 톤이 된다고 해서 뺐다(2026-07-20 사용자 결정).
            i += 1
            n += 1
        elif ch in '와과':
            # `{V}와 {V}` = 이름 나열 → 가운뎃점 / 그 밖엔 병기
            if NEXT_VAR.match(rest):
                out.append('·')
                i += 1
                while i < len(s) and s[i] == ' ':
                    i += 1
            else:
                out.append('와(과)')
                i += 1
            n += 1
        elif ch == '로':
            out.append('(으)로')
            i += 1
            n += 1
    return ''.join(out), n


def main():
    dry = '--dry' in sys.argv
    lines = open(PATH, encoding='utf-8').read().split('\n')
    total, changed, samples = 0, 0, []
    for i, line in enumerate(lines):
        cols = line.split('\t')
        if len(cols) < 5 or cols[0] not in BLOCKS:
            continue
        new, n = convert(cols[4])
        if n:
            total += n
            changed += 1
            if len(samples) < 30:
                samples.append((cols[0], cols[1], cols[4], new))
            cols[4] = new
            lines[i] = '\t'.join(cols)
    for blk, idx, old, new in samples:
        print('block%s idx%s' % (blk, idx))
        print('   전: %s' % old.replace('{N}', ' / ')[:110])
        print('   후: %s' % new.replace('{N}', ' / ')[:110])
    print('\n%d줄 / %d곳 %s' % (changed, total, '(dry)' if dry else '수정'))
    if not dry:
        bak = PATH + '.bak_namejosa'
        if not os.path.exists(bak):
            open(bak, 'w', encoding='utf-8').write(
                open(PATH, encoding='utf-8').read())
        open(PATH, 'w', encoding='utf-8').write('\n'.join(lines))


if __name__ == '__main__':
    main()
