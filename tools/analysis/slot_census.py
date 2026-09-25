"""Census of the 3,773 mapped slots: what characters does this game actually carry?

Drives the encoding design -- we need ~2,350 codepoints to repurpose for Hangul
(KS X 1001 완성형) and want to know exactly what we'd be giving up.

Usage: python slot_census.py <SLPM_667.01> [out.tsv]
"""
import struct
import sys
import unicodedata

BASE, N = 0x4389E0, 0x2c00


def idx(c):
    if 0x8100 <= c <= 0x9fff: return c - 0x8100
    if 0xe000 <= c <= 0xeaff: return c - 0xC100
    if 0xed00 <= c <= 0xeeff: return c - 0xC300
    return c - 0xC400


def sjis_ranges():
    """valid 2-byte SJIS: lead 0x81-0x9F / 0xE0-0xEF, trail 0x40-0x7E / 0x80-0xFC"""
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0)):
        for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            yield (lead << 8) | trail


def classify(ch, code):
    o = ord(ch)
    if 0x3040 <= o <= 0x309F: return 'hiragana'
    if 0x30A0 <= o <= 0x30FF: return 'katakana'
    if 0x4E00 <= o <= 0x9FFF: return 'kanji'
    if 0xFF01 <= o <= 0xFF5E: return 'fullwidth-alnum'
    if 0x2460 <= o <= 0x24FF or 0x3220 <= o <= 0x32FF: return 'enclosed'
    if 0x0391 <= o <= 0x03C9: return 'greek'
    if 0x0410 <= o <= 0x044F: return 'cyrillic'
    if unicodedata.category(ch).startswith('P') or unicodedata.category(ch).startswith('S'):
        return 'punct/symbol'
    return 'other'


def main():
    d = open(sys.argv[1], 'rb').read()
    tab = struct.unpack('<%dH' % N, d[BASE:BASE + N * 2])

    rows = []
    for code in sjis_ranges():
        i = idx(code)
        if not (0 <= i < N):
            continue
        slot = tab[i]
        if slot == 0xffff:
            continue
        try:
            ch = struct.pack('>H', code).decode('cp932')
        except Exception:
            ch = None
        rows.append((slot, code, ch, classify(ch, code) if ch else 'undecodable'))

    rows.sort()
    print('mapped slots: %d   slot range %d..%d' % (len(rows), rows[0][0], rows[-1][0]))
    dup = len(rows) - len({r[0] for r in rows})
    print('duplicate slots: %d' % dup)

    import collections
    cnt = collections.Counter(r[3] for r in rows)
    print('\n%-18s %6s   %s' % ('category', 'count', 'sample'))
    for cat, n in cnt.most_common():
        sample = ''.join(r[2] for r in rows if r[3] == cat and r[2])[:24]
        print('  %-16s %6d   %s' % (cat, n, sample))

    print('\nSJIS lead-byte spread:')
    lead = collections.Counter(r[1] >> 8 for r in rows)
    for lb in sorted(lead):
        print('  %02x: %4d' % (lb, lead[lb]))

    # what is NOT kana/kanji -- i.e. what we probably must keep
    keep = [r for r in rows if r[3] not in ('kanji', 'hiragana', 'katakana')]
    print('\nnon-kana/kanji (candidates to KEEP): %d' % len(keep))
    print('  ' + ''.join(r[2] for r in keep if r[2])[:200])

    sac = [r for r in rows if r[3] in ('kanji', 'hiragana', 'katakana')]
    print('\nkana+kanji (candidates to SACRIFICE for Hangul): %d' % len(sac))
    print('  need 2350 for KS X 1001 완성형 -> %s (surplus %d)'
          % ('ENOUGH' if len(sac) >= 2350 else 'NOT ENOUGH', len(sac) - 2350))

    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            f.write('slot\tsjis\tchar\tcategory\n')
            for slot, code, ch, cat in rows:
                f.write('%d\t%04X\t%s\t%s\n' % (slot, code, ch or '', cat))
        print('\nwrote %s' % sys.argv[2])


main()
