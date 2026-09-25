"""Locate the officer/city name tables by known-name clustering.

The prose detector (text_census) cannot see these: a name like 曹操 is pure kanji
with no hiragana and only 2 chars long, so every signal that scanner relies on is
absent by construction. Known names are the crib instead -- we know exactly what
to look for, so we look for it directly.

Method: find every occurrence of ~40 famous San11 officers, then look for
REGIONS where many DISTINCT names cluster. A real name table is dense (dozens of
distinct names within a few KB) and usually laid out on a fixed stride. Scattered
single hits are prose mentions or coincidence.

The stride check matters -- per the standing lesson, a table must show structure
(regular spacing, ascending) and not merely a pile of hits. A cluster with no
consistent stride is reported as such rather than called a table.

Usage:
  python name_table.py <file> [--window 4096] [--min-distinct 8]
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Famous enough to be in any San11 scenario, spread across factions so a
# cluster of them is unambiguous.
NAMES = [
    '曹操', '劉備', '孫権', '諸葛亮', '関羽', '張飛', '呂布', '董卓', '袁紹',
    '袁術', '孫堅', '孫策', '周瑜', '司馬懿', '趙雲', '馬超', '黄忠', '魏延',
    '姜維', '龐統', '徐庶', '甘寧', '太史慈', '陸遜', '呂蒙', '張遼', '夏侯惇',
    '夏侯淵', '許褚', '典韋', '荀彧', '郭嘉', '賈詡', '張角', '公孫瓚', '劉表',
    '劉璋', '馬騰', '厳顔', '黄蓋', '程普', '魯粛', '貂蝉', '曹丕', '曹仁',
]
CITIES = ['洛陽', '長安', '許昌', '成都', '建業', '襄陽', '江陵', '寿春', '鄴',
          '下邳', '小沛', '陳留', '濮陽', '北平', '南皮', '晋陽', '武威']


def find_all(data, needle):
    out, start = [], 0
    while True:
        j = data.find(needle, start)
        if j < 0:
            return out
        out.append(j)
        start = j + 1


def cluster(hits, window):
    """hits = [(off, name)] sorted -> [(start, end, {name: count})]"""
    groups, cur = [], []
    for off, nm in hits:
        if cur and off - cur[-1][0] > window:
            groups.append(cur)
            cur = []
        cur.append((off, nm))
    if cur:
        groups.append(cur)
    return groups


def stride_of(offsets):
    """Most common gap between consecutive hits, and how dominant it is."""
    if len(offsets) < 3:
        return None, 0.0
    gaps = [b - a for a, b in zip(offsets, offsets[1:])]
    c = collections.Counter(gaps)
    top, n = c.most_common(1)[0]
    return top, n / len(gaps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--window', type=int, default=4096)
    ap.add_argument('--min-distinct', type=int, default=8)
    a = ap.parse_args()

    data = open(a.file, 'rb').read()
    for label, names in (('OFFICERS', NAMES), ('CITIES', CITIES)):
        hits = []
        skipped = []
        for nm in names:
            try:
                b = nm.encode('cp932')          # 龐 etc. are not in cp932 at all
            except UnicodeEncodeError:
                skipped.append(nm)
                continue
            for off in find_all(data, b):
                hits.append((off, nm))
        hits.sort()
        groups = cluster(hits, a.window)
        good = [g for g in groups
                if len({nm for _, nm in g}) >= a.min_distinct]
        good.sort(key=lambda g: -len({nm for _, nm in g}))

        print('=' * 78)
        print('%s in %s (%d B)' % (label, os.path.basename(a.file), len(data)))
        print('  probes=%d (%d unencodable in cp932: %s)'
              % (len(names) - len(skipped), len(skipped), ' '.join(skipped) or '-'))
        print('  total hits=%d  clusters(window=%d)=%d  dense=%d'
              % (len(hits), a.window, len(groups), len(good)))
        print('=' * 78)
        for g in good[:8]:
            offs = [o for o, _ in g]
            distinct = {nm for _, nm in g}
            st, frac = stride_of(offs)
            print('\n  region %#x..%#x  span=%d B  hits=%d  distinct=%d'
                  % (offs[0], offs[-1], offs[-1] - offs[0], len(g), len(distinct)))
            if st is not None:
                print('    dominant stride=%d B (%.0f%% of gaps) -> %s'
                      % (st, frac * 100,
                         'FIXED-STRIDE TABLE' if frac > 0.5 else
                         'irregular; not a fixed-stride table'))
            print('    names: %s' % ' '.join(sorted(distinct)[:14]))
            print('    first 6 @ %s' % [hex(o) for o in offs[:6]])
        if not good:
            print('\n  no dense cluster -- names appear scattered, not tabled')


if __name__ == '__main__':
    main()
