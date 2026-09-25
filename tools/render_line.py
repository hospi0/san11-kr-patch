# -*- coding: utf-8 -*-
"""메시지를 **화면에 뜰 모습**으로 렌더한다 (세션26).

왜 필요한가
  실기 화면의 문장은 원문에 통짜로 존재하지 않는다. 「すみません / 聞いていませんでした」는
  `{01}C]{01}`(=すみません) + `聞いてい` + `{01}C{15}{01}`(=ませんでした) 로 **조립**된 결과다.
  그래서 스크린샷 문구로 TSV를 grep하면 "원문 못 찾음"이 나오고, 번역이 됐는지 안 됐는지
  판단을 그르친다(세션26에 실제로 그럴 뻔했다).

  이 렌더러는 `{01}C` 매크로를 조립 테이블의 대표 변형으로 치환해 실제 출력에 가깝게 만든다.
  ⚠️성격·성별 분기 중 **하나만** 고른 근사치다. 정확한 분기 재현이 아니라 대조용이다.

Usage:
  python tools/render_line.py <파일> <블록> <인덱스>
  python tools/render_line.py --grep "설득력"        # 렌더 결과에서 검색
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from help_codec import parse_offsets, segments, decode      # noqa: E402
from encoding import Codec                                  # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
MAC = re.compile(r'\{01\}C(\{[0-9a-f]{2}\}|[^{])(\{[0-9a-f]{2}\}|[^{])')
TOK = re.compile(r"\{(?:V:[0-9a-f]{2,6}|BTN[0-9a-f]{2}|ESC[0-9a-f]{2}|[0-9a-f]{2})\}")


def _byte(tok):
    if tok.startswith('{'):
        return int(tok[1:-1], 16)
    b = tok.encode('cp932')
    return b[0] if len(b) == 1 else None


def load_table(kr=True):
    """part1 메시지 -> 대표 단어(첫 번째 실텍스트 조각)."""
    path = 'work/entry3_kr.bin' if kr and os.path.exists('work/entry3_kr.bin') else 'work/entry3.bin'
    d = open(path, 'rb').read()
    codec = Codec(ELF)
    out = {}
    for i, seg in enumerate(segments(d, parse_offsets(d))):
        if i >= 416:
            break
        s = decode(seg.strip(b'\x05\x00'), codec)
        for w in re.split(r"\{[^}]*\}", s):
            w = re.sub(r'^(?:[=%+][0-9]+|[}|&])*', '', w.strip())
            if w and not w.isdigit() and not re.fullmatch(r'[A-Za-z][\x20-\x7e]?', w):
                out[i] = w
                break
    return out


def render(text, table):
    def sub(m):
        lo, bank = _byte(m.group(1)), _byte(m.group(2))
        if lo is None or bank is None:
            return ''
        return table.get(bank * 256 + lo, '')
    s = MAC.sub(sub, text)
    # ★`{01}J`는 **인수 2바이트까지** 통째로 지워야 한다. 라벨 인수 글자를 남기면
    #   렌더 결과에 가나가 섞여 「번역이 덜 됐다」는 거짓 경보가 쏟아진다.
    s = re.sub(r'\{01\}J(?:\{[0-9a-f]{2}\}|[^{])(?:\{[0-9a-f]{2}\}|[^{])?', '', s)
    s = re.sub(r'\{01\}S', '', s)
    s = TOK.sub('', s)
    return s.replace('{N}', '\n')


def main():
    table = load_table()
    if sys.argv[1] == '--grep':
        needle = sys.argv[2]
        for f in sorted(os.listdir('work')):
            if not (f.startswith('e4_') and f.endswith('.tsv')):
                continue
            for ln in io.open(os.path.join('work', f), encoding='utf-8'):
                p = ln.rstrip('\n').rstrip('\r').split('\t')
                if len(p) < 5 or not p[0].isdigit():
                    continue
                for col, lab in ((3, 'JP'), (4, 'KR')):
                    if not p[col].strip():
                        continue
                    r = render(p[col], table)
                    if needle in r:
                        print('%s blk%s #%s [%s]' % (f, p[0], p[1], lab))
                        print('   ' + r.replace('\n', '\n   '))
                        print()
        return
    f, blk, idx = sys.argv[1], sys.argv[2], sys.argv[3]
    for ln in io.open(os.path.join('work', f), encoding='utf-8'):
        p = ln.rstrip('\n').rstrip('\r').split('\t')
        if len(p) >= 5 and p[0] == blk and p[1] == idx:
            print('--- JP 렌더 ---'); print(render(p[3], table))
            print('--- KR 렌더 ---'); print(render(p[4], table) if p[4].strip() else '(미번역)')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
