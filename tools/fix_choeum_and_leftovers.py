# -*- coding: utf-8 -*-
"""번역문에 남은 **일본어 장음「ー」**와 매크로/조사 찌꺼기를 정리한다 (세션26).

찾은 방법
  `render_line.py`로 조립 결과까지 렌더한 뒤 가나가 남은 줄을 훑었다. 토큰만 지우고 보면
  멀쩡해 보이는데, **화면에 실제로 그려지는 모습**으로 보면 드러난다.

① 장음「ー」(22줄)
   「간다ーー！！」처럼 일본어 장음이 그대로 남았다. 앞 음절의 **중성을 따서 한글로 늘린다**
   (간다ー → 간다아 / 우랴ー → 우랴아). 그냥 지우면 감탄의 길이감이 사라진다.

② 매크로·조사 찌꺼기(3줄)
   `{01}C{88}{00}と` 에서 매크로만 지우고 뒤의 「と」를 안 지운 것,
   `{01}Cや`·`{01}Cふ` 처럼 **인수 1개짜리 어미 매크로**가 그대로 남은 것.
   ★인수 1개형은 종료바이트가 split_pad로 잘려나가 검출 정규식(인수 2개)에 안 걸렸다.

Usage: python tools/fix_choeum_and_leftovers.py [--write]
"""
import io
import os
import re
import sys

#

# 줄 단위 수동 수정(매크로/조사 찌꺼기).
MANUAL = {
    ('e4_dialogue.tsv', '24', '239'):
        '아, 아내를 맞이하는 것입니다{N}음, 그건 그렇지만{N}상대가 없어서야 어찌할 도리가……',
    ('e4_dialogue.tsv', '24', '995'):
        '?{N}{01}C{00}{00} 말인가?',
    ('e4_dialogue.tsv', '24', '1018'):
        '음……{N}밖을 다스리면, 안도 다스려집니다',
}


def drop_choeum(s):
    """장음「ー」를 없애고 **느낌표로 마무리**한다.

    「간다아」처럼 모음을 늘리면 한국어에선 어색하다(사용자 지시). 장음 자리는 빼고,
    뒤에 문장부호가 없을 때만 「！」를 붙인다 — 이미 「！！」가 있으면 그대로 둔다.
    """
    out = re.sub(r'ー+', '\x00', s)
    parts = out.split('\x00')
    res = parts[0]
    for nxt in parts[1:]:
        if not nxt or nxt[0] not in '！!？?…。.':
            res += '！'
        res += nxt
    return res


def main():
    write = '--write' in sys.argv
    n_long = n_man = 0
    for f in sorted(os.listdir('work')):
        if not (f.startswith('e4_') and f.endswith('.tsv')):
            continue
        path = os.path.join('work', f)
        raw = io.open(path, encoding='utf-8', newline='').read()
        lines = raw.split('\n')
        touched = False
        for i, ln in enumerate(lines):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
                continue
            new = p[4]
            key = (f, p[0], p[1])
            if key in MANUAL:
                new = MANUAL[key]
                n_man += 1
                print('[찌꺼기] %s blk%s #%s' % key)
                print('   전: %s' % p[4][:120])
                print('   후: %s' % new[:120])
            if 'ー' in new:
                before = new
                new = drop_choeum(new)
                if new != before:
                    n_long += 1
                    print('[장음] %s blk%s #%s' % key)
                    print('   전: %s' % before[:110])
                    print('   후: %s' % new[:110])
            if new != p[4]:
                p[4] = new
                lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
                touched = True
        if touched and write:
            bak = path + '.bak_choeum'
            if not os.path.exists(bak):
                io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print()
    print('장음 %d줄 / 찌꺼기 %d줄  %s'
          % (n_long, n_man, '수정 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
