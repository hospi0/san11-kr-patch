# -*- coding: utf-8 -*-
"""JSON에 적은 번역을 e4_*.tsv 의 kr 열에 넣는다 (세션26).

키는 `<파일>/<블록>/<인덱스>`. 값이 번역문이다.

안전장치 — 세션26에 실제로 한 번 사고를 냈기 때문에 넣었다(분기 대사 한 줄의 앞부분만 남기고
뒤를 통째로 날렸다. 되읽기도 빌드도 통과한다 — **아무도 안 잡아준다**):
  ① 이미 kr이 차 있는 줄은 건드리지 않는다(--force 없으면).
  ② 원문의 `{05}` 분기 구분자 개수가 번역문에서 줄면 거부한다.
  ③ `{V:…}`·`{BTN…}` 개수가 원문과 다르면 거부한다.
  ④ encode → decode 되읽기가 통과해야 한다(한자 잔존·토큰 오타를 여기서 잡는다).

Usage: python tools/apply_translations.py <json> [--write]
"""
import io
import json
import os
import re
import sys
import unicodedata as U
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from help_codec import decode, encode          # noqa: E402
from encoding import Codec                     # noqa: E402
from phrase_memory import split_tokens         # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
JPCH = re.compile(r"[぀-ヿ㐀-鿿]")


def check(jp, kr, codec):
    """(ok, 사유). 통과 못하면 그 줄은 쓰지 않는다."""
    jt, _ = split_tokens(jp)
    kt, _ = split_tokens(kr)
    a, b = Counter(jt), Counter(kt)
    if b['{05}'] < a['{05}']:
        return False, '{05} 분기 구분자가 %d → %d 로 줄었다' % (a['{05}'], b['{05}'])
    for t in set(list(a) + list(b)):
        if (t.startswith('{V:') or t.startswith('{BTN')) and a[t] != b[t]:
            return False, '%s 개수 %d → %d' % (t, a[t], b[t])
    body = ''.join(p for p in split_tokens(kr)[1])
    body = re.sub(r'\{01\}[CJS]', '', body)
    if JPCH.search(body):
        return False, '번역문에 일본어/한자가 남았다: %r' % JPCH.findall(body)[:5]
    try:
        enc = encode(U.normalize('NFC', kr), codec)
    except Exception as e:
        return False, '인코드 실패 %r' % e
    if U.normalize('NFC', decode(enc, codec)) != U.normalize('NFC', kr):
        return False, '되읽기 불일치'
    return True, ''


def main():
    src = sys.argv[1]
    write = '--write' in sys.argv
    force = '--force' in sys.argv
    data = json.load(io.open(src, encoding='utf-8'))
    codec = Codec(ELF)

    by_file = {}
    for key, kr in data.items():
        f, blk, idx = key.rsplit('/', 2)
        by_file.setdefault(f, {})[(blk, idx)] = kr

    ok = skip = fail = 0
    for f, table in by_file.items():
        path = os.path.join('work', f)
        raw = io.open(path, encoding='utf-8', newline='').read()
        lines = raw.split('\n')
        for i, ln in enumerate(lines):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit():
                continue
            k = (p[0], p[1])
            if k not in table:
                continue
            if p[4].strip() and not force:
                print('  건너뜀(이미 번역됨) %s blk%s #%s' % (f, p[0], p[1]))
                skip += 1
                continue
            good, why = check(p[3], table[k], codec)
            if not good:
                print('  ★거부 %s blk%s #%s — %s' % (f, p[0], p[1], why))
                fail += 1
                continue
            p[4] = table[k]
            lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            ok += 1
        if write:
            bak = path + '.bak_apply'
            if not os.path.exists(bak):
                io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print()
    print('적용 %d / 건너뜀 %d / 거부 %d  %s'
          % (ok, skip, fail, '(기록함)' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
