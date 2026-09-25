"""Solve the master atlas base from identified glyphs.

Twelve glyphs were located in EE RAM by exact pixel match and then read off the
dumped cache texture by eye. Each character's SJIS code gives its slot via the
table at file 0x4389E0, so base = addr - slot*224. If the atlas really is a flat
slot-indexed array, every glyph must agree on one base.

Usage: python solve_base.py <SLPM_667.01>
"""
import struct
import sys
import collections

PER = 224

# (character, SJIS, RAM address found by pixel match)
GLYPHS = [
    ('づ', 0x82C3, 0x00b199b0),   # づ
    ('か', 0x82A9, 0x00b182f0),   # か
    ('ル', 0x8393, 0x00b202b0),   # ル
    ('決', 0x8C88, 0x00b4aef0),   # 決
    ('戦', 0x90ED, 0x00b79950),   # 戦
    ('武', 0x9590, 0x00ba7e70),   # 武
    ('将', 0x8FAB, 0x00b6bb10),   # 将
    ('登', 0x9375, 0x00b91970),   # 登
    ('録', 0x985E, 0x00bc4110),   # 録
    ('編', 0x95D2, 0x00bab830),   # 編
    ('集', 0x8F57, 0x00b67270),   # 集
    ('新', 0x9056, 0x00b71610),   # 新
]

d = open(sys.argv[1], 'rb').read()
BASE_TAB, N = 0x4389E0, 0x2c00
tab = struct.unpack('<%dH' % N, d[BASE_TAB:BASE_TAB + N * 2])


def idx(c):
    if 0x8100 <= c <= 0x9fff: return c - 0x8100
    if 0xe000 <= c <= 0xeaff: return c - 0xC100
    if 0xed00 <= c <= 0xeeff: return c - 0xC300
    return c - 0xC400


votes = collections.Counter()
print('%-4s %-7s %-8s %-6s %s' % ('ch', 'sjis', 'addr', 'slot', 'implied base'))
for ch, sjis, addr in GLYPHS:
    slot = tab[idx(sjis)]
    if slot == 0xffff:
        print('  %s SJIS %04x -> NOT MAPPED' % (ch, sjis))
        continue
    base = addr - slot * PER
    votes[base] += 1
    print('%-4s %04x    %#08x %-6d %#010x' % (ch, sjis, addr, slot, base))

print('\ndistinct implied bases: %d' % len(votes))
for b, n in votes.most_common():
    print('   %#010x  x%d' % (b, n))

if len(votes) == 1:
    base = next(iter(votes))
    print('\nUNANIMOUS -> atlas base = %#010x' % base)
    print('  atlas spans %#x .. %#x  (%d glyphs x %d B = %d B)'
          % (base, base + 3773 * PER, 3773, PER, 3773 * PER))
