# -*- coding: utf-8 -*-
"""entry4 슬롯 초과 8차(최종 확정) 축약 — 111B 잔여 + 안전여유 확보.
Usage: python analysis/shrink_tutorial8.py [--dry]
"""
import io, shutil, sys
SRC = 'work/e4_tutorial.tsv'

E = {
 ('25','197'):[('참고로, 부대의 병사가 적어지면{N}강한 적이 다가오는 것만으로도 혼란 상태에{N}빠질 수 있으니 주의하십시오{N}또한 금은 0이라도 출진할 수 있지만{N}병량은 최소 1이 필요합니다{N}그럼 부대를 편성해 주십시오{N}빠른 출진을 원하면{N}자동 버튼으로 병과를 선택해{N}간단히 편성할 수 있습니다',
                '부대 병사가 적으면{N}강한 적이 다가오는 것만으로도{N}혼란 상태에 빠질 수 있으니 주의하십시오{N}금은 0이어도 출진 가능하나{N}병량은 최소 1이 필요합니다{N}그럼 부대를 편성해 주십시오{N}빠른 출진을 원하면{N}자동 버튼을 사용하십시오')],
 ('25','100'):[('할 일을 잊으셨다면, {V:96}19x{BTNba}{BTNbb} 버튼을{N}눌러서{V:96}0x, 클리어 조건을 확인해 주세요',
                '할 일을 잊으셨다면{V:96}19x{BTNba}{BTNbb} 버튼으로{V:96}0x 클리어 조건을 확인해 주세요')],
 ('25','188'):[('출진 시에는、{V:96}19x누구{V:96}0x에게 부대를 이끌게 할지{N}{V:96}19x어떤 병장{V:96}0x을 부대에 장비시킬지{N}{V:96}19x어떤 물자{V:96}0x를 얼마나 가져갈지{N}……대략 이것들을 정합니다',
                '출진 시엔、{V:96}19x누구{V:96}0x에게 부대를 이끌게 할지{N}{V:96}19x어떤 병장{V:96}0x을 장비시킬지{N}{V:96}19x어떤 물자{V:96}0x를 얼마나 가져갈지{N}……대략 이것들을 정합니다')],
 ('26','1029'):[('또한, {V:96}19x조폐나 곡창은{N}Lv에 관계없이 영향을 미치{V:96}0x니{N}유용하게 활용해 주십시오',
                  '또한 {V:96}19x조폐·곡창은{N}Lv과 무관하게 영향을 미치{V:96}0x니{N}유용하게 활용해 주십시오')],
 ('25','336'):[('이제 주공은 6개 도시를 다스리니{N}이 도시들에서 꾸준히 내정을 하면{N}500 정도는 순식간일 것입니다',
                '이제 6개 도시를 다스리니{N}꾸준히 내정을 하면{N}500 정도는 순식간일 것입니다')],
 ('25','207'):[('전법에 대해 설명해 드리지요', '전법을 설명해 드리지요')],
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
    shutil.copy(SRC, SRC + '.bak_shrink8')
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('저장 완료 (백업 %s.bak_shrink8)' % SRC)


if __name__ == '__main__':
    main()
