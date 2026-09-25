"""특기·기교·능력 세 테이블 통합 추출 → 번역용 TSV.

## 테이블 (전부 entry5 = s11pkres idx=5, 파일오프셋 0x1e9800)

| 테이블 | base | stride | 개수 | 끝 |
|---|---|---|---|---|
| 특기 特技 | 0x5210 | 0x5d | 100 | 0x7664 = 기교 base와 정확히 맞닿음 |
| 기교 技巧 | 0x7664 | 0x5c |  36 | 0x8354 (3탭 × 3행 × 4레벨) |
| 능력 能力研究 | **0x9e64** | 0x4a | **98** | 0xbab8 = 파일 끝과 정확히 일치 |

⚠️★**능력을 0xa7a4/66으로 적어놨던 옛 기록은 틀렸다.** 앞쪽 32개(능력치 15 · 병과적성 12 ·
특기 5)를 통째로 놓쳤고, 실기 스크린샷에 「統+5低」「戟兵Ｂ」가 일본어로 남아 사용자가 발견했다.
98 = 특기노드 71 + 능력치 15(統武知政魅 × 低中高) + 병과적성 12(6병과 × ＡＢ).
[[feedback_scan_coverage_and_detectors]] — 샘플을 전수로 기록하지 말 것.

## 레코드 필드 — 100/36/98 전수 열별 통계로 확정 (table_columns.py)

특기(93B): +0x00 이름 4B+\\0 (★+0x04가 100/100 널 = 전부 2한자)
           +0x05 읽기 (★+0x05·+0x07이 100/100 0x83 = 카타카나)
           +0x18 설명 (★+0x18~+0x37 널0% & 짝수열 값종류 16~22 = SJIS 리드)
           +0x5b 플래그
기교(92B): +0x00 이름 ≤8B+\\0 (★+0x08 77% 널 = 4한자 28개 / +0x04 22% 널 = 2한자 8개)
           +0x09 읽기 (★+0x09·+0x0b·+0x0d가 36/36 0x83)
           +0x2a 설명 (★+0x2a~ 널0% & 짝수열 값종류 9~16)
           +0x55 금 u16, +0x57 필요기교P u16 (★값 4종뿐 = 1000/2000/5000/10000)
능력(74B): +0x00 이름 ≤8B+\\0 (★+0x06~+0x08이 98/98 널. 원본 최대 6B = 「統+5低」「槍兵Ｂ」)
           +0x09 설명 ≤54B (★+0x34~+0x3f가 98/98 널, 첫 live = +0x40)
           ⚠️**설명 길이가 3종**: 특기 30B(71개) · 적성 26B(12개) · 능력치 35B(15개).
             "설명 30B 고정"은 특기 노드 66개만 본 **표본 편향**이었다.
           ★특기 노드 설명은 「特技「X」を武将に習得させる」 템플릿이고 문장 안에 이름이
             한 번 더 박힌다 → 이름 번역 시 두 곳을 같이 바꿔야 한다.

⚠️★★**널을 따라 걷는 파서 금지.** 필드의 남는 꼬리에 옛 레이아웃 찌꺼기가 남아 있어
(게임은 \\0까지만 읽으니 무해) 널추적 파서는 그걸 문자열 시작으로 오인해 2바이트 어긋난다.
지난 세션 `work/tokki_raw.tsv`가 「バ輸送部隊の…」로 깨진 게 전부 이 이유. 고정 오프셋으로 읽어라.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from tokki_names import TOKKI, GIKOU   # noqa: E402

ENTRY5 = os.path.join(HERE, '..', 'work', 'entry5.bin')
KRNAME = {'특기': TOKKI, '기교': GIKOU, '능력': TOKKI}

# (base, stride, count, 이름off, 이름cap, 읽기off, 읽기cap, 설명off, 설명cap)
SPEC = {
    '특기': dict(base=0x5210, stride=0x5d, count=100,
                name=(0x00, 0x05), read=(0x05, 0x13), desc=(0x18, 0x43)),
    '기교': dict(base=0x7664, stride=0x5c, count=36,
                name=(0x00, 0x09), read=(0x09, 0x21), desc=(0x2a, 0x2a)),
    '능력': dict(base=0x9e64, stride=0x4a, count=98,
                name=(0x00, 0x09), read=None, desc=(0x09, 0x36)),
}

KATA = re.compile(r'^[ァ-ヶー・]+$')
# 찌꺼기 검출기: 어긋난 디코드는 반각가나(ﾚｺﾍ…)·라틴 문자로 튄다.
# ⚠️반각 숫자/마침표/％는 정상이다 — 게임이 「50％」「1.5倍」로 쓴다(거짓양성 9건 겪음).
JUNK = re.compile(r'[｡-ﾟA-Za-z�]')


def field(rec, off, cap):
    end = rec.find(b'\x00', off, off + cap)
    if end < 0:
        end = off + cap
    try:
        return rec[off:end].decode('cp932'), end - off
    except UnicodeDecodeError:
        return None, end - off


def main():
    blob = open(ENTRY5, 'rb').read()
    tsv = io.open(sys.argv[1], 'w', encoding='utf-8')
    rep = io.open(sys.argv[2], 'w', encoding='utf-8')

    tsv.write('# 삼국지11 PUK — 특기100 + 기교36 + 능력66 설명 번역용\n')
    tsv.write('# kr열에 한글 번역을 넣어 주세요. 비워두면 미번역으로 처리합니다.\n')
    tsv.write('# jpB = 원문 바이트, capB = 필드 용량(추정). 번역이 jpB 이하면 100%% 안전합니다.\n')
    tsv.write('# ⚠️능력 66개는 설명이 전부 같은 템플릿입니다 — 1번만 번역하시면 나머지는 제가 복제합니다.\n')
    tsv.write('#\n')
    tsv.write('table\tidx\toffset\t이름\t이름(한글)\tjpB\tcapB\tjp\tkr\n')

    for tname, sp in SPEC.items():
        bad = 0
        maxd = 0
        rep.write('\n===== %s =====\n' % tname)
        for i in range(sp['count']):
            off = sp['base'] + i * sp['stride']
            rec = blob[off:off + sp['stride']]
            name, _ = field(rec, *sp['name'])
            desc, dlen = field(rec, *sp['desc'])
            maxd = max(maxd, dlen)
            if not desc or JUNK.search(desc):
                bad += 1
                rep.write('  ⚠️ idx%d 0x%04x %s : %r\n' % (i, off, name, desc))
            tsv.write('%s\t%d\t0x%04x\t%s\t%s\t%d\t%d\t%s\t\n'
                      % (tname, i, off, name, KRNAME[tname].get(name, ''),
                         dlen, sp['desc'][1], desc))
        rep.write('  레코드 %d개 / 설명 찌꺼기 %d개 / 설명 최대 %dB (용량 %dB)\n'
                  % (sp['count'], bad, maxd, sp['desc'][1]))

    tsv.close()
    rep.close()


if __name__ == '__main__':
    main()
