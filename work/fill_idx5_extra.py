# -*- coding: utf-8 -*-
"""work/idx5_extra_kr.tsv의 kr을 채운다. 용어는 기존 확정 번역과 전부 대조 완료(docs/15):
  - 지형 20종: work/ui_kr.tsv의 기존 확정 번역 그대로 재사용(草地=초원·砂地=모래·荒地=황야·
    本道=대로·桟道=잔도·渡=나루·岸=물가·崖=벼랑·都市=도시·関所=관문·港=항·間道=간도·
    土=땅·森=숲·川=하천·河=강·海=바다·湿地=습지·毒泉=독천, 浅瀬=여울은 facilities.py와 일치).
  - 전장시설 이름(화종·화구·화선·업화종·산악·유적·동작대): ui_kr.tsv auto 항목과 완전히 일치.
  - 병과 용어(기병·창병·극병·노병): e4_dict.tsv/e4_sys.tsv 확정 번역과 일치.
  - 설명문은 e4_dict.tsv의 같은 시설/병기 항목의 상세 설명(주위 N칸·아군 부대·병량 소비 경감
    등)에서 핵심 어휘를 그대로 가져와 예산(70B 안팎)에 맞게 압축했다.
"""
import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'idx5_extra_kr.tsv')

KR = {
    # ---- 전장시설 이름 (ui_kr.tsv 기존 확정과 동일) ----
    ('fac', 16, 'name'): '화종', ('fac', 18, 'name'): '화구', ('fac', 20, 'name'): '화선',
    ('fac', 22, 'name'): '업화종', ('fac', 26, 'name'): '산악', ('fac', 28, 'name'): '유적',
    ('fac', 30, 'name'): '동작대',
    # 시설 Lv 변형 — 8B 하드캡(한글 2음절+반각 " LvN" 4B = 정확히 8B)
    ('fac', 31, 'name'): '시장 Lv1', ('fac', 32, 'name'): '농장 Lv1', ('fac', 33, 'name'): '병영 Lv1',
    # 兵舎=병영(兵士=병사 충돌 회피), 鍛冶=대장간(단야 아님; ui_overrides 빈대장간수와 일치).
    # 대장간 Lv1=10B라 idx5 예산은 8→10 필요(레코드 내 카타카나 읽기만 바뀌고 구조 보존).
    ('fac', 34, 'name'): '대장간 Lv1', ('fac', 35, 'name'): '구사 Lv1',
    ('fac', 50, 'name'): '시장 Lv2', ('fac', 51, 'name'): '시장 Lv3',
    ('fac', 52, 'name'): '농장 Lv2', ('fac', 53, 'name'): '농장 Lv3',
    ('fac', 54, 'name'): '병영 Lv2', ('fac', 55, 'name'): '병영 Lv3',
    ('fac', 56, 'name'): '대장간 Lv2', ('fac', 57, 'name'): '대장간 Lv3',
    ('fac', 58, 'name'): '구사 Lv2', ('fac', 59, 'name'): '구사 Lv3',
    # ---- 전장시설 설명 (e4_dict.tsv 같은 항목의 상세설명 어휘를 압축) ----
    ('fac', 4, 'desc'): '주위 3칸 아군 부대 병량소비·피해 경감(진보다 큼)',
    ('fac', 6, 'desc'): '주위 2칸 적 부대에 매턴 화살 공격',
    ('fac', 7, 'desc'): '주위 3칸 적 부대에 매턴 연노 공격',
    ('fac', 10, 'desc'): '주위 2~3칸 적 부대에 매턴 투석 공격',
    ('fac', 12, 'desc'): '주위 2칸 아군 부대 기력 회복',
    ('fac', 14, 'desc'): '이민족의 거점',
    ('fac', 15, 'desc'): '도적의 거점',
    ('fac', 16, 'desc'): '인접 칸에 인화한다',
    ('fac', 17, 'desc'): '주위 2칸에 인화한다',
    ('fac', 18, 'desc'): '인화하며 3칸 구른다',
    ('fac', 19, 'desc'): '인화하며 5칸 구른다',
    ('fac', 20, 'desc'): '인접 칸에 인화. 수상 설치 가능',
    ('fac', 21, 'desc'): '인화하며 4칸 구른다. 건물 관통',
    ('fac', 22, 'desc'): '주위 2칸에 인화, 적 부대 혼란',
    ('fac', 24, 'desc'): '파괴 시 주위를 수공에 빠뜨림',
    # ---- 건설조건 ----
    ('fac', 31, 'cond'): '흡수 합병 가능', ('fac', 32, 'cond'): '흡수 합병 가능',
    ('fac', 33, 'cond'): '흡수 합병 가능', ('fac', 34, 'cond'): '흡수 합병 가능',
    ('fac', 35, 'cond'): '흡수 합병 가능', ('fac', 49, 'cond'): '1도시 1개만',
    # ---- 병장 설명 (기병·창병·극병·노병 = e4_dict/e4_sys 확정 용어) ----
    ('wpn', 0, 'desc'): '표준 장비 병장. 위력은 최약',
    ('wpn', 1, 'desc'): '기병에 유리하나 극병에 불리',
    ('wpn', 2, 'desc'): '창병에 유리하나 기병에 불리',
    ('wpn', 3, 'desc'): '2칸 앞에 화살 공격 가능',
    ('wpn', 4, 'desc'): '극병에 유리하나 창병에 불리',
    ('wpn', 5, 'desc'): '건물을 직접 공격하는 병기. 건물 내구를 깎는다',
    ('wpn', 6, 'desc'): '건물에 화살 공격하는 병기. 거점 병사를 깎는다',
    ('wpn', 7, 'desc'): '정란의 강화판. 투석 공격으로 내구·병사를 깎는다',
    ('wpn', 8, 'desc'): '충차의 강화판. 화염 방사로 건물 내구를 깎는다',
    ('wpn', 9, 'desc'): '표준 장비 함선',
    ('wpn', 10, 'desc'): '대형선. 이동력·장갑 모두 주가보다 강력',
    ('wpn', 11, 'desc'): '누선의 강화판. 투석 공격 가능',
    # ---- 지형 20 (work/ui_kr.tsv 기존 확정 번역과 동일, cap 4B 하드) ----
    ('ter', 0, 'name'): '초원', ('ter', 1, 'name'): '땅', ('ter', 2, 'name'): '모래',
    ('ter', 3, 'name'): '습지', ('ter', 4, 'name'): '독천', ('ter', 5, 'name'): '숲',
    ('ter', 6, 'name'): '하천', ('ter', 7, 'name'): '강', ('ter', 8, 'name'): '바다',
    ('ter', 9, 'name'): '황야', ('ter', 10, 'name'): '대로', ('ter', 11, 'name'): '잔도',
    ('ter', 12, 'name'): '나루', ('ter', 13, 'name'): '여울', ('ter', 14, 'name'): '물가',
    ('ter', 15, 'name'): '벼랑', ('ter', 16, 'name'): '도시', ('ter', 17, 'name'): '관문',
    ('ter', 18, 'name'): '항', ('ter', 19, 'name'): '간도',
    # ---- 관직 81번째 (item_names.py RANKS 관례와 동일) ----
    ('rank', 80, 'name'): '없음',
}


def main():
    lines = io.open(PATH, encoding='utf-8').read().split('\n')
    out = []
    filled = 0
    missing = []
    for ln in lines:
        if not ln or ln.startswith('#') or ln.startswith('table\t'):
            out.append(ln)
            continue
        p = ln.split('\t')
        key = (p[0], int(p[1]), p[2])
        if key in KR:
            p[6] = KR[key]
            filled += 1
        else:
            missing.append((key, p[5]))
        out.append('\t'.join(p))
    io.open(PATH, 'w', encoding='utf-8', newline='').write('\n'.join(out))
    print('filled %d' % filled)
    if missing:
        print('MISSING %d:' % len(missing))
        for k, jp in missing:
            print(' ', k, repr(jp))


if __name__ == '__main__':
    main()
