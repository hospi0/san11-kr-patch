"""특기·기교·능력 이름 번역본 검증.

검사 항목:
  1. 커버리지 — entry5에서 읽은 이름이 전부 번역돼 있나 (샘플 아님, 전수)
  2. 예산 — 특기 4B 고정 / 기교 ≤8B / 능력 4B
  3. 인코딩 — 모든 음절이 운반체 코덱으로 인코딩되나
  4. 능력↔특기 정합 — 능력 이름이 전부 특기 목록에 있나

★**예산 계산은 반드시 실제 인코더(Codec.encode)로 한다.** 손으로 len(s)*2를 세면
인코더와 어긋나 거짓 통과/거짓 초과가 난다 — 세션3·세션5에서 같은 버그가 정반대
방향으로 두 번 났다. [[feedback_kr_patch_verification]]
"""
import io
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from encoding import Codec              # noqa: E402
from tokki_names import TOKKI, GIKOU    # noqa: E402

ENTRY5 = os.path.join(HERE, '..', 'work', 'entry5.bin')
ELF = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"

SPEC = {
    '특기': dict(base=0x5210, stride=0x5d, count=100, name=(0x00, 0x05), cap=4, table=TOKKI),
    '기교': dict(base=0x7664, stride=0x5c, count=36, name=(0x00, 0x09), cap=8, table=GIKOU),
    '능력': dict(base=0xa7a4, stride=0x4a, count=66, name=(0x00, 0x09), cap=4, table=TOKKI),
}


def field(rec, off, cap):
    end = rec.find(b'\x00', off, off + cap)
    if end < 0:
        end = off + cap
    return rec[off:end].decode('cp932')


def main():
    blob = open(ENTRY5, 'rb').read()
    codec = Codec(ELF)
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    fails = 0

    for tname, sp in SPEC.items():
        missing, over, unenc = [], [], []
        names = []
        for i in range(sp['count']):
            off = sp['base'] + i * sp['stride']
            jp = field(blob[off:off + sp['stride']], *sp['name'])
            names.append(jp)
            kr = sp['table'].get(jp)
            if kr is None:
                missing.append((i, off, jp))
                continue
            try:
                enc = codec.encode(kr)      # ★검사기 = 인코더 (같은 함수)
            except Exception as e:
                unenc.append((jp, kr, str(e)))
                continue
            if len(enc) > sp['cap']:
                over.append((jp, kr, len(enc), sp['cap']))
            elif tname == '특기' and len(enc) != sp['cap']:
                over.append((jp, kr, len(enc), sp['cap']))   # 특기는 4B '정확히'

        uniq = len(set(names))
        out.write('\n===== %s =====\n' % tname)
        out.write('레코드 %d개 (고유 이름 %d개)\n' % (sp['count'], uniq))
        out.write('  번역 누락      : %d %s\n' % (len(missing), missing or ''))
        out.write('  예산 위반      : %d %s\n' % (len(over), over or ''))
        out.write('  인코딩 불가    : %d %s\n' % (len(unenc), unenc or ''))
        fails += len(missing) + len(over) + len(unenc)

        if tname == '능력':
            notin = sorted(set(names) - set(TOKKI))
            out.write('  특기 목록에 없는 능력 이름: %d %s\n' % (len(notin), notin or ''))
            fails += len(notin)

    out.write('\n%s\n' % ('✅ 전부 통과' if fails == 0 else '❌ 문제 %d건' % fails))
    out.close()
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
