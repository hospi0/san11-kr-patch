"""아이템(entry6 0x2522d ×50) · 작위(entry5 0x41ca ×10) 필드 경계를 전수 통계로 잡는다.

table_columns.py와 같은 방법이되 엔트리를 골라 쓴다.
읽는 법: 널 100% = 필드 경계 / 0x83 100% = 카타카나(읽기) 시작 /
        널 0% + 짝수열 값종류 적음 = SJIS 본문 / 값 종류 ≤4 = 바이너리 필드

★사본 비교도 같이 한다 — 로스터는 52벌 중 A16/B36의 **내용이 달랐다**(docs/06).
  아이템도 그러면 일괄 주입하면 안 되고 사본마다 읽어서 번역해야 한다.
"""
import io
import os
import struct
import sys
from collections import Counter

ROM = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)"
S11 = os.path.join(ROM, 's11pkres.bin')

ITEM = dict(entry=6, base=0x2522d, stride=0x39, count=50)
RANK = dict(entry=5, base=0x41ca, stride=0x2c, count=10)
# 아이템 52벌: 그룹A 엔트리 6~21 rel 0x253f5(倚天) / 그룹B 24~29·32~61 rel 0x7f40a
GRP_A = list(range(6, 22))
GRP_B = list(range(24, 30)) + list(range(32, 62))
A_ANCHOR, B_ANCHOR = 0x253f5, 0x7f40a          # 倚天の剣 위치 = 사본 정렬 앵커


def load():
    s11 = open(S11, 'rb').read()
    n, sec = struct.unpack('<II', s11[4:12])
    tab = [struct.unpack('<II', s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(n)]
    return s11, tab, sec


def ent(s11, tab, sec, i):
    o, b = tab[i]
    return s11[o * sec: o * sec + b]


def report(recs, name, stride, out):
    out.write('\n===== %s: %d개 × %dB =====\n' % (name, len(recs), stride))
    out.write('off   널%%  0x83%%  값종류  최빈  판정\n')
    for c in range(stride):
        col = [r[c] for r in recs]
        nulls = 100 * col.count(0) // len(col)
        l83 = 100 * col.count(0x83) // len(col)
        cnt = Counter(col)
        v = ''
        if nulls >= 95:
            v = '← 항상 널 = 필드 경계'
        elif l83 >= 95:
            v = '← 항상 0x83 = 카타카나'
        elif len(cnt) <= 4:
            v = '← 값 %d종 = 바이너리' % len(cnt)
        elif nulls == 0 and len(cnt) <= 24 and c % 2 == 0:
            v = '← 널0%% & 종류적음 = SJIS 리드'
        out.write('+0x%02x  %3d  %4d  %5d  0x%02x  %s\n'
                  % (c, nulls, l83, len(cnt), cnt.most_common(1)[0][0], v))


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    s11, tab, sec = load()

    e6 = ent(s11, tab, sec, 6)
    recs = [e6[ITEM['base'] + i * ITEM['stride']:
               ITEM['base'] + (i + 1) * ITEM['stride']] for i in range(ITEM['count'])]
    report(recs, '아이템(entry6)', ITEM['stride'], out)

    e5 = ent(s11, tab, sec, 5)
    recs = [e5[RANK['base'] + i * RANK['stride']:
               RANK['base'] + (i + 1) * RANK['stride']] for i in range(RANK['count'])]
    report(recs, '작위(entry5)', RANK['stride'], out)

    # ---- 52벌 사본이 내용이 같은가 ----
    out.write('\n===== 아이템 52벌 사본 비교 (테이블 %dB 전체) =====\n'
              % (ITEM['stride'] * ITEM['count']))
    span = ITEM['stride'] * ITEM['count']
    blobs = {}
    for grp, anchor in (('A', A_ANCHOR), ('B', B_ANCHOR)):
        for i in (GRP_A if grp == 'A' else GRP_B):
            e = ent(s11, tab, sec, i)
            base = anchor - 8 * ITEM['stride']       # 倚天の剣 = idx 8
            blobs[(grp, i)] = e[base: base + span]
    uniq = {}
    for k, v in blobs.items():
        uniq.setdefault(v, []).append(k)
    out.write('사본 %d벌 → 서로 다른 내용 %d종\n' % (len(blobs), len(uniq)))
    for j, (v, ks) in enumerate(uniq.items()):
        out.write('  종류%d: %d벌  %s\n'
                  % (j, len(ks), ' '.join('%s%d' % k for k in ks[:8])
                     + (' …' if len(ks) > 8 else '')))
    out.close()


if __name__ == '__main__':
    main()
