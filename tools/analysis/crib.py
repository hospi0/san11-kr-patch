import struct, sys

d = open('SLPM_667.01', 'rb').read()
BASE = 0x4389E0
N = 0x2c00


def idx(c):
    if 0x8100 <= c <= 0x9fff: return c - 0x8100
    if 0xe000 <= c <= 0xeaff: return c - 0xC100
    if 0xed00 <= c <= 0xeeff: return c - 0xC300
    return c - 0xC400


tab = struct.unpack('<%dH' % N, d[BASE:BASE + N * 2])


def slot(c):
    i = idx(c)
    return tab[i] if 0 <= i < N else None


inv = {}
for c in list(range(0x8100, 0xa000)) + list(range(0xe000, 0xf000)):
    i = idx(c)
    if 0 <= i < N and tab[i] != 0xffff:
        inv[tab[i]] = c

out = []
out.append('slots 0..11:')
for s in range(12):
    c = inv.get(s)
    try:
        ch = struct.pack('>H', c).decode('cp932')
    except Exception:
        ch = '?'
    out.append('  slot%-4d SJIS %04x  %s' % (s, c, ch))

out.append('')
out.append('CRIB glyphs:')
for name, c in [('space', 0x8140), ('ichi', 0x88ea), ('zero', 0x824f),
                ('kuni', 0x8d91), ('nichi', 0x93fa), ('san', 0x8e4f)]:
    try:
        ch = struct.pack('>H', c).decode('cp932')
    except Exception:
        ch = '?'
    out.append('  %-7s SJIS %04x %s -> slot %s' % (name, c, ch, slot(c)))

out.append('')
seq = [(c, tab[idx(c)]) for c in range(0x8100, 0xf000)
       if 0 <= idx(c) < N and tab[idx(c)] != 0xffff]
mono = all(seq[i][1] < seq[i + 1][1] for i in range(len(seq) - 1))
out.append('ordered-by-SJIS: %s  (n=%d, first=%04x last=%04x)'
           % (mono, len(seq), seq[0][0], seq[-1][0]))

txt = '\n'.join(out)
open(sys.argv[1], 'w', encoding='utf-8').write(txt)
print(txt)
