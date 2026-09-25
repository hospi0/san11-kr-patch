# -*- coding: utf-8 -*-
"""미번역 줄을 **매크로 해설과 함께** 보여준다 (세션26).

번역할 때 `{01}C…` 매크로를 살릴지 지울지가 매번 헷갈린다. 판정 기준은 하나다:

  · **단어형**(PART1_SAFE_INDICES에 있음) = 1인칭·2인칭·호칭·감탄사 → 이미 한글이므로 **보존**
  · **어미형**(그 외)                     = 일본어 활용어미가 그대로 나온다 → **지우고**
                                            한국어 어미를 번역문 안에 직접 써 넣는다
                                            (한국어는 어간을 잘라 활용시킬 수 없다)

인덱스 = `01 43 lo bank` 의 **bank*256 + lo**. 종료바이트가 곧 뱅크다.

Usage: python tools/show_untranslated.py [블록번호 ...]
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from help_codec import parse_offsets, segments, decode      # noqa: E402
from build_help import PART1_SAFE_INDICES                   # noqa: E402
from encoding import Codec                                  # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
MAC = re.compile(r'\{01\}C(\{[0-9a-f]{2}\}|[^{])(\{[0-9a-f]{2}\}|[^{])')
TOK = re.compile(r"\{(?:V:[0-9a-f]{2,6}|N|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")
JPCH = re.compile(r"[぀-ヿ㐀-鿿]")


def _byte(tok):
    if tok.startswith('{'):
        return int(tok[1:-1], 16)
    b = tok.encode('cp932')
    return b[0] if len(b) == 1 else None


def load_table():
    """part1 메시지 -> 그 안의 단어들(한글화된 entry3_kr 기준)."""
    path = 'work/entry3_kr.bin' if os.path.exists('work/entry3_kr.bin') else 'work/entry3.bin'
    d = open(path, 'rb').read()
    codec = Codec(ELF)
    out = {}
    for i, seg in enumerate(segments(d, parse_offsets(d))):
        if i >= 416:
            break
        s = decode(seg.strip(b'\x05\x00'), codec)
        words = [w for w in re.split(r"\{[^}]*\}", s) if w.strip() and not w.strip().isdigit()]
        out[i] = words
    return out


def main():
    want = {int(a) for a in sys.argv[1:] if a.isdigit()}
    table = load_table()
    for f in sorted(os.listdir('work')):
        if not (f.startswith('e4_') and f.endswith('.tsv')) or 'bio' in f:
            continue
        for ln in io.open(os.path.join('work', f), encoding='utf-8'):
            p = ln.rstrip('\n').rstrip('\r').split('\t')
            if len(p) < 5 or not p[0].isdigit() or p[4].strip():
                continue
            if want and int(p[0]) not in want:
                continue
            body = MAC.sub('', TOK.sub('', p[3]))
            if not JPCH.search(body):
                continue                       # 번역할 텍스트 없음(제어행)
            print('=== %s blk%s #%s' % (f, p[0], p[1]))
            print('JP: %s' % p[3])
            seen = set()
            for m in MAC.finditer(p[3]):
                lo, bank = _byte(m.group(1)), _byte(m.group(2))
                if lo is None or bank is None or m.group(0) in seen:
                    continue
                seen.add(m.group(0))
                idx = bank * 256 + lo
                kind = '단어형·보존' if idx in PART1_SAFE_INDICES else '어미형·삭제'
                print('    %-16s idx=%-4d %-8s %s'
                      % (m.group(0), idx, kind, ' / '.join(table.get(idx, []))[:70]))
            print()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
