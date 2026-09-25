# -*- coding: utf-8 -*-
"""기존 e4_*.tsv 의 kr 표기를 **새 코덱 정규형**으로 재작성한다 (세션26).

배경:
  `help_codec.decode`가 `{01}C`/`{01}J` 매크로의 인수 2바이트를 이제 그대로 보존한다.
  그 결과 같은 바이트라도 표기가 달라진 줄이 32개 있다.
      옛: `{01}J{`      → 새: `{01}J{7b}`
      옛: `{01}J{N}`    → 새: `{01}J{0a}`
      옛: `{01}J{ESC09}`→ 새: `{01}J{1b}{09}`
  build_e4는 `decode(encode(kr)) == kr` 로 되읽기를 검증하므로, 표기가 옛 형태로 남아 있으면
  **그 줄이 통째로 원문(일본어)으로 되돌아간다**. 표기만 맞춰주면 된다.

안전성:
  치환값 = `decode(encode(kr))` 이므로 **인코드 결과 바이트가 같다는 것이 정의상 보장**된다.
  (실제로 아래에서 encode(old) == encode(new) 를 어서션으로 다시 확인한다.)

Usage: python tools/normalize_macro_args.py [--write]
"""
import io
import os
import sys
import unicodedata as U

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from help_codec import decode, encode          # noqa: E402
from encoding import Codec                     # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'


def main():
    write = '--write' in sys.argv
    codec = Codec(ELF)
    total = 0
    for f in sorted(os.listdir('work')):
        if not (f.startswith('e4_') and f.endswith('.tsv')):
            continue
        path = os.path.join('work', f)
        lines = io.open(path, encoding='utf-8', newline='').read().split('\n')
        changed = 0
        for i, ln in enumerate(lines):
            p = ln.rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
                continue
            old = U.normalize('NFC', p[4]).strip()
            try:
                enc = encode(old, codec)
            except Exception:
                continue                        # 인코드 자체가 안 되는 줄은 건드리지 않는다
            new = U.normalize('NFC', decode(enc, codec))
            if new == old:
                continue
            assert encode(new, codec) == enc, '바이트가 달라진다: %s %s' % (p[0], p[1])
            print('  %s blk%s #%s' % (f, p[0], p[1]))
            print('     옛: %r' % old[:90])
            print('     새: %r' % new[:90])
            p[4] = new
            lines[i] = '\t'.join(p) + ('\r' if ln.endswith('\r') else '')
            changed += 1
        if changed:
            total += changed
            print('%s: %d줄' % (f, changed))
            if write:
                if not os.path.exists(path + '.bak_macroarg'):
                    io.open(path + '.bak_macroarg', 'w', encoding='utf-8', newline='').write(
                        io.open(path, encoding='utf-8', newline='').read())
                io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print()
    print('합계 %d줄 %s' % (total, '재작성 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    main()
