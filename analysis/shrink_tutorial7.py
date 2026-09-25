# -*- coding: utf-8 -*-
"""entry4 슬롯 초과 7차(마무리) 축약.
Usage: python analysis/shrink_tutorial7.py [--dry]
"""
import io, shutil, sys
SRC = 'work/e4_tutorial.tsv'

E = {
 ('25','27'): [('그 사업들 대부분이 성공을 거두어{N}더 훌륭하고 더 풍요로운 천하를 지향하며',
                '그 사업들 대부분이 성공하여{N}더 풍요로운 천하를 지향하며')],
 ('25','223'):[('누군가가 포로가 되거나', '누군가 포로가 되거나')],
 ('26','388'):[('{01}C{0e}{00}이 명장·용장에게 명하여{N}장강에 함대를 전개한다면',
                '{01}C{0e}{00}이 명장·용장에게 명해{N}장강에 함대를 전개하면'),
               ('병력의 차이 따위는 문제가 아닙니다{N}거기에 우리 군의 정예병이 더해지면{N}{V:0c38}군을 격파하는 것은 필연{N}……아무 문제도 없습니다',
                '병력 차이는 문제가 아닙니다{N}거기에 우리 정예병이 더해지면{N}{V:0c38}군 격파는 필연{N}……문제없습니다')],
 ('25','159'):[('이번에는 실제로 군비를 갖춰 보여라！', '이번엔 실제로 군비를 갖춰 보여라！')],
 ('26','403'):[('그리 된다면야{N}{01}C{0e}{00}를 따라온 장병들도{N}보답받는 셈이 될 것이겠지요',
                '그리 된다면{N}{01}C{0e}{00}를 따라온 장병들도{N}보답받는 셈이겠지요')],
 ('26','450'):[('그 능력에 걸맞은 향품을 주고', '능력에 걸맞은 향품을 주고')],
 ('26','710'):[('돌아가신 {01}Ck{00}의 원통함을 풀고자', '돌아가신 {01}Ck{00}의 원한을 풀고자')],
 ('25','336'):[('그 부분은 주공께서 직접 다양한 방법을{N}시도해 보시면 됩니다',
                '그 부분은 다양한 방법을{N}직접 시도해 보시면 됩니다')],
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
    shutil.copy(SRC, SRC + '.bak_shrink7')
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('저장 완료 (백업 %s.bak_shrink7)' % SRC)


if __name__ == '__main__':
    main()
