"""Recursive text census -- descends into nested LINK containers.

text_census.py measures each top-level entry as one blob. 96 of the text-bearing
entries are themselves LINK archives, so their text was counted but never
attributed to the sub-entry that actually holds it, and any sub-entry whose text
is diluted by a large binary sibling could be missed entirely.

Nested LINK headers use their OWN sector size -- idx=1015 is sector 0x10, not
0x800 -- so the parser must read it from the header rather than assume the
top-level value.

Reuses the calibrated detector from text_census (classify run>=8 + hiragana gate,
measure run>=3). See that module's docstring -- in particular round 4, which this
script is what exposed: recursion made the total DROP, proving the flat count was
counting 'ャャャャ' pixel filler as text.

Usage:
  python deep_census.py <archive> [--csv out.csv]
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from link import Link, sniff                                       # noqa: E402
from text_census import scan, RUN_CLASSIFY, RUN_MEASURE, HIRA_MIN  # noqa: E402

MAX_DEPTH = 4


def parse_link(b):
    """-> [(offset, size)] of sub-entries, or None if b is not a LINK archive."""
    if len(b) < 0x10 or b[:4] != b'LINK':
        return None
    count, sector, _z = struct.unpack('<III', b[4:16])
    if not count or not sector or sector & (sector - 1):
        return None                       # sector must be a power of two
    need = 0x10 + 8 * count
    if need > len(b):
        return None
    out = []
    for i in range(count):
        so, sz = struct.unpack('<II', b[0x10 + i * 8:0x18 + i * 8])
        off = so * sector
        if sz == 0:
            continue
        if off + sz > len(b):
            return None                   # not really a LINK, or truncated
        out.append((off, sz))
    return out


def walk(b, path, depth, out):
    """Emit (path, size, vol, kana, type) for every leaf that carries text."""
    subs = parse_link(b) if depth < MAX_DEPTH else None
    if subs:
        for i, (off, sz) in enumerate(subs):
            walk(b[off:off + sz], path + [i], depth + 1, out)
        return
    mass, longest, distinct, hira, zero_frac = scan(b, RUN_CLASSIFY)
    if zero_frac > 0.90 or mass < 16:
        return
    variety = distinct / mass if mass else 0.0
    if hira < HIRA_MIN or variety < 0.02:
        return
    vol, _, _, vhira, _ = scan(b, RUN_MEASURE)
    out.append(('.'.join(map(str, path)), len(b), vol, vhira, sniff(b[:32])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('archive')
    ap.add_argument('--csv')
    a = ap.parse_args()

    arc = Link(a.archive)
    leaves, n_nested, n_sub = [], 0, 0
    for i in range(arc.count):
        b = arc.read(i)
        if parse_link(b):
            n_nested += 1
            n_sub += len(parse_link(b))
        walk(b, [i], 0, leaves)

    leaves.sort(key=lambda r: -r[2])
    total = sum(r[2] for r in leaves)
    print('=' * 78)
    print('COVERAGE : %d top-level entries, %d of them nested LINK '
          '(%d sub-entries), recursion depth<=%d'
          % (arc.count, n_nested, n_sub, MAX_DEPTH))
    print('DETECTOR : classify run>=%d + hiragana>=%.2f, measure run>=%d'
          % (RUN_CLASSIFY, HIRA_MIN, RUN_MEASURE))
    print('RESULT   : %d text-bearing leaves' % len(leaves))
    print('TEXT VOL : %d JP chars (~%d bytes)' % (total, total * 2))
    print('=' * 78)
    print('\ntop 30 leaves (path = idx.sub.sub):')
    print('  %-18s %10s %9s %6s  %s' % ('path', 'size', 'chars', 'kana', 'type'))
    for p, sz, vol, ka, kind in leaves[:30]:
        print('  %-18s %10d %9d %6.3f  %s' % (p, sz, vol, ka, kind))

    if a.csv:
        with open(a.csv, 'w', encoding='utf-8') as f:
            f.write('path,size,chars,kana_frac,type\n')
            for p, sz, vol, ka, kind in leaves:
                f.write('%s,%d,%d,%.4f,%s\n' % (p, sz, vol, ka, kind))
        print('\nwrote %s (%d rows)' % (a.csv, len(leaves)))


if __name__ == '__main__':
    main()
