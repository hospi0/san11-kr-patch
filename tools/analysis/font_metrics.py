"""Measure the game font's real glyph metrics, so Hangul can be drawn to match.

Rendering Hangul "as large as fits" is wrong: it makes every syllable a
different size and leaves no margin, unlike the game's own glyphs. Instead
measure the ink box the original font actually uses inside its 20x20 cell and
target that.

Reads the atlas straight out of s11pkres.bin (offset 0x49810, 224 B/glyph).

Usage: python font_metrics.py <s11pkres.bin> [SLPM_667.01]
"""
import struct
import sys

import numpy as np

ATLAS = 0x49810
PER, PIX = 224, 200
G = 3773


def glyphs(path):
    f = open(path, 'rb')
    f.seek(ATLAS)
    raw = np.frombuffer(f.read(G * PER), np.uint8).reshape(G, PER)
    b = raw[:, :PIX].reshape(G, 20, 10)
    px = np.empty((G, 20, 20), np.uint8)
    px[:, :, 0::2] = b & 0x0f
    px[:, :, 1::2] = b >> 4
    return px


px = glyphs(sys.argv[1])
ink = px != 0
has = ink.any(axis=(1, 2))
print('glyphs: %d   non-blank: %d' % (G, int(has.sum())))

tops, bots, lefts, rights = [], [], [], []
for i in np.nonzero(has)[0]:
    rows = np.nonzero(ink[i].any(axis=1))[0]
    cols = np.nonzero(ink[i].any(axis=0))[0]
    tops.append(rows[0]); bots.append(rows[-1])
    lefts.append(cols[0]); rights.append(cols[-1])
tops, bots = np.array(tops), np.array(bots)
lefts, rights = np.array(lefts), np.array(rights)

print('\nink bounding box across all glyphs (0-based, inside the 20x20 cell):')
for name, arr in (('top', tops), ('bottom', bots), ('left', lefts), ('right', rights)):
    print('  %-7s min=%2d  p10=%2d  median=%2d  p90=%2d  max=%2d'
          % (name, arr.min(), np.percentile(arr, 10), np.median(arr),
             np.percentile(arr, 90), arr.max()))

h = bots - tops + 1
w = rights - lefts + 1
print('\nink height: median=%d  p90=%d  max=%d' % (np.median(h), np.percentile(h, 90), h.max()))
print('ink width : median=%d  p90=%d  max=%d' % (np.median(w), np.percentile(w, 90), w.max()))

# The "em box" a dense square kanji fills = the size Hangul should match.
dense = np.nonzero(has & (ink.sum(axis=(1, 2)) > 200))[0]
print('\ndense glyphs (ink>200px): %d' % len(dense))
dt = np.array([np.nonzero(ink[i].any(axis=1))[0][0] for i in dense])
db = np.array([np.nonzero(ink[i].any(axis=1))[0][-1] for i in dense])
dl = np.array([np.nonzero(ink[i].any(axis=0))[0][0] for i in dense])
dr = np.array([np.nonzero(ink[i].any(axis=0))[0][-1] for i in dense])
print('  their box: top=%d bottom=%d left=%d right=%d  -> %dx%d'
      % (np.median(dt), np.median(db), np.median(dl), np.median(dr),
         np.median(dr) - np.median(dl) + 1, np.median(db) - np.median(dt) + 1))

print('\ngrey-level histogram (4bpp index usage):')
hist = np.bincount(px[has].ravel(), minlength=16)
for v in range(16):
    print('  %2d: %8d %s' % (v, hist[v], '#' * int(40 * hist[v] / hist.max())))
