"""사용자 번역 TSV의 기계적 결함을 고쳐 정본 `work/tokki_kr.tsv`를 만든다.

출력 = 특기100 + 기교36 + **능력98** = 234줄.

## 고치는 것
1. **능력 98줄 전체를 entry5에서 다시 조립** — 사용자 TSV엔 특기 노드 66개만 있었다.
   (제가 테이블을 0xa7a4/66으로 잘못 잡아 앞쪽 32개를 빼고 뽑아 드린 탓.)
   또 사용자가 「特技「待伏」を…」의 한자를 그대로 두셨는데, 운반체 방식이라 한자 슬롯엔
   한글이 덧칠돼 있어 화면에 엉뚱한 한글이 뜬다(도움말 때 「자(字)」 병기 불가와 같은 이유).
   ★**조사를 같이 고쳐야 한다.** 「매복」+를 은 틀렸다(받침 있음 → 을).
     세션5에서 「정보을 통해」로 똑같이 데였다 — [[feedback_kr_patch_verification]].
2. **특기 白馬** — 「기사(騎射)」 한자병기 제거.
3. **기교 6줄** — 바이트 cap 40B 초과 → 구분자만 줄인 최소 수정(FIXUPS).
4. **특기 6줄** — 바이트는 통과했지만 **화면 폭 21.5 초과**로 잘림(WIDTH_FIXUPS).

## 두 종류의 예산을 둘 다 봐야 한다
- **바이트**(CAP) — 넘으면 옆 필드를 깔아뭉갠다. 크래시/데이터 파손.
- **화면 폭**(DISP_MAX) — 넘으면 조용히 잘린다. 바이트는 멀쩡한데 화면만 깨진다.
  ★실기 스크린샷 없이는 폭을 알 수 없다. 바이트만 보고 "통과"라고 하면 안 된다.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from encoding import Codec              # noqa: E402
from tokki_names import (TOKKI, GIKOU, STAT_KR, STAT_FULL,   # noqa: E402
                         LEVEL_KR, UNIT_KR)

# ★테이블마다 이름 사전이 다르다.
#   ⚠️처음에 전부 TOKKI로 찾아서 기교 36개가 몽땅 ''가 됐고, 빌더가 그 빈 문자열을
#     써서 ISO의 기교 이름을 널로 지워버렸다. ISO 되읽기 검증에서 잡았다.
NAMES = {'특기': TOKKI, '기교': GIKOU}

# 능력 98개는 사용자 TSV(특기 노드 66개뿐)가 아니라 **entry5에서 직접 읽어 조립**한다.
# 앞쪽 32개(능력치15·적성12·특기5)가 TSV에 아예 없었기 때문 — 실기에서 일본어로 남아 발각.
ENTRY5 = os.path.join(HERE, '..', 'work', 'entry5.bin')
NOU_BASE, NOU_STRIDE, NOU_COUNT = 0x9e64, 0x4a, 98
NOU_NAME, NOU_DESC = 0x00, 0x09

RE_STAT = re.compile(r'^([統武知政魅])\+5([低中高])$')
RE_APT = re.compile(r'^(槍兵|戟兵|弩兵|騎兵|兵器|水軍)([ＡＢ])$')

ELF = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"
SRC = os.path.join(HERE, '..', 'my files', 'tokki_desc_kr.tsv')

# ★텍스트 최대 = (첫 '살아있는' 다음 필드 오프셋 − 설명 오프셋) − 1.
#   널 종료자 자리를 반드시 뺀다. 안 빼서 cap이 1B씩 헐거웠던 적 있다.
#
# ★★다음 필드를 '옆 칸'이 아니라 **살아있는 필드**로 잡아야 한다. 레코드 꼬리엔 옛
#   레이아웃 찌꺼기가 남아 있어 옆 칸이 데이터처럼 보이지만 죽은 바이트다. 열별 고유값
#   개수로 갈랐다 — 찌꺼기는 종류 25~56(고엔트로피), 살아있는 필드는 종류 ≤9.
#
#   특기: 설명 +0x18 → +0x38~+0x5a 전부 종류25~56(찌꺼기), 첫 live = **+0x5b**(종류3)
#         ⇒ 0x5b − 0x18 − 1 = **66**
#   기교: 설명 +0x2a → 첫 live = **+0x53**(종류9 = 값 0~8이 정확히 4번씩 = **행 번호**)
#         ⇒ 0x53 − 0x2a − 1 = **40**
#         ⚠️처음에 +0x54(레벨 0~3)를 다음 필드로 봐서 41로 잡았다. 그러면 널이 +0x53의
#           행 번호를 0으로 덮어써 기교표 배치가 깨진다. (+0x55 금 u16, +0x57 기교P u16)
#   능력: 설명 +0x09 → +0x34~+0x3f가 98/98 널, 첫 live = **+0x40**(값 3종)
#         ⇒ 0x40 − 0x09 − 1 = **54**
#         ⚠️처음엔 30으로 잡았다. 66개 표본이 전부 같은 템플릿(30B)이라 +0x27이 100%
#           널로 보였을 뿐 — **표본 편향**이었다. 98개 전수로 다시 재니 능력치 노드가 35B다.
CAP = {'특기': 66, '기교': 40, '능력': 54}
# 이름칸 = 다음 필드(읽기/설명) 직전까지. 특기 4B / 기교 8B(+0x09 읽기) / 능력 8B(+0x09 설명)
NAME_CAP = {'특기': 4, '기교': 8, '능력': 8}

# ★★**바이트 예산을 통과해도 화면에서 잘린다.** 화면 열 폭이 따로 있다(2026-07-17 실기).
#   화면마다 동작이 다르다:
#     특기일람 = 고정폭 열, **잘라냄**  → 실기 33샘플로 역산: 안잘림 최대 21.5 / 잘림 최소 23.5
#                                        (두 집합이 안 겹침 = 폭이 원인 확정). 안전선 = **21.5**
#     기교표   = 고정폭 열, **잘라냄**  → 투석개발 20.0이 테두리에 딱 붙어 보임. 안전선 = **20.0**(여유0)
#     능력표   = **워드랩**             → 2줄로 흐름. 폭 제약 없음(19.5까지 확인)
#   ⚠️"능력표에서 워드랩되더라"를 전체로 일반화했다가 특기일람이 잘렸다.
#     한 화면 보고 다른 화면을 결론내지 말 것. [[feedback_kr_patch_verification]]
DISP_MAX = {'특기': 21.5, '기교': 20.0, '능력': None}


def width(s):
    """전각 단위 표시 폭. 전각 1.0 / 반각 ASCII 0.5."""
    return sum(0.5 if 0x20 <= ord(c) <= 0x7E else 1.0 for c in s)


# 기교 4줄이 cap 41B를 넘었다. 표현은 사용자 문안 그대로 두고 구분자만 줄인 최소 수정.
# 실제 인코더로 재서 전부 41B 이하 확인함.
# ★후보는 전부 실제 인코더로 재서 골랐다. 손으로 세지 말 것 — 이 표를 만들면서
#   손계산으로 3번 틀렸다. [[feedback_kr_patch_verification]]
FIXUPS = {
    # 「과」→「·」 + 「잔도 통행 피해」→「잔도 피해」          42B → 36B
    '難所行軍': '샛길·여울 통행 가능. 잔도 피해 없음',
    # 「으로」 제거                                        41B → 37B
    '兵糧襲撃': '창병 공격 시, 적 부대의 병량을 빼앗음',
    # 「, 」→공백 + 「사용 가능」→「사용가능」               41B → 39B
    '石造建築': '장애물「석벽」 시설「석병팔진」사용가능',
    # 「, 」→「·」 + 」시설 사이 공백 제거 + 「사용가능」.
    # 원문 「兵装「投石、闘艦」施設「投石台」」도 구분자가 없다.  43B → 40B
    '投石開発': '병장「투석·투함」시설「투석대」사용가능',
    # 「, 」→「·」 + 「사용가능」 + 「화계강화」               42B → 40B
    '爆薬錬成': '함정「업화종·업화구」사용가능. 화계강화',
    # 「자금」→「금」 + 「항구의 최대」→「항구」 + 「상한증가」   45B → 40B
    '港関拡張': '관문·항구 금·병량·병사·병장 상한증가',
}

# 특기일람에서 **화면 폭 21.5를 넘어 잘린** 6개. 바이트는 전부 통과했었다.
# 連環·眼力·傾国은 실기에서 잘린 게 확인됐고, 藤甲(24.5)은 더 길다.
# 補佐(22.5)·風水(22.0)는 회색지대(21.5~23.5)라 보수적으로 같이 줄인다.
WIDTH_FIXUPS = {
    '連環': '부대 계략 성공 시, 인접 부대에도 파급',        # 24.5 → 18.5 (「대상 부대의」는 함의)
    '藤甲': '화계 외 피해 절반 경감. 화계 피해는 2배',      # 24.5 → 19.5
    '眼力': '미발견 재야가 있으면 탐색으로 반드시 발견',      # 24.0 → 20.5
    '傾国': '남성만인 부대에 대한 계략 성공률이 2배',        # 23.5 → 19.0
    '補佐': '인간관계 없어도 지원 공격 가능(싫어함 제외)',    # 22.5 → 21.5 (조사 하나만)
    '風水': '소속 도시에 메뚜기떼·역병이 발생하지 않음',      # 22.0 → 21.0 (「에서」→「에」)
}


def has_batchim(syl):
    """한글 음절에 받침이 있나 → 을/를, 이/가 판별용."""
    return (ord(syl) - 0xAC00) % 28 != 0


def eul_reul(word):
    return '을' if has_batchim(word[-1]) else '를'


def nou_desc(kr_name):
    """능력 설명 템플릿. 사용자 문안을 cap 안으로 줄이고 조사를 맞춘 것."""
    return '특기「%s」%s 무장이 습득' % (kr_name, eul_reul(kr_name))


def cstr(blob, off, cap):
    end = blob.find(b'\x00', off, off + cap)
    if end < 0:
        end = off + cap
    return blob[off:end].decode('cp932')


def nou_rows():
    """능력 98개를 entry5에서 읽어 (오프셋, jp이름, kr이름, kr설명)로 조립.

    노드 3종:
      능력치 15 = 統武知政魅 × 低中高 — 「統+5低」/「70未満の統率を5上げる（最大70まで）」
      적성   12 = 6병과 × ＡＢ        — 「槍兵Ｂ」/「槍兵適性Ｃの武将をＢにする」
      특기   71                        — TOKKI + 습득 템플릿
    ★상한값(70/80/95)과 등급(Ａ/Ｂ/Ｃ)은 **원문에서 뽑는다**. 표로 또 적으면 어긋난다.
    """
    blob = open(ENTRY5, 'rb').read()
    rows = []
    for i in range(NOU_COUNT):
        off = NOU_BASE + i * NOU_STRIDE
        rec = blob[off:off + NOU_STRIDE]
        jp = cstr(rec, NOU_NAME, NOU_DESC - NOU_NAME)
        jd = cstr(rec, NOU_DESC, 0x40 - NOU_DESC)

        m = RE_STAT.match(jp)
        if m:
            st, lv = m.groups()
            lim = re.match(r'^(\d+)未満', jd).group(1)
            full = STAT_FULL[st]
            kn = '%s+5%s' % (STAT_KR[st], LEVEL_KR[lv])
            kd = '%s 미만인 %s%s 5 올림 （최대 %s까지）' % (lim, full, eul_reul(full), lim)
        else:
            m = RE_APT.match(jp)
            if m:
                un, gr = m.groups()
                g = re.search(r'適性([ＡＢＣ])の武将を([ＡＢＣ])にする', jd).groups()
                kn = '%s%s' % (UNIT_KR[un], gr)
                kd = '%s 적성 %s인 무장을 %s로' % (UNIT_KR[un], g[0], g[1])
            else:
                kn = TOKKI[jp]
                kd = nou_desc(kn)
        rows.append((off, jp, jd, kn, kd))
    return rows


def main():
    codec = Codec(ELF)
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    rep = io.open(sys.argv[2], 'w', encoding='utf-8')
    out.write('# 특기100+기교36+능력66 설명 한글 — 정본\n')
    out.write('table\tidx\toffset\t이름\t이름kr\tkrB\tcapB\tjp\tkr\n')

    fixed_nou = fixed_other = fixed_width = 0
    over, wide = [], []
    for ln in io.open(SRC, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if not ln or ln.startswith('#') or ln.startswith('table\t'):
            continue
        f = ln.split('\t')
        tbl, idx, off, name, jp = f[0], f[1], f[2], f[3], f[6]
        if tbl == '능력':
            continue          # 능력은 TSV 말고 entry5에서 98개를 통째로 조립한다(아래)
        kr = f[7].strip() if len(f) > 7 else ''
        krname = NAMES[tbl].get(name)
        if not krname:
            raise SystemExit('%s %s 의 한글 이름이 없다 — tokki_names.py 확인' % (tbl, name))

        if name == '白馬':
            kr = re.sub(r'\(騎射\)', '', kr)
            fixed_other += 1
        elif tbl == '기교' and name in FIXUPS:
            kr = FIXUPS[name]
            fixed_other += 1
        if tbl == '특기' and name in WIDTH_FIXUPS:
            kr = WIDTH_FIXUPS[name]
            fixed_width += 1

        n = len(codec.encode(kr))       # ★검사기 = 인코더
        if n > CAP[tbl]:
            over.append((tbl, idx, name, kr, n, CAP[tbl]))
        w = width(kr)
        if DISP_MAX[tbl] and w > DISP_MAX[tbl]:
            wide.append((tbl, name, kr, w, DISP_MAX[tbl]))
        out.write('%s\t%s\t%s\t%s\t%s\t%d\t%d\t%s\t%s\n'
                  % (tbl, idx, off, name, krname, n, CAP[tbl], jp, kr))

    # ---- 능력 98개 = entry5에서 통째로 조립 ----
    kinds = {'능력치': 0, '적성': 0, '특기': 0}
    for off, jp, jd, kn, kd in nou_rows():
        fixed_nou += 1
        kinds['능력치' if RE_STAT.match(jp) else
              '적성' if RE_APT.match(jp) else '특기'] += 1
        nb, db = len(codec.encode(kn, halfwidth_space=False)), len(codec.encode(kd))
        if nb > NAME_CAP['능력']:
            over.append(('능력', '-', jp, kn, nb, NAME_CAP['능력']))
        if db > CAP['능력']:
            over.append(('능력', '-', jp, kd, db, CAP['능력']))
        if DISP_MAX['능력'] and width(kd) > DISP_MAX['능력']:
            wide.append(('능력', jp, kd, width(kd), DISP_MAX['능력']))
        out.write('능력\t%d\t0x%04x\t%s\t%s\t%d\t%d\t%s\t%s\n'
                  % ((off - NOU_BASE) // NOU_STRIDE, off, jp, kn, db, CAP['능력'], jd, kd))

    rep.write('능력 %d줄 조립 %s / 특기·기교 수정 %d줄\n' % (fixed_nou, kinds, fixed_other))
    rep.write('\n능력 노드 3종 샘플:\n')
    for off, jp, jd, kn, kd in nou_rows()[:3] + nou_rows()[15:17] + nou_rows()[32:34]:
        rep.write('  %-8s → %-6s : %-34s %dB\n' % (jp, kn, kd, len(codec.encode(kd))))
    rep.write('\n===== cap 초과 (반드시 줄여야 함) =====\n')
    for o in over:
        rep.write('  %s idx%s %s : %dB > cap %dB\n    %s\n' % (o[0], o[1], o[2], o[4], o[5], o[3]))
    rep.write('\n총 cap 초과 %d건\n' % len(over))

    rep.write('\n===== 화면 폭 초과 (바이트를 통과해도 화면에서 잘린다) =====\n')
    for t, nm, k, w, lim in wide:
        rep.write('  %s %s : 폭 %.1f > 안전선 %.1f\n    %s\n' % (t, nm, w, lim, k))
    rep.write('총 폭 초과 %d건 (폭 수정 적용 %d건)\n' % (len(wide), fixed_width))

    rep.write('\n테이블별 최대 폭 / 안전선:\n')
    for t in ('특기', '기교', '능력'):
        ws = [width(f[8]) for f in
              (l.rstrip('\n').split('\t') for l in io.open(sys.argv[1], encoding='utf-8'))
              if len(f) > 8 and f[0] == t]
        rep.write('  %s: 최대 %.1f / 안전선 %s\n'
                  % (t, max(ws), DISP_MAX[t] if DISP_MAX[t] else '없음(워드랩)'))
    rep.close()


if __name__ == '__main__':
    main()
