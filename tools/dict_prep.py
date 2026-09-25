# -*- coding: utf-8 -*-
"""용어사전(e4_dict) 번역 준비 도구.

하는 일:
  1. 기존 KR 자산(ui_kr.tsv + 전법 senpou + 수동 오버라이드)으로 **glossary map**(jp→ko)을 만든다.
  2. 각 dict 항목의 하이퍼링크 `{1c}[{1c}I<8hex><표시텍스트>{1c}]`에서 **표시텍스트만 한글로 치환**한다
     (id·구조는 그대로. 표시텍스트는 다른 용어사전 항목의 표제어라 이미 번역돼 있다).
  3. 번역용 **워크시트**(work/dict_worksheet.tsv)를 뽑는다: block, index, 링크-한글화된 jp, (빈)kr.
     → 나는 링크 태그는 그대로 두고 주변 산문만 번역하면 된다.

★하이퍼링크 커버리지: 248종 중 229 = ui_kr, 나머지는 전법 + 아래 MANUAL로 채운다.
"""
import io
import os
import re
import sys
import unicodedata as U

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from senpou_names import SENPOU  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_TSV = os.path.join(ROOT, 'work', 'e4_dict.tsv')
UI_TSV = os.path.join(ROOT, 'work', 'ui_kr.tsv')
WORKSHEET = os.path.join(ROOT, 'work', 'dict_worksheet.tsv')

LINK_RE = re.compile(r'(\{1c\}\[\{1c\}I[0-9A-Fa-f]{8})(.*?)(\{1c\}\])')

# ui_kr·전법에 없는 하이퍼링크 표시텍스트 수동 매핑 (실기/기존 용어 기준).
MANUAL = {
    '武将データ編集': '무장 데이터 편집',
    'ＺＯＣ': 'ＺＯＣ',            # 지배영역(ZOC). 전각 그대로 = 게임 용어
    'いなご': '메뚜기 떼',         # 蝗害 이벤트
    '必殺コマンド': '필살 커맨드',
}


def load_glossary():
    """jp -> ko. 우선순위: MANUAL > 전법 > ui_kr(auto/override)."""
    g = {}
    if os.path.exists(UI_TSV):
        for ln in io.open(UI_TSV, encoding='utf-8'):
            p = ln.rstrip('\n').split('\t')
            if len(p) >= 8 and p[2].strip() and p[7].strip():
                g.setdefault(p[2].strip(), p[7].strip())
    g.update(SENPOU)
    g.update(MANUAL)
    return g


def read_rows():
    rows = []
    for ln in io.open(DICT_TSV, encoding='utf-8'):
        if ln.startswith('#'):
            continue
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 5 and p[0].isdigit():
            rows.append(p)  # block, index, bytes, jp, kr
    return rows


def koreanize_links(text, glossary, unresolved=None):
    """하이퍼링크 표시텍스트를 한글로 치환. id·구조 보존."""
    def repl(m):
        disp = U.normalize('NFC', m.group(2))   # 표시텍스트가 NFD(탁점 분리)라 정규화 후 조회
        ko = glossary.get(disp)
        if ko is None:
            if unresolved is not None:
                unresolved.add(disp)
            return m.group(0)          # 못 찾으면 원문 유지(잡히도록)
        return m.group(1) + ko + m.group(3)
    return LINK_RE.sub(repl, text)


def main():
    g = load_glossary()
    rows = read_rows()
    unresolved = set()
    n_links = 0
    with io.open(WORKSHEET, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# dict 번역 워크시트 — jp_klink 컬럼은 하이퍼링크 표시텍스트가 이미 한글이다.\n')
        f.write('# 번역은 kr 컬럼에. {1c}[{1c}I...{1c}] 링크 태그와 {N}{V:..}{05}{BTNxx}는 그대로 보존.\n')
        f.write('# block\tindex\tbytes\tjp_klink\tkr\n')
        for r in rows:
            n_links += len(LINK_RE.findall(r[3]))
            kl = koreanize_links(r[3], g, unresolved)
            f.write('\t'.join([r[0], r[1], r[2], kl, r[4]]) + '\n')
    print('glossary %d개, 항목 %d개, 링크 %d개' % (len(g), len(rows), n_links))
    print('해결 못한 표시텍스트: %d종' % len(unresolved))
    for d in sorted(unresolved):
        print('   미해결:', d)
    print('-> %s' % WORKSHEET)


if __name__ == '__main__':
    main()
