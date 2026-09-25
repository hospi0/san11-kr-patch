"""KOEI%SAN11 서브컨테이너(55개) 시나리오/튜토리얼/결전제패 타이틀 패치.

work/kessen_titles_plan.tsv (container_off, jp, kr, patch_off, jp_bytes,
kr_need, avail, fits) 기준으로 ISO를 in-place로 고쳐 쓴다. 원문 자리 + 뒤따르는
널 바이트를 예산으로 삼고, 남는 자리는 0x00으로 채운다(원문 길이를 넘어서도
전부 0으로 지워야 이전 바이트가 안 남는다).

Usage:
  python tools/patch_kessen_titles.py <iso> [--only 0x1eee008,...] [--dry]
"""
import sys
sys.path.insert(0, 'tools')
from encoding import Codec  # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
PLAN = 'work/kessen_titles_plan.tsv'


def load_plan():
    rows = []
    with open(PLAN, encoding='utf-8') as f:
        next(f)
        for ln in f:
            p = ln.rstrip('\n').split('\t')
            rows.append({
                'container': int(p[0], 16), 'jp': p[1], 'kr': p[2],
                'patch_off': int(p[3], 16), 'jp_bytes': int(p[4]),
                'kr_need': int(p[5]), 'avail': int(p[6]), 'fits': p[7] == 'True',
            })
    return rows


def main():
    iso_path = sys.argv[1]
    only = None
    for i, a in enumerate(sys.argv):
        if a == '--only':
            only = {int(x, 16) for x in sys.argv[i + 1].split(',')}
    dry = '--dry' in sys.argv

    codec = Codec(ELF)
    rows = load_plan()
    if only:
        rows = [r for r in rows if r['container'] in only]

    bad = [r for r in rows if not r['fits']]
    if bad:
        raise SystemExit('예산 초과 %d건 — 중단' % len(bad))

    f = None if dry else open(iso_path, 'r+b')
    n = 0
    for r in rows:
        kr_bytes = codec.encode(r['kr'])
        span = r['avail']
        payload = kr_bytes + b'\x00' * (span - len(kr_bytes))
        print('0x%x  %-14s -> %-14s  (%d/%d B)' %
              (r['patch_off'], r['jp'], r['kr'], len(kr_bytes) + 1, span))
        if not dry:
            f.seek(r['patch_off'])
            f.write(payload)
        n += 1

    if f:
        f.close()
    print('\n%s %d개 지점' % ('[dry-run] 확인만' if dry else '패치 완료', n))


if __name__ == '__main__':
    main()
