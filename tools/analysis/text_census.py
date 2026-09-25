"""Full census of text-bearing entries in s11pkres.bin. Scans ALL entries.

Why the detector looks like this
--------------------------------
The obvious metric -- "how many valid SJIS chars are in this entry" -- is pure
noise. ~13% of random byte positions start a valid SJIS pair that cp932 will
happily decode, so the 870 KB font atlas (raw 4bpp pixels, zero text) scores
40,409 "characters". An earlier version of this script reported 7,315 of 9,383
entries as text-bearing and 19.9M characters. All noise.

Calibrated against controls instead of guessed thresholds (2026-07-16).

Round 1 -- ink. Runs of >=8 consecutive valid SJIS chars are ~0.13^8 by chance,
so raw 4bpp/binary controls land on exactly 0 mass:
    idx=2  font atlas, raw 4bpp      max run 4    mass>=8: 0
    idx=70 binary blob               max run 4    mass>=8: 0
MASS8 (chars living in runs of >=8) is therefore the ink signal. Plain char
count is meaningless and is never reported as volume.

Round 2 -- mass8 alone still lies. 8bpp image data has different byte statistics
than the 4bpp controls: smooth/repeating pixels DO form long runs. Decoding the
hits is what settled it -- noise spells obscure kanji that never co-occur, and
repeated pixel patterns spell literal filler:
    idx=676 GCOL  mass 20,116  '屁栢嚶劒禦嚥利漉剔吏貯囎剱'   <- background CG
    idx=1015      mass  8,196  '末摩末摩末摩末摩末摩...'      <- pixels
    idx=91        mass  6,167  '珥珥珥珥珥珥珥...'            <- pixels
    idx=2518      mass  6,015  '澵渧鳬瀅澵渹鈿粭鉗鉗砌'        <- pixels
Real text reads as Japanese: idx=21 '劉表、劉虞と友好関係にあり、董卓、袁術と
激しく対立している。領地は陳留。', idx=24 '高祖・劉邦が秦・楚を倒して興した'.

KANA FRACTION separates them cleanly, because image bytes scatter uniformly over
the JIS table and essentially never land on hiragana, while real Japanese prose
is ~50% kana:
    noise  (676, 675, 2518, 2582, 2596, 1015, 91)   0.002 - 0.034
    real   (24, 21, 13, 6, 5)                       0.467 - 0.537
    real   (3, event dialog broken up by opcodes)   0.266
A >10x gap with nothing in between -> threshold 0.15.

(Round 4 below supersedes this: kana was still too weak. Final constraints are
  1. ink     -- mass8 > 0
  2. blank   -- mostly-0x00 payloads vetoed regardless of ink
  3. hiragana-- hira/particle fraction >= HIRA_MIN; kills ALL image-data noise.
                variety is kept only as a weak secondary veto -- it cannot do
                this job: GCOL noise scores 0.060, real prose idx=5 only 0.088.)

Round 3 -- run>=8 undercounts badly. Short records never reach 8 chars:
idx=24's own title '国力向上の基本' is 7. Measuring idx=24 at run>=3 finds 6,379
chars vs 1,290 at run>=8 -- a 4.8x undercount. The kana gate still separates at
run>=3 (noise 0.008-0.048 vs real 0.558-0.861), so the threshold is only needed
for robust CLASSIFICATION, not for measurement. Hence two passes:
    classify at RUN_CLASSIFY=8 (kana-gated, robust)
    measure  at RUN_MEASURE=3  (catches short records)
Event dialog is the reason classification cannot also drop to 3: idx=3 is
opcode-interleaved, so its kana fraction falls to 0.047 at run>=3 and it would
be thrown out, while at run>=8 it reads a clean 0.266.

Round 4 -- KATAKANA IS NOT A VALID SIGNAL. Recursing into nested LINK made the
total DROP by 100,006 chars, which should be impossible if the flat count were
honest. It wasn't: idx=2050's "text" is 'ャャャャャャャ...' -- one katakana
repeated. kana_frac scores that 1.0, because ャ IS kana. The nested-LINK text in
the flat census was ~100K chars of pixel filler, and the recursive number is the
correct one.

Hiragana (+ common particles) is the signal that cannot be faked, because image
bytes never land in the hiragana block and repeated filler is a single codepoint:
    noise (2050 'ャャャ', 676 GCOL, 1015, 2518)  hira 0.000  particles 0.000
    real  (21, 13, 5, 24)                        hira 0.244-0.427  part 0.174-0.292
Exactly 0.000 vs 0.24+ -> threshold 0.05. Variety cannot substitute: GCOL noise
has variety 0.060, ABOVE real prose idx=5 at 0.088's neighbourhood.

CAVEATS -- the reported volume is a FLOOR, not a total. Invisible by design:
1. Pure-kanji name tables (曹操/劉備): no hiragana, short runs. Use known-name
   search instead (search_names.py).
2. UI text in SLPM_667.01 -- not in this archive at all.
3. HALF-WIDTH KATAKANA (single byte 0xA1-0xDF). idx=3 is built from 'ﾃﾞｽ'/'ﾀﾞｿﾞ'
   fragments plus terms like 伯母様/兄者 -- an honorific/sentence-ending assembly
   table, NOT event dialogue as previously documented. This scanner only sees
   2-byte SJIS, so every half-width string is missed.

Coverage (N scanned, filters, thresholds) is printed with every run. A sample
is never reported as a total.

Usage:
  python text_census.py <archive> [--min-mass N] [--csv out.csv]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from link import Link, sniff                                  # noqa: E402

RUN_CLASSIFY = 8     # calibrated: raw-binary controls give 0 mass at >=8
RUN_MEASURE = 3      # short records ('国力向上の基本' = 7 chars) need this
HIRA_MIN = 0.05      # calibrated: noise EXACTLY 0.000, real prose 0.244-0.427
KANA_MIN = HIRA_MIN  # back-compat alias
RUN_MIN = RUN_CLASSIFY

# Hiragana particles that dominate any real Japanese sentence. Used as a second
# independent positive signal -- noise scores exactly 0.000 on these too.
PARTICLES = frozenset(
    (c.encode('cp932')[0] << 8) | c.encode('cp932')[1]
    for c in 'のにはをがでとたしてるいなも')


def _is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def _is_trail(b):
    return 0x40 <= b <= 0x7E or 0x80 <= b <= 0xFC


def _is_hira(code):
    """Hiragana only. Katakana is NOT usable as the signal -- see round 4."""
    return 0x829F <= code <= 0x82F1


def scan(b, run_min=RUN_MIN):
    """-> (mass, max_run, distinct_in_runs, hira_frac, zero_frac)

    mass = number of SJIS chars that live in a run of >= run_min chars.
    Only those chars count as text; isolated hits are noise by construction.
    hira_frac counts hiragana + common particles: the signal image data cannot fake.
    """
    n = len(b)
    if n < 16:
        return 0, 0, 0, 0.0, 1.0
    zeros = b.count(0)
    mass = longest = hira = 0
    chars = set()
    cur = []
    i = 0

    def flush():
        nonlocal mass, longest, hira
        if len(cur) >= run_min:
            mass += len(cur)
            hira += sum(1 for c in cur if _is_hira(c) or c in PARTICLES)
            chars.update(cur)
        longest = max(longest, len(cur))
        cur.clear()

    while i < n - 1:
        if _is_lead(b[i]) and _is_trail(b[i + 1]):
            try:
                b[i:i + 2].decode('cp932')
            except Exception:
                i += 1
                flush()
                continue
            cur.append((b[i] << 8) | b[i + 1])
            i += 2
        else:
            flush()
            i += 1
    flush()
    return mass, longest, len(chars), (hira / mass if mass else 0.0), zeros / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('archive')
    ap.add_argument('--min-mass', type=int, default=16,
                    help='minimum chars in long runs to call an entry text')
    ap.add_argument('--csv')
    a = ap.parse_args()

    arc = Link(a.archive)
    hits, by_type = [], {}
    n_blank = n_noink = 0

    n_noise = 0
    for i in range(arc.count):
        b = arc.read(i)
        mass, longest, distinct, hira, zero_frac = scan(b, RUN_CLASSIFY)
        variety = distinct / mass if mass else 0.0
        if zero_frac > 0.90:
            n_blank += 1
            continue
        if mass < a.min_mass:
            n_noink += 1
            continue
        if hira < HIRA_MIN or variety < 0.02:
            n_noise += 1                      # image data aliasing into SJIS
            continue
        # entry is real text -> re-measure at the low threshold to catch the
        # short records that RUN_CLASSIFY structurally misses
        vol, _, _, vhira, _ = scan(b, RUN_MEASURE)
        kind = sniff(b[:32])
        hits.append((i, len(b), vol, longest, vhira, variety, kind))
        by_type[kind] = by_type.get(kind, 0) + 1

    hits.sort(key=lambda h: -h[2])
    total_mass = sum(h[2] for h in hits)

    print('=' * 78)
    print('COVERAGE : scanned %d / %d entries (100%%), %d B payload'
          % (arc.count, arc.count, sum(e[1] for e in arc.entries)))
    print('DETECTOR : classify at run>=%d + hiragana>=%.2f, measure at run>=%d'
          % (RUN_CLASSIFY, HIRA_MIN, RUN_MEASURE))
    print('FILTERS  : min_mass=%d, zero_frac<=0.90, variety>=0.02' % a.min_mass)
    print('CONTROLS : idx=2 atlas mass 0 | GCOL/2050 hira 0.000 | prose hira 0.24+')
    print('RESULT   : %d text-bearing | %d blank | %d no-ink | %d rejected as '
          'image-noise' % (len(hits), n_blank, n_noink, n_noise))
    print('TEXT VOL : %d JP chars (~%d bytes)' % (total_mass, total_mass * 2))
    print('           ^ PROSE FLOOR. Excludes name tables (no kana) and all')
    print('             UI text in SLPM_667.01 (not in this archive).')
    print('=' * 78)

    print('\nby container type:')
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        m = sum(h[2] for h in hits if h[6] == k)
        print('  %-28s %5d entries  %9d chars' % (k, v, m))

    print('\ntop 40 by text mass:')
    print('  %5s %10s %9s %6s %6s %7s  %s'
          % ('idx', 'size', 'mass', 'maxrun', 'hira', 'variety', 'type'))
    for i, sz, mass, lo, ka, va, kind in hits[:40]:
        print('  %5d %10d %9d %6d %6.3f %7.3f  %s' % (i, sz, mass, lo, ka, va, kind))

    if a.csv:
        with open(a.csv, 'w', encoding='utf-8') as f:
            f.write('idx,size,mass,max_run,kana_frac,variety,type\n')
            for row in hits:
                f.write('%d,%d,%d,%d,%.4f,%.4f,%s\n' % row)
        print('\nwrote %s (%d rows)' % (a.csv, len(hits)))


if __name__ == '__main__':
    main()
