"""LINK archive reader/writer for s11pkres.bin (KOEI's San11/Nobunaga format).

Format (fully decoded, docs/01):
  0x00  "LINK"
  0x04  u32  entry count            (9383 in the retail JP disc)
  0x08  u32  sector size            (0x800)
  0x0c  u32  0
  0x10  entry[count], 8 B each: (sector_offset:u32, byte_size:u32)
        file offset = sector_offset * sector_size
There is no filename table -- entries are identified by index.

Rebuild keeps the TOTAL FILE SIZE identical, which is what lets the final patch
overwrite s11pkres.bin inside the ISO in place (tools/iso.py patch). Inside that
budget entries may move and grow freely, because the table stores each entry's
sector offset explicitly. Slack at the tail is the growth budget; rebuild refuses
rather than silently producing a differently-sized archive.

Usage:
  python link.py list    <archive> [n]        # first n entries (default 40)
  python link.py info    <archive> <idx>      # one entry: offsets, size, sniff
  python link.py extract <archive> <idx> <out>
  python link.py dumpall <archive> <outdir>   # every entry -> outdir/NNNN.bin
  python link.py rebuild <archive> <dir> <out>  # dir/NNNN.bin overrides
  python link.py roundtrip <archive>          # rebuild with no overrides, diff
"""
import hashlib
import os
import struct
import sys

HDR = 0x10
ENT = 8


class Link:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        h = self.f.read(HDR)
        if h[:4] != b'LINK':
            raise SystemExit('not a LINK archive (magic %r)' % h[:4])
        self.count, self.sector, _z = struct.unpack('<III', h[4:16])
        tab = self.f.read(ENT * self.count)
        self.entries = [struct.unpack('<II', tab[i * ENT:(i + 1) * ENT])
                        for i in range(self.count)]
        self.size = os.path.getsize(path)

    def offset(self, i):
        return self.entries[i][0] * self.sector

    def read(self, i):
        off, size = self.offset(i), self.entries[i][1]
        self.f.seek(off)
        return self.f.read(size)

    def table_end(self):
        return HDR + ENT * self.count

    def data_start(self):
        """Lowest byte a payload may occupy; the table must not be overwritten."""
        return min(self.offset(i) for i in range(self.count))


def sniff(b):
    """Best-effort type tag. The 39 known resource kinds are in docs/01."""
    if len(b) < 4:
        return 'tiny'
    m4 = b[:4]
    if m4 == b'LINK':
        return 'LINK (nested)'
    if m4 == b'\x00\x00\xfe\xff':
        tag = b[0x08:0x12]
        return 'container %s' % tag.decode('latin1', 'replace').strip('\x00')
    for tag in (b'FCVD', b'KSEF', b'KM01', b'TOD2', b'GCOL', b'K3ST', b'AIMG',
                b'NUNO', b'IECS'):
        if m4 == tag:
            return tag.decode()
    return m4.hex()


def rebuild(src, override_dir, out):
    """Repack, honouring overrides, into a file of the ORIGINAL total size."""
    a = Link(src)
    payloads = {}
    if override_dir:
        for name in os.listdir(override_dir):
            stem, ext = os.path.splitext(name)
            if ext != '.bin' or not stem.isdigit():
                continue
            i = int(stem)
            if not 0 <= i < a.count:
                raise SystemExit('override %s: index out of range' % name)
            payloads[i] = open(os.path.join(override_dir, name), 'rb').read()

    # Entries keep their original order; only their offsets are recomputed.
    # Starting the data at the original first-entry offset preserves whatever
    # alignment/padding the game's loader may expect ahead of it.
    cur = a.data_start()
    if cur < a.table_end():
        raise SystemExit('table (%d B) overlaps first payload (%d)'
                         % (a.table_end(), cur))
    new_ents, blobs = [], []
    for i in range(a.count):
        data = payloads.get(i)
        if data is None:
            data = a.read(i)
        if cur % a.sector:
            raise SystemExit('internal: entry %d not sector aligned' % i)
        new_ents.append((cur // a.sector, len(data)))
        blobs.append(data)
        cur += (len(data) + a.sector - 1) // a.sector * a.sector

    if cur > a.size:
        raise SystemExit('REFUSED: repack needs %d B, original is %d B (over by %d). '
                         'In-place ISO patching requires an identical total size.'
                         % (cur, a.size, cur - a.size))

    with open(out, 'wb') as o:
        o.write(b'LINK' + struct.pack('<III', a.count, a.sector, 0))
        for so, sz in new_ents:
            o.write(struct.pack('<II', so, sz))
        for i, data in enumerate(blobs):
            o.seek(new_ents[i][0] * a.sector)
            o.write(data)
        o.truncate(a.size)          # keep the tail slack -> exact original size

    slack = a.size - cur
    print('rebuilt -> %s' % out)
    print('  entries    : %d (%d overridden)' % (a.count, len(payloads)))
    print('  used       : %d B' % cur)
    print('  slack/grow : %d B (%.1f MB)' % (slack, slack / 1048576))
    return out


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, arc = sys.argv[1], sys.argv[2]

    if cmd == 'list':
        a = Link(arc)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        print('count=%d sector=%#x size=%d' % (a.count, a.sector, a.size))
        for i in range(min(n, a.count)):
            print('  %5d off=%#-12x size=%-10d %s'
                  % (i, a.offset(i), a.entries[i][1], sniff(a.read(i)[:32])))

    elif cmd == 'info':
        a = Link(arc)
        i = int(sys.argv[3])
        b = a.read(i)
        print('idx    : %d' % i)
        print('sector : %d' % a.entries[i][0])
        print('offset : %#x (%d)' % (a.offset(i), a.offset(i)))
        print('size   : %d' % len(b))
        print('type   : %s' % sniff(b))
        print('head   : %s' % b[:48].hex())

    elif cmd == 'extract':
        a = Link(arc)
        i, out = int(sys.argv[3]), sys.argv[4]
        open(out, 'wb').write(a.read(i))
        print('idx %d (%d B) -> %s' % (i, a.entries[i][1], out))

    elif cmd == 'dumpall':
        a = Link(arc)
        outdir = sys.argv[3]
        os.makedirs(outdir, exist_ok=True)
        for i in range(a.count):
            open(os.path.join(outdir, '%04d.bin' % i), 'wb').write(a.read(i))
        print('dumped %d entries -> %s' % (a.count, outdir))

    elif cmd == 'rebuild':
        rebuild(arc, sys.argv[3], sys.argv[4])

    elif cmd == 'roundtrip':
        out = arc + '.roundtrip'
        rebuild(arc, None, out)
        a, b = sha1(arc), sha1(out)
        print('\noriginal : %s' % a)
        print('rebuilt  : %s' % b)
        print('%s' % ('IDENTICAL — repacker is lossless'
                      if a == b else 'DIFFERS — inspect before trusting rebuild'))
        os.remove(out)


if __name__ == '__main__':
    main()
