"""ISO9660 reader/patcher for the San11 PUK PS2 disc.

Why this exists: the final patch does NOT rebuild the ISO. ISO9660 stores file
data contiguously, so as long as a file keeps its original size we can overwrite
its bytes in place inside the ISO. That keeps LBAs, directory records and the
2 GB movie blob untouched.

Usage:
  python iso.py list   <iso>              # walk the filesystem, print LBA/size
  python iso.py verify <iso>              # check files against known SHA-1
  python iso.py extract <iso> <name> <out>
  python iso.py patch  <iso> <name> <src> # in-place, size must match exactly
"""
import hashlib
import struct
import sys

SECTOR = 2048

# SHA-1 baseline recorded in README.md (original, unmodified disc)
BASELINE = {
    'SLPM_667.01':  (5242752,   '8f3d9bfabc698d0fd7a8e31e7b72bd5c9daca527'),
    'OVERLAY1.BIN': (396928,    'fe5bacf6ada4057fb51d20f70dfeeb7097017ce1'),
    'OVERLAY2.BIN': (326784,    '4d7178e4d2a2554a750a90e82601840bf7b4b156'),
    'S11PKRES.BIN': (517752832, 'c2aa80b8e3c70a42e86fae4cba587654d187bd9d'),
    'SYSTEM.CNF':   (80,        '9cfe36bef5ee7e7239a674f563bc5cf1d3829f5a'),
}


def _both_endian32(b):
    """ISO9660 stores 32-bit values twice: LE then BE. Trust the LE half."""
    return struct.unpack('<I', b[:4])[0]


def read_dir(f, lba, size, path='/'):
    """Yield (path, lba, size, is_dir) for every record in a directory extent."""
    f.seek(lba * SECTOR)
    data = f.read(size)
    off = 0
    while off < len(data):
        rec_len = data[off]
        if rec_len == 0:
            # rest of this sector is padding; jump to the next one
            off = (off // SECTOR + 1) * SECTOR
            if off >= len(data):
                break
            continue
        rec = data[off:off + rec_len]
        ext_lba = _both_endian32(rec[2:10])
        ext_len = _both_endian32(rec[10:18])
        flags = rec[25]
        name_len = rec[32]
        name = rec[33:33 + name_len]
        if name in (b'\x00', b'\x01'):        # '.' and '..'
            off += rec_len
            continue
        nm = name.decode('latin1').split(';')[0]
        is_dir = bool(flags & 0x02)
        full = path + nm
        yield full, ext_lba, ext_len, is_dir
        if is_dir:
            yield from read_dir(f, ext_lba, ext_len, full + '/')
        off += rec_len


def walk(iso):
    f = open(iso, 'rb')
    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    if pvd[0] != 1 or pvd[1:6] != b'CD001':
        raise SystemExit('not an ISO9660 image (no PVD at sector 16)')
    root = pvd[156:190]
    root_lba = _both_endian32(root[2:10])
    root_len = _both_endian32(root[10:18])
    vol = pvd[40:72].decode('latin1').strip()
    return f, vol, list(read_dir(f, root_lba, root_len))


def sha1_at(f, lba, size):
    f.seek(lba * SECTOR)
    h = hashlib.sha1()
    left = size
    while left:
        chunk = f.read(min(1 << 20, left))
        if not chunk:
            break
        h.update(chunk)
        left -= len(chunk)
    return h.hexdigest()


def find(entries, name):
    for full, lba, size, is_dir in entries:
        if not is_dir and full.split('/')[-1].upper() == name.upper():
            return full, lba, size
    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, iso = sys.argv[1], sys.argv[2]
    f, vol, entries = walk(iso)

    if cmd == 'list':
        print('volume: %s' % vol)
        for full, lba, size, is_dir in entries:
            print('  %-28s %s lba=%-9d size=%-12d off=%#x'
                  % (full, 'D' if is_dir else 'F', lba, size, lba * SECTOR))

    elif cmd == 'verify':
        print('volume: %s' % vol)
        ok = True
        for name, (want_sz, want_sha) in BASELINE.items():
            hit = find(entries, name)
            if not hit:
                print('  MISSING  %s' % name)
                ok = False
                continue
            full, lba, size = hit
            if size != want_sz:
                print('  SIZE MISMATCH %s: iso=%d want=%d' % (name, size, want_sz))
                ok = False
                continue
            got = sha1_at(f, lba, size)
            mark = 'OK  ' if got == want_sha else 'FAIL'
            print('  %s %-14s lba=%-9d size=%-12d %s' % (mark, name, lba, size, got))
            ok &= (got == want_sha)
        print('\n%s' % ('ALL MATCH — ISO is the same build as the extracted files'
                        if ok else 'MISMATCH — do not delete the extracted copy'))

    elif cmd == 'extract':
        name, out = sys.argv[3], sys.argv[4]
        full, lba, size = find(entries, name)
        f.seek(lba * SECTOR)
        with open(out, 'wb') as o:
            left = size
            while left:
                c = f.read(min(1 << 20, left))
                o.write(c)
                left -= len(c)
        print('extracted %s (%d B) -> %s' % (full, size, out))

    elif cmd == 'patch':
        name, src = sys.argv[3], sys.argv[4]
        full, lba, size = find(entries, name)
        data = open(src, 'rb').read()
        if len(data) != size:
            raise SystemExit('REFUSED: size differs (src=%d iso=%d). In-place patching '
                             'requires an identical size.' % (len(data), size))
        f.close()
        with open(iso, 'r+b') as w:
            w.seek(lba * SECTOR)
            w.write(data)
        print('patched %s in place at lba=%d (%d B)' % (full, lba, size))


if __name__ == '__main__':
    main()
