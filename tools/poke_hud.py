"""HUD 行/技 + 부대상태 뱃지를 ISO 안에 제자리 기록 (idx=94, 8bpp/W512).

S11PKRES.BIN은 ISO에 연속으로 놓여 있어 파일크기·LBA·디렉토리레코드를 안 건드리고
바이트만 덮어쓸 수 있다(poke_glyph.py와 같은 방식).

  ISO 오프셋 = <S11PKRES.BIN ISO 오프셋> + 0x04C1E800(entry94) + 행*512 + x

★안전장치: 쓰기 전에 그 자리 바이트가 **원본 셀과 일치**하는지 확인한다. 오프셋이 틀리면
  조용히 망가뜨리는 대신 큰 소리로 실패한다. 이미 우리가 쓴 자리(재실행)는 통과시킨다.

Usage:
  python poke_hud.py <iso> [--only hud|badges] [--em 16] [--badge-em 14] [--dry] [--force]
"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from iso import walk, find                                                # noqa: E402
import hud_badge as H                                                     # noqa: E402

ENTRY94_IN_S11 = 0x04C1E800

iso_path = sys.argv[1]
font = 'C:/Windows/Fonts/batang.ttc'
em, bem, weight, bweight = 16, 14, 0.3, 0.2
lem, lweight, lhalo = 22, 1.2, 1.3   # 라벨(気力/耐久/治安)
only = None
dry = '--dry' in sys.argv
force = '--force' in sys.argv
for i, a in enumerate(sys.argv):
    if a == '--font':
        font = sys.argv[i + 1]
    elif a == '--em':
        em = int(sys.argv[i + 1])
    elif a == '--badge-em':
        bem = int(sys.argv[i + 1])
    elif a == '--label-em':
        lem = int(sys.argv[i + 1])
    elif a == '--only':
        only = sys.argv[i + 1]

ref = open('work/entry94.bin', 'rb').read()

f, vol, entries = walk(iso_path)
_, lba, _sz = find(entries, 'S11PKRES.BIN')
base = lba * 2048 + ENTRY94_IN_S11
print('S11PKRES.BIN at ISO %#x (lba %d)' % (lba * 2048, lba))
print('entry94  at ISO %#x' % base)


def read_iso(row0, x, h, w):
    got = np.zeros((h, w), np.uint8)
    for i in range(h):
        f.seek(base + (row0 + i) * H.PITCH + x)
        got[i] = np.frombuffer(f.read(w), np.uint8)
    return got


plan = []

if only != 'badges':
    for kanji, x in H.CELLS.items():
        want = H.read_cell(ref, x)
        new = H.make_cell(H.KR[kanji], font, em=em, weight=weight)
        got = read_iso(H.ROW0, x, H.CH, H.CW)
        state = 'clean' if np.array_equal(got, want) else (
            'already-patched' if np.array_equal(got, new) else 'MISMATCH')
        print('  %s @ ISO %#x  %s' % (kanji, base + H.ROW0 * H.PITCH + x, state))
        if state == 'MISMATCH' and not force:
            raise SystemExit('guard failed for %s -- refusing to write' % kanji)
        if state != 'already-patched':
            plan.append((kanji, H.ROW0, x, new, H.PITCH))

if only != 'hud':
    for key, (r0, x, kr) in H.BADGES.items():
        want = H.badge_cell(ref, r0, x)
        new = H.make_badge(want, kr, font, em=bem, weight=bweight)
        got = read_iso(r0, x, 18, 20)
        state = 'clean' if np.array_equal(got, want) else (
            'already-patched' if np.array_equal(got, new) else 'MISMATCH')
        print('  %-4s @ ISO %#x  %s  -> %s' % (key, base + r0 * H.PITCH + x, state, kr))
        if state == 'MISMATCH' and not force:
            raise SystemExit('guard failed for %s -- refusing to write' % key)
        if state != 'already-patched':
            plan.append((key, r0, x, new, H.PITCH))

if only != 'hud':
    import hud_labels as L
    r0, r1, x0, x1 = L.REGION
    want = L.read_region(ref)
    new = L.make_region(font, em=lem, weight=lweight, halo_px=lhalo)
    got = np.zeros((r1 - r0, x1 - x0), np.uint8)
    for i in range(r1 - r0):                       # ⚠️이 구역은 피치 **256**이다 (뱃지는 512)
        f.seek(base + (r0 + i) * L.PITCH + x0)
        got[i] = np.frombuffer(f.read(x1 - x0), np.uint8)
    state = 'clean' if np.array_equal(got, want) else (
        'already-patched' if np.array_equal(got, new) else 'MISMATCH')
    print('  labels @ ISO %#x  %s  -> 기력/내구/치안' % (base + r0 * L.PITCH + x0, state))
    if state == 'MISMATCH' and not force:
        raise SystemExit('guard failed for labels -- refusing to write')
    if state != 'already-patched':
        plan.append(('labels', r0, x0, new, L.PITCH))

f.close()

if not plan:
    print('nothing to do -- everything already patched')
    raise SystemExit(0)
if dry:
    print('dry run -- %d cell(s) would be written' % len(plan))
    raise SystemExit(0)

with open(iso_path, 'r+b') as w:
    for name, r0, x, cell, pitch in plan:
        for i in range(cell.shape[0]):
            w.seek(base + (r0 + i) * pitch + x)
            w.write(cell[i].tobytes())
        print('  wrote %s' % name)
print('done: %d cell(s) -> %s' % (len(plan), iso_path))
