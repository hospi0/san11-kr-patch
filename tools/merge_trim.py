"""my files/*_trim.txt (원본/축약 대조 편집본) -> work/e4_*.tsv kr 컬럼 병합.

trim.txt 포맷:
  N) [block-index]
  원본: <text>
  축약: <text>
  (빈 줄)

축약이 원본과 다른 줄만 대상 tsv의 kr을 갱신한다. 원본이 현재 tsv의 kr과
다르면(드리프트) 그 항목은 건너뛰고 경고만 낸다 — 잘못된 줄에 덮어쓰지 않기 위함.

드리프트 검사는 "현재 tsv"가 아니라 --baseline으로 준 트림-전 원본 tsv 기준으로 한다.
(현재 tsv는 이전 병합으로 이미 축약돼 있을 수 있어, 그걸 기준으로 삼으면 이미 적용된
줄이 전부 오탐 드리프트로 잡혀 재적용이 막힌다.)

Usage:
  python tools/merge_trim.py "my files/tutorial_trim.txt" work/e4_tutorial.tsv \
      --baseline work/e4_tutorial.tsv.bak_pretrim
"""
import io
import re
import sys
import unicodedata as U

ENTRY_RE = re.compile(r'^\d+\)\s*\[(\d+)-(\d+)\]$')


def parse_trim(path):
    entries = {}
    lines = io.open(path, encoding='utf-8').read().split('\n')
    i = 0
    while i < len(lines):
        m = ENTRY_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        block, idx = int(m.group(1)), int(m.group(2))
        orig = lines[i + 1]
        comp = lines[i + 2]
        assert orig.startswith('원본: '), (i, orig)
        assert comp.startswith('축약: '), (i, comp)
        entries[(block, idx)] = (orig[len('원본: '):], comp[len('축약: '):])
        i += 3
    return entries


def body_bytes(s):
    t = re.sub(r'\{[^}]+\}', '', s)
    return sum(2 if '가' <= c <= '힣' else 1 for c in t)


def read_tsv_kr(tsv_path):
    kr = {}
    for ln in io.open(tsv_path, encoding='utf-8'):
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            kr[(int(p[0]), int(p[1]))] = U.normalize('NFC', p[4])
    return kr


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    trim_path, tsv_path = args[0], args[1]
    baseline_path = tsv_path
    if '--baseline' in sys.argv:
        baseline_path = sys.argv[sys.argv.index('--baseline') + 1]

    entries = parse_trim(trim_path)
    baseline_kr = read_tsv_kr(baseline_path)
    print('trim 항목: %d개 (드리프트 기준: %s)' % (len(entries), baseline_path))

    rows = io.open(tsv_path, encoding='utf-8').read().split('\n')
    out = []
    applied = saved = drift = unchanged = 0
    seen = set()
    for ln in rows:
        p = ln.split('\t')
        if len(p) >= 5 and p[0].isdigit():
            key = (int(p[0]), int(p[1]))
            if key in entries:
                seen.add(key)
                orig, comp = entries[key]
                base_kr = baseline_kr.get(key)
                if base_kr is not None and U.normalize('NFC', orig) != base_kr:
                    drift += 1
                    print('  ⚠️드리프트 [%d-%d] 기준tsv≠원본, 건너뜀' % key)
                elif comp != orig:
                    cur_kr = U.normalize('NFC', p[4])
                    if cur_kr == comp:
                        unchanged += 1
                    else:
                        saved += body_bytes(cur_kr) - body_bytes(comp)
                        p[4] = comp
                        applied += 1
                else:
                    unchanged += 1
            ln = '\t'.join(p)
        out.append(ln)

    missing = set(entries) - seen
    if missing:
        print('  ⚠️tsv에서 못 찾은 항목 %d개: %s' % (len(missing), sorted(missing)[:5]))

    io.open(tsv_path, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
    print('적용 %d줄 / 변경없음 %d줄 / 드리프트 %d줄 (건너뜀)' % (applied, unchanged, drift))
    print('원문 바이트 절감(raw, LZ압축 전): %d B' % saved)


if __name__ == '__main__':
    main()
