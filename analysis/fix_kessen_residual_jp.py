# -*- coding: utf-8 -*-
"""e4_kessen.tsv에 남은 미번역 한자(지명·인명·군세명·커맨드명 등) 66줄을
프로젝트에 이미 확립된 용어(cities_kr.tsv·places_kr.tsv·e4_sys.tsv·e4_dict.tsv,
그리고 kessen 자체에서 이미 번역된 다른 줄들)에 맞춰 치환한다.

긴 복합어를 먼저 치환해야 부분 문자열이 깨지지 않는다(예: 曹操部隊 -> 조조부대를
먼저 치환하지 않으면 曹操만 조조로 바뀌고 部隊가 남는다).

Usage: python analysis/fix_kessen_residual_jp.py [--dry]
"""
import io
import shutil
import sys

TSV = 'work/e4_kessen.tsv'

# 길이 내림차순으로 적용(복합어 먼저)
REPLACEMENTS = [
    ('曹操部隊', '조조부대'),
    ('曹操軍', '조조군'),
    ('劉備軍', '유비군'),
    ('孫権軍', '손권군'),
    ('袁紹軍', '원소군'),
    ('都市コマンド', '도시 커맨드'),
    ('部隊コマンド', '부대 커맨드'),
    ('半年以内', '반년 이내'),
    ('指定日数経過', '지정일수 경과'),
    ('戦法のみ', '전법만'),
    ('戦法', '전법'),
    ('荊南', '형남'),
    ('零陵', '영릉'),
    ('桂陽', '계양'),
    ('武陵', '무릉'),
    ('長沙', '장사'),
    ('柴桑', '시상'),
    ('小沛', '소패'),
    ('陳留', '진류'),
    ('徐州', '서주'),
    ('許昌', '허창'),
    ('長坂', '장판'),
    ('汝南', '여남'),
    ('漢中', '한중'),
    ('赤壁', '적벽'),
    ('虎痴', '호치'),
    ('孔明', '공명'),
    ('関羽', '관우'),
    ('黄忠', '황충'),
    ('劉備', '유비'),
    ('馬騰', '마등'),
    ('袁紹', '원소'),
    ('周瑜', '주유'),
    ('諸葛亮', '제갈량'),
    ('曹操', '조조'),
    ('移動', '이동'),
    ('呼寄', '호출'),
    ('・', ', '),
]


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')
    n = 0
    for i, ln in enumerate(lines):
        p = ln.rstrip('\r').split('\t')
        if len(p) < 5 or not p[0].isdigit() or not p[4].strip():
            continue
        kr = p[4]
        new = kr
        for old, rep in REPLACEMENTS:
            new = new.replace(old, rep)
        if new != kr:
            p[4] = new
            lines[i] = '\t'.join(p)
            n += 1

    print('%d줄 수정' % n)
    if dry:
        print('(--dry: 쓰지 않음)')
        return
    shutil.copy(TSV, TSV + '.bak3')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('-> %s' % TSV)


if __name__ == '__main__':
    main()
