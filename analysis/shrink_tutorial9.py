# -*- coding: utf-8 -*-
"""entry4 슬롯 초과 9차(최종) — 오타 수정 + 안전여유 확보.
Usage: python analysis/shrink_tutorial9.py [--dry]
"""
import io, shutil, sys
SRC = 'work/e4_tutorial.tsv'

E = {
 ('26','173'):[('문제없다고 생각습니다', '문제없다고 생각합니다')],   # 오타 수정(어간 누락)
 ('25','23'): [('오늘날까지도 수많은 백성들에게 사랑받고 있다', '오늘날까지도 백성들에게 사랑받고 있다')],
 ('26','95'): [('하오면 천운은 다시 원래로 돌아가야 마땅하며', '하오면 천운은 다시 돌아가야 마땅하며')],
 ('28','69'): [('야습 준비는 시시각각 갖추어지고 있었다', '야습 준비는 시시각각 갖춰지고 있었다')],
 ('25','159'):[('그곳에서 군비를 갖추어{N}{V:0c32} 타도에 대비하도록 하라',
                '그곳에서 군비를 갖춰{N}{V:0c32} 타도에 대비하라')],
 ('26','709'):[('아직 {V:0d32}님은 건재하다', '아직 {V:0d32}님이 건재하다')],
 ('26','665'):[('{V:96}2x한{V:96}0x 왕조는 재흥의 길을 걷기 시작했다', '{V:96}2x한{V:96}0x 왕조는 재흥의 길을 걸었다')],
}


def main():
    dry = '--dry' in sys.argv
    lines = io.open(SRC, encoding='utf-8').read().split('\n')
    idxmap = {}
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            idxmap[(p[0], p[1])] = i
    ok = 0
    fails = []
    saved = 0
    for key, subs in E.items():
        if key not in idxmap:
            fails.append(('%s:%s' % key, '행없음', ''))
            continue
        i = idxmap[key]
        p = lines[i].split('\t')
        for old, new in subs:
            c = p[4].count(old)
            if c != 1:
                fails.append(('%s:%s' % key, 'old %d회' % c, old))
                continue
            saved += (len(old) - len(new))
            p[4] = p[4].replace(old, new)
            ok += 1
        lines[i] = '\t'.join(p)
    print('치환 성공 %d개 / 실패 %d개 / 원시 절감 %d자' % (ok, len(fails), saved))
    for k, r, o in fails:
        print('  실패 [%s] %s : %r' % (k, r, o))
    if dry:
        print('(--dry: 저장 안 함)')
        return
    shutil.copy(SRC, SRC + '.bak_shrink9')
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('저장 완료 (백업 %s.bak_shrink9)' % SRC)


if __name__ == '__main__':
    main()
