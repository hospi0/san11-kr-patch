"""Extract members from a PCSX2 savestate (.p2s).

A .p2s is a ZIP, but PCSX2 compresses members with zstd (method 93), which
python's zipfile refuses. So read each member's raw bytes straight out of the
archive and decompress with the zstandard module.

Members of interest:
  eeMemory.bin  32 MB  EE main RAM   <- master font atlas lives here
  GS.bin         4 MB  GS VRAM       <- 144-slot glyph cache lives here
  Screenshot.png       what was on screen when the state was saved

Usage: python p2s.py <state.p2s> <outdir>
"""
import os
import struct
import sys
import zipfile

import zstandard

ZSTD = 93


def raw_member(f, zi):
    """Return the member's stored (still-compressed) bytes."""
    f.seek(zi.header_offset)
    sig, ver, flags, method, t, d, crc, csz, usz, nlen, elen = \
        struct.unpack('<IHHHHHIIIHH', f.read(30))
    if sig != 0x04034b50:
        raise SystemExit('bad local header for %s' % zi.filename)
    f.seek(nlen + elen, os.SEEK_CUR)
    return f.read(zi.compress_size)


def extract(p2s, outdir, names=None):
    os.makedirs(outdir, exist_ok=True)
    z = zipfile.ZipFile(p2s)
    f = open(p2s, 'rb')
    out = {}
    for zi in z.infolist():
        if names and zi.filename not in names:
            continue
        blob = raw_member(f, zi)
        if zi.compress_type == ZSTD:
            blob = zstandard.ZstdDecompressor().decompress(
                blob, max_output_size=zi.file_size)
        elif zi.compress_type != zipfile.ZIP_STORED:
            blob = z.read(zi.filename)
        if len(blob) != zi.file_size:
            print('  ! %s: got %d want %d' % (zi.filename, len(blob), zi.file_size))
        dst = os.path.join(outdir, zi.filename)
        with open(dst, 'wb') as o:
            o.write(blob)
        out[zi.filename] = dst
        print('  %-28s %10d B  -> %s' % (zi.filename, len(blob), dst))
    return out


if __name__ == '__main__':
    extract(sys.argv[1], sys.argv[2],
            names=sys.argv[3].split(',') if len(sys.argv) > 3 else None)
