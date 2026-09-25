# -*- coding: utf-8 -*-
"""추출 게이트에 걸려 TSV에서 빠졌던 메시지를 **kr을 보존한 채** 되살린다 (세션26).

왜 필요한가
  `extract_e4.py`의 라운드트립 게이트는 "인코드하면 원본 바이트가 안 나오는 줄"을 버린다.
  그 판정 자체는 옳지만, 세션26 전까지는 **코덱이 `{01}C`/`{01}J` 매크로의 인수 2바이트를
  텍스트로 오해**해서 멀쩡한 줄 152개를 거짓 탈락시켰다. 그래서 그 줄들은 TSV에 아예 없었고,
  번역될 기회조차 없이 실기에서 일본어로 남았다(사용자 제보 「미번역」 7종의 진범).

  코덱을 고친 지금 다시 게이트를 돌리면 그 줄들이 통과한다. 하지만 `extract_e4.py`를 통째로
  다시 돌리면 **kr 열이 전부 날아간다**(9,276줄). 그래서 이 스크립트는 **빠진 index만 골라
  제자리에 끼워 넣는다**. 기존 줄은 jp 열까지 손대지 않는다.

Usage: python tools/recover_missing_rows.py [--write]
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ls11                                                     # noqa: E402
from help_codec import parse_offsets, segments, decode, encode  # noqa: E402
from build_help import split_pad                                # noqa: E402
from extract_e4 import GROUPS, _same                            # noqa: E402

E4 = 'work/entry4.bin'


def main():
    write = '--write' in sys.argv
    e4 = open(E4, 'rb').read()
    blocks = {i: ls11.decode_block(e4, i) for i in range(30)}

    total = 0
    for name, idxs, _desc in GROUPS:
        path = os.path.join('work', 'e4_%s.tsv' % name)
        raw = io.open(path, encoding='utf-8', newline='').read()
        lines = raw.split('\n')

        have = set()
        first_data = None
        for i, ln in enumerate(lines):
            p = ln.split('\t')
            if len(p) >= 5 and p[0].isdigit():
                have.add((int(p[0]), int(p[1])))
                if first_data is None:
                    first_data = i

        new_rows = []
        for bi in idxs:
            d = blocks[bi]
            for k, seg in enumerate(segments(d, parse_offsets(d))):
                if (bi, k) in have:
                    continue
                pre, body, suf = split_pad(seg)
                if not body:
                    continue                                    # 패딩뿐인 슬롯 = 번역 대상 아님
                try:
                    jp = decode(body)
                    if not _same(pre + encode(jp, None, jp_passthrough=True) + suf, seg):
                        continue                                # 아직도 게이트 실패 = 손대면 안 된다
                except Exception:
                    continue
                new_rows.append((bi, k, len(seg), jp))

        if not new_rows:
            print('%-22s 추가 없음' % os.path.basename(path))
            continue

        # 기존 줄 사이 올바른 자리에 끼워 넣는다(정렬 유지 = diff 보기 쉽게).
        out, ptr = lines[:first_data], 0
        merged = sorted(
            [(int(l.split('\t')[0]), int(l.split('\t')[1]), l) for l in lines[first_data:]
             if len(l.split('\t')) >= 5 and l.split('\t')[0].isdigit()]
            + [(b, k, '%d\t%d\t%d\t%s\t' % (b, k, n, jp.replace('\t', ' ')))
               for b, k, n, jp in new_rows],
            key=lambda x: (idxs.index(x[0]), x[1]))
        out += [m[2] for m in merged]
        tail = [l for l in lines[first_data:]
                if not (len(l.split('\t')) >= 5 and l.split('\t')[0].isdigit())]
        out += tail
        ptr = len(new_rows)

        print('%-22s +%d줄' % (os.path.basename(path), ptr))
        for b, k, n, jp in new_rows[:6]:
            print('     blk%-2d #%-4d %r' % (b, k, jp[:70]))
        total += ptr
        if write:
            bak = path + '.bak_recover'
            if not os.path.exists(bak):
                io.open(bak, 'w', encoding='utf-8', newline='').write(raw)
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(out))

    print()
    print('합계 %d줄 %s' % (total, '복원 완료' if write else '(--write 를 주면 실제로 씀)'))


if __name__ == '__main__':
    main()
