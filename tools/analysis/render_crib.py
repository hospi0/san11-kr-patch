"""Render candidate atlas cells as ASCII and check against known cribs."""
import struct, sys
import numpy as np

ENT = int(sys.argv[1]) if len(sys.argv) > 1 else 24
HDR = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x78
PER = int(sys.argv[3]) if len(sys.argv) > 3 else 72
W = int(sys.argv[4]) if len(sys.argv) > 4 else 24
H = int(sys.argv[5]) if len(sys.argv) > 5 else 24

f = open('s11pkres.bin', 'rb')
f.seek(4)
n = struct.unpack('<I', f.read(4))[0]
f.seek(0x10)
tbl = [struct.unpack('<II', f.read(8)) for _ in range(n)]
a, b = tbl[ENT]
f.seek(a * 0x800)
d = f.read(b)
print('entry idx=%d size=%d  hdr=%#x per=%d cell=%dx%d' % (ENT, b, HDR, PER, W, H))
print('head:', d[:0x80].hex(' '))
print()

rb = PER // H


def cell(gi):
    o = HDR + gi * PER
    g = d[o:o + PER]
    if len(g) < PER:
        return None
    bits = np.unpackbits(np.frombuffer(g, np.uint8)).reshape(H, rb * 8)[:, :W]
    return bits


# cribs: slot -> expected char
CRIB = {0: 'ideographic space (MUST be blank)',
        61: 'zero 0',
        407: 'ichi 一 (one horizontal bar)',
        1258: 'kuni 国',
        2491: 'nichi 日'}

for s, desc in CRIB.items():
    c = cell(s)
    print('--- slot %d : %s' % (s, desc))
    if c is None:
        print('    <out of range>')
        continue
    for row in c:
        print('    ' + ''.join('#' if v else '.' for v in row))
    print()
