"""entry4(LS11)를 ISO 안에 제자리 기록 — 인코더 수용 테스트 / 번역 삽입용.

★크기를 원본과 **정확히 같게** 맞춘다(부족분은 0 패딩). 그러면:
  - LINK 엔트리(섹터·크기)를 안 건드린다
  - s11pkres.bin 크기·ISO 크기·LBA·디렉토리레코드 전부 그대로
  - 순수 바이트 덮어쓰기 = poke_hud.py와 같은 방식
LS11은 블록테이블의 오프셋으로 데이터를 찾으므로 **꼬리의 잉여 바이트는 아무도 안 읽는다.**

⚠️패딩으로 못 맞출 만큼 커지면(번역 후) 그땐 LINK 재배치가 필요하고, **RAM 슬롯 한계**가
  관문이 된다(entry3가 0x1E000 초과로 검은화면 난 전례. docs/11). 그건 별도 과제다.

Usage:
  python poke_e4.py <iso> [--src work/entry4_rebuilt.bin] [--dry] [--restore]
"""
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from iso import walk, find                                    # noqa: E402

ENTRY4_IN_S11 = 632 * 0x800          # 섹터 632
ORIG_SIZE = 709268

iso_path = sys.argv[1]
src = 'work/entry4_rebuilt.bin'
dry = '--dry' in sys.argv
restore = '--restore' in sys.argv
for i, a in enumerate(sys.argv):
    if a == '--src':
        src = sys.argv[i + 1]
if restore:
    src = 'work/entry4.bin'

orig = open('work/entry4.bin', 'rb').read()
assert len(orig) == ORIG_SIZE, len(orig)
new = open(src, 'rb').read()
if len(new) > ORIG_SIZE:
    raise SystemExit('원본(%d)보다 큼: %d B — 패딩으로 못 맞춘다. LINK 재배치가 필요하다.'
                     % (ORIG_SIZE, len(new)))
padded = new + b'\x00' * (ORIG_SIZE - len(new))

f, vol, entries = walk(iso_path)
_, lba, _sz = find(entries, 'S11PKRES.BIN')
off = lba * 2048 + ENTRY4_IN_S11
print('S11PKRES.BIN at ISO %#x (lba %d)' % (lba * 2048, lba))
print('entry4       at ISO %#x  (%d B)' % (off, ORIG_SIZE))
f.seek(off)
cur = f.read(ORIG_SIZE)
f.close()

state = ('clean' if cur == orig else
         'already-patched' if cur == padded else 'OTHER')
print('현재 상태: %s' % state)
if cur[:4] != b'LS11':
    raise SystemExit('그 자리가 LS11이 아니다 (%r) — 오프셋이 틀렸다.' % cur[:4])
print('소스: %s  %d B  (+패딩 %d)' % (src, len(new), ORIG_SIZE - len(new)))
if cur == padded:
    print('이미 같은 내용 — 할 일 없음')
    raise SystemExit(0)
if dry:
    print('dry run — 안 씀')
    raise SystemExit(0)

with open(iso_path, 'r+b') as w:
    w.seek(off)
    w.write(padded)
print('기록 완료 -> %s' % iso_path)
