# -*- coding: utf-8 -*-
"""조각 사전으로 미번역 줄을 채운다 (세션26).

  ① 토큰 구조는 **한 글자도 건드리지 않는다** — 조각만 갈아끼운다.
  ② 사전에 없는 조각은 그대로 두고 `work/phrase_todo.tsv`에 모은다(= 사람이 번역할 몫).
  ③ 한 줄이라도 일본어 조각이 남으면 kr을 **쓰지 않는다** — 반쪽짜리 번역은
     실기에서 「한글+가나」 섞인 줄이 되고, 운반체 한자까지 겹쳐 더 심하게 깨진다.

Usage: python tools/apply_phrase_memory.py [--write]
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phrase_memory import build_memory, split_tokens, peel   # noqa: E402

JPCH = re.compile(r"[぀-ヿ㐀-鿿]")


def rebuild(toks, parts):
    out = []
    for i, p in enumerate(parts):
        out.append(p)
        if i < len(toks):
            out.append(toks[i])
    return ''.join(out)


def main():
    write = '--write' in sys.argv
    mem = build_memory()
    # ★손으로 채운 조각 번역을 덧붙인다(work/phrase_kr.tsv: jp<TAB>kr).
    #   긴 제어구조(점프 테이블 안에 낀 짧은 전투 대사 등)는 줄 전체를 다시 쓰면 위험하다 —
    #   조각만 갈아끼우면 토큰 구조가 자동으로 보존된다.
    extra = 'work/phrase_kr.tsv'
    if os.path.exists(extra):
        n = 0
        for ln in io.open(extra, encoding='utf-8'):
            p = ln.rstrip('\n').rstrip('\r').split('\t')
            if len(p) >= 2 and p[0].strip() and p[1].strip():
                _pre, key = peel(p[0].strip())      # 사전 키도 같은 함수로 정규화
                mem[key] = p[1].strip()
                n += 1
        print('수기 조각 사전 %d개 병합' % n)
    print('조각 사전 %d개' % len(mem))

    todo, filled, partial = {}, [], []
    files = ['work/' + f for f in sorted(os.listdir('work'))
             if f.startswith('e4_') and f.endswith('.tsv')]
    result = {}
    for path in files:
        lines = io.open(path, encoding='utf-8', newline='').read().split('\n')
        for i, ln in enumerate(lines):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or p[4].strip():
                continue
            toks, parts = split_tokens(p[3])
            if not any(JPCH.search(x) for x in parts):
                continue                                  # 번역할 텍스트가 없는 제어행
            new, miss = [], []
            for x in parts:
                pre, s = peel(x.strip())
                if not s or not JPCH.search(s):
                    new.append(x)
                    continue
                if s in mem:
                    # ★x는 NFD가 섞여 있어 x.replace(s,...)가 안 먹는다 —
                    #   앞뒤 공백만 보존하고 「조건식 + 번역문」으로 다시 조립한다.
                    lead = x[:len(x) - len(x.lstrip())]
                    trail = x[len(x.rstrip()):]
                    new.append(lead + pre + mem[s] + trail)
                else:
                    new.append(x)
                    miss.append(s)
            if miss:
                for s in miss:
                    todo.setdefault(s, []).append((os.path.basename(path), p[0], p[1]))
                partial.append((path, i, p[0], p[1]))
                continue
            p[4] = rebuild(toks, new)
            lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            filled.append((os.path.basename(path), p[0], p[1], p[4]))
        result[path] = lines

    print('완역 %d줄 / 미완 %d줄 / 미지 조각 %d종' % (len(filled), len(partial), len(todo)))
    with io.open('work/phrase_todo.tsv', 'w', encoding='utf-8') as f:
        f.write('jp\tkr\t용례\n')
        for s, where in sorted(todo.items(), key=lambda kv: -len(kv[1])):
            f.write('%s\t\t%s x%d\n' % (s, '%s blk%s#%s' % where[0], len(where)))
    print('-> work/phrase_todo.tsv')
    for x in filled[:12]:
        print('   %s blk%s #%s  %s' % (x[0], x[1], x[2], x[3][:80]))

    if write:
        for path, lines in result.items():
            bak = path + '.bak_phrasemem'
            if not os.path.exists(bak):
                io.open(bak, 'w', encoding='utf-8', newline='').write(
                    io.open(path, encoding='utf-8', newline='').read())
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
        print('※ 파일에 기록했다')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
