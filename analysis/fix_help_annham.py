"""help_kr.tsv의 「안 함」 9줄 교정.

`help_compress.py`의 규칙 `않습니다$ -> 안 함`이 비문을 만들었다("소지하고 있지 안 함").
규칙은 `않음`으로 고쳤고, 여기서는 **이미 TSV에 구워진 결과물**을 바로잡는다.
「존재하지 않음」류는 「없음」이 더 자연스럽고 짧아 그쪽으로 다시 썼다.

Usage: python analysis/fix_help_annham.py [--dry]
"""
import io
import shutil
import sys

TSV = 'work/help_kr.tsv'

FIX = {
    '534': '소지한 아이템 없음',
    '543': '유효한 저장 데이터 없음',
    '569': '설정할 수 있는 도시 없음',
    '743': '관직에 오른 무장 없음',
    '758': '동맹 관계인 세력 없음',
    '813': '대상이 되는 무장 없음',
    '929': '"PlayStation BB Unit"에 설치되어 있지 않음',
    '930': '"PlayStation BB Unit"이 연결되어 있지 않음',
    '932': '도시에 무장이 배치되어 있지 않음',
}


def main():
    dry = '--dry' in sys.argv
    lines = io.open(TSV, encoding='utf-8').read().split('\n')
    out, n = [], 0
    for ln in lines:
        p = ln.rstrip('\r').split('\t')
        if len(p) >= 5 and p[0] in FIX and '안 함' in p[4]:
            print('[%s] %s\n   -> %s' % (p[0], p[4], FIX[p[0]]))
            p[4] = FIX[p[0]]
            ln = '\t'.join(p)
            n += 1
        out.append(ln)
    print('\n%d줄 교정' % n)
    if n != len(FIX):
        print('★기대 %d줄인데 %d줄만 잡혔다 — TSV를 확인하라' % (len(FIX), n))
    if dry:
        print('(--dry: 쓰지 않음)')
        return
    shutil.copy(TSV, TSV + '.bak')
    io.open(TSV, 'w', encoding='utf-8', newline='').write('\n'.join(out))
    print('-> %s' % TSV)


if __name__ == '__main__':
    main()
