"""Locate UI strings in SLPM_667.01 and show the space actually available.

In-place editing means a replacement must fit the slot. What matters is not just
the original string length but how much null padding follows before the next
live string, so measure that rather than assume.

Usage: python find_ui_text.py <SLPM_667.01> [string ...]
"""
import sys

DEFAULT = ['つづきから', 'はじめから', 'チュートリアル', '決戦制覇モード',
           '武将登録・編集', 'オプション', '有名な戦いなどをプレイできます']


def readable(b):
    out, j = '', 0
    while j < len(b):
        c = b[j]
        if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef) and j + 1 < len(b):
            try:
                out += b[j:j + 2].decode('cp932'); j += 2; continue
            except Exception:
                pass
        if 0x20 <= c < 0x7f:
            out += chr(c)
        elif c == 0:
            out += '·'
        else:
            out += '[%02x]' % c
        j += 1
    return out


def main():
    d = open(sys.argv[1], 'rb').read()
    targets = sys.argv[2:] or DEFAULT
    for s in targets:
        pat = s.encode('cp932')
        hits = []
        p = d.find(pat)
        while p != -1:
            hits.append(p)
            p = d.find(pat, p + 1)
        print('\n=== %-18s (%d B)  hits=%d' % (s, len(pat), len(hits)))
        for p in hits[:4]:
            end = p + len(pat)
            pad = 0
            while end + pad < len(d) and d[end + pad] == 0:
                pad += 1
            # back up to the start of this slot: how much null precedes it
            pre = 0
            while p - pre - 1 >= 0 and d[p - pre - 1] == 0:
                pre += 1
            print('  file %#08x  VA %#08x   trailing NULs=%-4d  leading NULs=%d'
                  % (p, p + 0xFFF00, pad, pre))
            print('     capacity if slot ends at next string: %d B (%d full-width chars)'
                  % (len(pat) + pad, (len(pat) + pad) // 2))
            print('     ctx: %s' % readable(d[max(0, p - 24):end + min(pad, 8) + 16]))


main()
