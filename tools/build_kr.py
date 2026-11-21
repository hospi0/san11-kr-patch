# -*- coding: utf-8 -*-
"""한글 패치 빌드: 무장 로스터(52벌) + 지명 105곳 + UI 2,572개.

전부 ISO 사본 in-place 바이트 패치(크기 불변). 재조립 없음.

  1. s11pkres 아틀라스: 쓰이는 한글 음절을 운반체 한자 슬롯에 그린다
  2. s11pkres 로스터 52벌: 姓/名/字 필드를 한글 운반체 코드로 교체
  3. s11pkres 엔트리5 지명: 都市42 · 関10 · 港35 · 州12 · 地方6 이름 필드 교체
  4. SLPM_667.01 UI: work/ui_kr.tsv의 번역을 슬롯에 in-place 교체

★ 로스터는 52벌이지만 **레이아웃이 두 종류**다(2026-07-17 실측):
    그룹A 16벌  stride 0x98  姓 +0x58 / 名 +0x5d / 字 +0x62   = PUK 시나리오
    그룹B 36벌  stride 0xcb  姓 +0x00 / 名 +0x05 / 字 +0x0a   = 본편 시나리오
  于禁文則 시그니처 52개 중 앞 16개가 A, 뒤 36개가 B다.
    A base = sig - 6*0x98 - 0x58     B base = sig - 6*0xcb
  ⚠️ 두 그룹은 **내용도 다르다**. idx 832부터 A엔 水滸伝 보너스 무장(宋江·
     盧俊義)이 있고 B엔 いに３３ 류 placeholder가 있다. 그래서 번역본을
     일괄 주입하면 안 되고, **사본마다 자기 바이트를 읽어 번역**해야 한다.

Usage: python build_kr.py <iso사본> [font.ttc] [ink_h] [weight]
"""
import os
import struct
import sys

import numpy as np
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from encoding import Codec                                # noqa: E402
from font_build import render_fixed, autofit_size, SS     # noqa: E402
from iso import walk, find                                # noqa: E402
from kr_names import translate_name, to_hangul            # noqa: E402
from facilities import find_facility_offsets, kr_of as fac_kr   # noqa: E402
from fac_desc import (find_desc_offsets, kr_bytes as desc_kr,   # noqa: E402
                      check_prefix_locks)
import help_reloc                                               # noqa: E402

ATLAS_IN_S11 = 0x49810
PER, PIX, YBASE = 224, 200, 19

SIG = bytes.fromhex('98b00000008bd600000095b691a5')   # 于禁文則 (로스터 idx 6)
FIELD, N_REC = 5, 900
NAME_HOOK_ON = True       # 2026-11-21 이름 입력 한글 조합(tools/name_hook.py, docs/17) — OVERLAY1 + SLPM 동굴
JOSA_HOOK_ON = True       # 2026-11-21 진짜 동굴로 옮김(josa_hook.CAVES — 실행 파일+OVERLAY1/2+RAM 무참조)
EXTRA_REC = (1000, 1001)                                   # 범용 무장 칸(도적·오환)
EXTRA_NAMES = {'賊': '적', '将': '장', '烏丸': '오환', '武将': '무장'}
# (라벨, stride, 姓오프셋, 시그니처 개수)
GROUP_A = ("A", 0x98, 0x58, 16)
GROUP_B = ("B", 0xcb, 0x00, 36)

ENTRY5 = 0x1e9800          # s11pkres 안 엔트리5(지명 테이블) 파일 오프셋
REPO = os.path.dirname(HERE)
S11_SRC = r"C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan)/s11pkres.bin"


def read_field(buf, off):
    """5바이트 필드 → 문자열([Gf0xx] 표기). SJIS 아니면 None."""
    seg = buf[off:off + FIELD]
    out, i = [], 0
    while i < FIELD - 1:
        if seg[i] == 0:
            break
        hi, lo = seg[i], seg[i + 1]
        if 0xf0 <= hi <= 0xf1:
            out.append("[G%02x%02x]" % (hi, lo))
        else:
            try:
                out.append(bytes([hi, lo]).decode("cp932"))
            except Exception:
                return None
        i += 2
    return "".join(out)


def load_places_kr():
    rows = []
    with open(os.path.join(REPO, "work/places_kr.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 5 and p[4]:
                rows.append((int(p[1], 16), p[2], p[4]))
    return rows


ENTRY5_SIZE = 0xbab8
# entry5 클린 이름 테이블 (docs/10): (라벨, base, stride, 개수). 이름 = 레코드 맨 앞 [SJIS]\0.
# 병장 테이블은 剣(0x3ac2)부터 12개(剣槍戟弩軍馬衝車井闌投石木獣走舸楼船闘艦). 皇帝(0x41ca)는 제외.
ENTRY5_TABLES = [("병장", 0x3ac2, 0x96, 12), ("관직", 0x4382, 0x2e, 80)]


def load_entry5_names(s11):
    """entry5 병장8 + 관직80 이름 → (rel_off, jp, kr). 1:1 독음만(가이지·비1:1 스킵)."""
    ent = s11[ENTRY5:ENTRY5 + ENTRY5_SIZE]

    def name_at(off):
        """(문자열, 바이트수). 가이지·비SJIS 이름은 (None, 0)."""
        out, j = [], off
        while j < len(ent) - 1:
            hi, lo = ent[j], ent[j + 1]
            if hi == 0:
                break
            if 0xf0 <= hi <= 0xf1:
                return None, 0         # 가이지 포함 이름은 건드리지 않음
            try:
                ch = bytes([hi, lo]).decode("cp932")
            except Exception:
                return None, 0
            if len(ch) != 1:
                return None, 0
            out.append(ch); j += 2
        return "".join(out), j - off

    rows, skip = [], []
    for label, base, stride, cnt in ENTRY5_TABLES:
        for k in range(cnt):
            off = base + k * stride
            nm, nb = name_at(off)
            if not nm:
                continue
            kr = to_hangul(nm)
            if len(kr) != len(nm):     # 두음법칙 등으로 1:1 깨짐 → 사람 확인 필요
                skip.append((label, hex(off), nm, kr))
                continue
            rows.append((off, nm, kr, nb))
    return rows, skip


# 시나리오 제목 — 시나리오 컨테이너 idx6~19의 rel 0x5f (본체8 + PK6).
# 제목 필드 = 0x5f..0x6f(17B), 산문은 rel 0x70부터 → 산문 불변, 제목만 in-place.
# 사용자 확정 번역(2026-07-17 세션6). 전부 ≤16B(8음절) 예산 내.
SCENARIO_TITLES = {
    6: "황건의 난", 7: "반동탁연합", 8: "군웅할거", 9: "관도대전", 10: "삼고초려",
    11: "유비입촉", 12: "남만정벌", 13: "영웅집결", 14: "하진포위망", 15: "시대의 패자",
    16: "여포토벌전", 17: "원가의 싸움", 18: "적벽대전", 19: "한중쟁탈전",
}
TITLE_REL = 0x5f
TITLE_FIELD = 0x11        # 0x5f..0x6f — 넘으면 산문(0x70) 침범


# ── 특기100 · 기교36 · 능력66 (entry5) ─────────────────────────────────
# 테이블(analysis/table_columns.py에서 전수 열별통계로 확정):
#   특기 base 0x5210 stride 0x5d ×100 → 0x7664 (기교 base와 정확히 맞닿음)
#   기교 base 0x7664 stride 0x5c × 36 → 0x8354 (3탭 × 3행 × 4레벨)
#   능력 base 0x9e64 stride 0x4a × 98 → 0xbab8 (= entry5 크기와 정확히 일치)
#        = 특기노드 71 + 능력치 15(統武知政魅 × 低中高) + 병과적성 12(6병과 × ＡＢ)
#        ⚠️처음에 0xa7a4/66으로 잡아 앞쪽 32개를 통째로 놓쳤다(실기에 「統+5低」「戟兵Ｂ」가
#          일본어로 남아 사용자가 발견). 표본 편향 — [[feedback_scan_coverage_and_detectors]]
#
# (이름오프, 이름cap, 설명오프, 설명cap) — cap은 **텍스트 최대**(널 자리 뺀 값).
# ★cap의 근거 = '첫 살아있는 필드'까지의 거리 − 1. 레코드 꼬리엔 옛 레이아웃 찌꺼기가
#   남아 있어 옆 칸이 데이터처럼 보이므로, 열별 고유값 개수로 갈랐다
#   (찌꺼기 = 종류 25~56 고엔트로피 / 살아있는 필드 = 종류 ≤9).
#   특기: 첫 live = +0x5b(종류3)          ⇒ 0x5b−0x18−1 = 66
#   기교: 첫 live = **+0x53**(종류9 = 0~8이 4번씩 = **행 번호**) ⇒ 0x53−0x2a−1 = 40
#         ⚠️+0x54(레벨 0~3)를 경계로 보면 41이 되는데, 그러면 널이 행 번호를 0으로
#           덮어써 기교표 배치가 깨진다. (+0x55 금 u16, +0x57 기교P u16)
#   능력: 설명 +0x09 → +0x34~+0x3f가 98/98 널, 첫 live = **+0x40** ⇒ 0x40−0x09−1 = **54**
#         ⚠️"cap 30"으로 잡았던 건 66개 표본이 전부 같은 템플릿(30B)이라 +0x27이 100% 널로
#           보였기 때문. 98개 전수로 재니 능력치 노드 설명이 35B다.
TOKKI_SPEC = {
    "특기": (0x00, 4, 0x18, 66),
    "기교": (0x00, 8, 0x2a, 40),
    "능력": (0x00, 8, 0x09, 54),
}


# ── 아이템 52벌 · 작위 10 (analysis/item_rank_cols.py에서 전수 통계로 확정) ────
# 아이템 = 시나리오 컨테이너 52벌(로스터와 같은 구조). 앵커 = 倚天の剣 = 슬롯 idx 8.
#   ⚠️사본 52벌의 테이블 바이트는 28종으로 다르다(시나리오별 스탯) → **사본마다 자기
#     바이트를 읽어 번역**한다(로스터와 같은 이유. 일괄 주입 금지).
#   레코드 0x39(57B): +0x00 이름 ≤12B(★+0x0c가 50/50 널) · +0x0d 읽기(★50/50 0x83)
ITEM_STRIDE, ITEM_COUNT, ITEM_NAME_CAP = 0x39, 50, 12
ITEM_GRP = [(list(range(6, 22)), 0x253f5),                      # 그룹A 16벌
            (list(range(24, 30)) + list(range(32, 62)), 0x7f40a)]  # 그룹B 36벌
# 작위 = entry5 0x41ca stride 0x2c × 10 → 0x4382(관직 base)에서 정확히 끝남.
#   +0x00 이름 ≤10B (★+0x0b가 10/10 0x83 = 읽기 시작). SLPM엔 없다(entry5 전용).
RANK_BASE, RANK_STRIDE, RANK_COUNT, RANK_NAME_CAP = 0x41ca, 0x2c, 10, 10


def _cstr(buf, off, cap):
    e = buf.find(b"\x00", off, off + cap)
    if e < 0:
        e = off + cap
    try:
        return buf[off:e].decode("cp932")
    except UnicodeDecodeError:
        return None


def load_item_names(s11, sec, tab):
    """52벌 사본마다 자기 이름을 읽어 번역 → [(파일오프셋, jp, kr)]"""
    from item_names import ITEMS                       # noqa: E402
    rows = []
    for idxs, anchor in ITEM_GRP:
        for i in idxs:
            eoff = tab[i][0] * sec
            base = anchor - 8 * ITEM_STRIDE
            for k in range(ITEM_COUNT):
                o = eoff + base + k * ITEM_STRIDE
                nm = _cstr(s11, o, ITEM_NAME_CAP)
                if not nm:
                    continue
                kr = ITEMS.get(nm)
                if not kr:
                    raise SystemExit("아이템 번역 없음: %r (엔트리 %d)" % (nm, i))
                rows.append((o, nm, kr))
    return rows


def load_rank_names(s11):
    from item_names import RANKS                       # noqa: E402
    rows = []
    for k in range(RANK_COUNT):
        o = ENTRY5 + RANK_BASE + k * RANK_STRIDE
        nm = _cstr(s11, o, RANK_NAME_CAP + 1)
        kr = RANKS.get(nm)
        if not kr:
            raise SystemExit("작위 번역 없음: %r @0x%x" % (nm, o))
        rows.append((o, nm, kr))
    return rows


def load_kokugo_names(s11, sec, tab):
    """국호 51종 × 52벌 (시나리오 컨테이너) → [(파일오프셋, jp, kr)]

    세션22 발견: 「蜀군입니다」처럼 세력 표시명이 일본 한자로 남던 원인.
    ⚠️아이템과 **같은 컨테이너지만 rel 오프셋도 그룹 나눔도 다르다**(16/14/22).
      그래서 ITEM_GRP를 재사용하지 않고, rel 3종을 컨테이너 시작에서 직접 더한다.
    ⚠️사본마다 설명문이 다른 판본이 섞여 있으므로(길이 84/86칸) **사본마다 자기
      바이트를 읽어 조회**한다 — 로스터·아이템과 같은 이유. 일괄 주입 금지.
    """
    import kokugo_names as kk                        # noqa: E402
    rows = []
    starts = sorted({t[0] * sec for t in tab})
    for rel in kk.RELS:
        for base in starts:
            o0 = base + rel
            if o0 + kk.STRIDE > len(s11):
                continue
            # 이 컨테이너에 국호 테이블이 실제로 있는지 확인(앵커 = 첫 칸이 魏)
            if _cstr(s11, o0, kk.NAME_CAP + 1) != '魏':
                continue
            for k in range(200):                     # 84/86칸 + 여유
                o = o0 + k * kk.STRIDE
                if s11[o] == kk.SENTINEL:            # 테이블 끝 센티넬
                    break
                nm = _cstr(s11, o, kk.NAME_CAP + 1)
                if not nm or not nm.strip():
                    break
                kr = kk.kr_of(nm)
                if kr is None:                       # 자리표시자 = 건너뜀
                    continue
                # 설명문(+0x12)도 같이 싣는다. 원문 길이를 함께 넘겨 **옛 꼬리를
                # 널로 덮을** 수 있게 한다(찌꺼기가 남으면 다음 파서가 어긋난다).
                d0 = o + kk.DESC_OFF
                de = s11.find(b"\x00", d0, d0 + kk.DESC_CAP)
                old_len = (de - d0) if de >= 0 else kk.DESC_CAP
                rows.append((o, nm, kr, kk.desc_of(nm), old_len))
    return rows


def load_senpou_names(s11):
    """전법 = entry5 0x8354 stride 0x38 × 32 → 0x8a54 (세션9 발견. tools/senpou_names.py)

    32슬롯 중 19개만 실사용이고 19~31은 `戦法19` 플레이스홀더 = **번역하지 않고 건너뛴다**
    (빈 값을 쓰면 원본이 널로 지워진다 — 세션7 기교 이름 사고).
    """
    from senpou_names import SENPOU, BASE, STRIDE, COUNT, NAME_CAP, NAME_OFF  # noqa: E402
    rows = []
    for k in range(COUNT):
        o = ENTRY5 + BASE + k * STRIDE + NAME_OFF
        nm = _cstr(s11, o, NAME_CAP + 1)
        kr = SENPOU.get(nm)
        if not kr:
            continue                       # 플레이스홀더(戦法19…) = 원본 유지
        rows.append((o, nm, kr))
    if not rows:
        raise SystemExit("전법 테이블을 못 읽었다 — entry5 0x8354 레이아웃 확인 필요")
    return rows


def load_tokki_kr():
    """work/tokki_kr.tsv → [(테이블, entry5상대오프셋, jp이름, kr이름, kr설명)]"""
    import io as _io
    p = os.path.join(REPO, "work/tokki_kr.tsv")
    if not os.path.exists(p):
        return []
    rows = []
    for line in _io.open(p, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or line.startswith("table\t"):
            continue
        f = line.split("\t")
        rows.append((f[0], int(f[2], 16), f[3], f[4], f[8]))
    return rows


def load_scenario_titles(s11):
    """(제목_파일오프셋, idx, 한글). 컨테이너 base = LINK 섹터 * 섹터크기."""
    sec = struct.unpack("<I", s11[8:12])[0]
    rows = []
    for idx, kr in SCENARIO_TITLES.items():
        base = struct.unpack_from("<I", s11, 0x10 + idx * 8)[0] * sec
        rows.append((base + TITLE_REL, idx, kr))
    return rows


# 시나리오 개요문·세력공략문 — docs/14. tools/extract_scenario.py가 만든
# work/scenario_kr.tsv를 읽는다. 컨테이너 idx6~21(16개), 고정 레이아웃:
#   개요문 rel 0x70..0x1a2(306B, 꼬리 24B는 실측상 항상 0 → 안전상 282B로 제한)
#   공략문 rel 0x275 + slot*0x138, 슬롯 = [텍스트 최대 311B][flag 1B, 불변]
SCN_OVERVIEW_REL, SCN_OVERVIEW_CAP = 0x70, 282
SCN_BRIEF_BASE, SCN_BRIEF_STRIDE, SCN_BRIEF_TEXT_CAP = 0x275, 0x138, 311
# idx20·21 제목은 SCENARIO_TITLES에 없다(세션6이 idx6~19만 확정) → scenario_kr.tsv가 담당.
SCN_TITLE_REL, SCN_TITLE_FIELD = TITLE_REL, TITLE_FIELD


def load_scenario_kr(s11):
    """work/scenario_kr.tsv -> (파일오프셋, idx, section, jp, kr, cap).
    kr이 빈 줄은 스킵(원본 유지)."""
    p = os.path.join(REPO, "work/scenario_kr.tsv")
    if not os.path.exists(p):
        return []
    sec = struct.unpack("<I", s11[8:12])[0]
    bases = {}
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("idx\t"):
                continue
            idx_s, section, slot_s, flag_s, jp, kr = line.rstrip("\n").split("\t")
            if not kr:
                continue
            idx = int(idx_s)
            if idx not in bases:
                bases[idx] = struct.unpack_from("<I", s11, 0x10 + idx * 8)[0] * sec
            base = bases[idx]
            if section == "title":
                rows.append((base + SCN_TITLE_REL, idx, section, jp, kr, SCN_TITLE_FIELD - 1))
            elif section == "overview":
                rows.append((base + SCN_OVERVIEW_REL, idx, section, jp, kr, SCN_OVERVIEW_CAP))
            elif section == "brief":
                off = base + SCN_BRIEF_BASE + int(slot_s) * SCN_BRIEF_STRIDE
                rows.append((off, idx, section, jp, kr, SCN_BRIEF_TEXT_CAP))
            else:
                raise SystemExit("scenario_kr.tsv: 알 수 없는 section %r" % section)
    return rows


def load_idx5_extra_kr():
    """work/idx5_extra_kr.tsv -> (entry5상대오프셋, table, jp, kr, budget).
    docs/15: idx5(=entry5) 안에서 기존 파이프라인이 안 덮는 필드(전장시설·병장·지형·관직81).
    PC JPN/KOR(도원결의) 바이트 diff를 구조 오라클로 확정(번역문은 안 씀). kr 빈 줄은 스킵."""
    p = os.path.join(REPO, "work/idx5_extra_kr.tsv")
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("table\t"):
                continue
            table, k, field, off, budget, jp, kr = line.rstrip("\n").split("\t")
            if not kr:
                continue
            rows.append((int(off, 16), table, jp, kr, int(budget)))
    return rows


def load_ui_kr():
    """(파일오프셋, 원문, 한글, 예산). 번역 안 된 것(TODO)은 뺀다."""
    rows = []
    with open(os.path.join(REPO, "work/ui_kr.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 9 and p[7] and not p[8].startswith("TODO"):
                rows.append((int(p[0], 16), p[2], p[7], int(p[5])))
    return rows


def _write_boxes(w, base_off, tex, texw, boxes):
    """텍스처 전체가 아니라 **박스 사각형만** 써넣는다.

    ★★한 텍스처를 두 도구가 나눠 쓰는 경우가 있다 — 일기토 단어 텍스처
      0x04b36990 은 `battle_words`(단어 24칸)와 `ornate_words`('합') 둘 다의
      대상이다. 두 도구 모두 **원본 s11pkres에서 읽어** 자기 박스만 고친
      **전체 텍스처**를 돌려주므로, 통째로 쓰면 나중에 쓴 3j가 3i의 결과를
      지워 버린다. 세션22 빌드에서 실제로 일기토 단어 24칸이 전부 일본어로
      되돌아갔고(실기에서 攻撃/闘志/防御/一発로 확인됨), 각 도구의 미리보기는
      멀쩡해서 빌드 로그·미리보기만으로는 안 잡혔다.
      → 박스만 쓰면 이 충돌 자체가 성립하지 않는다.
    """
    for b in boxes:
        x, y, bw_, bh = b[:4]
        for row in range(y, y + bh):
            w.seek(base_off + row * texw + x)
            w.write(tex[row, x:x + bw_].tobytes())


def main():
    iso_path = sys.argv[1]
    fontpath = sys.argv[2] if len(sys.argv) > 2 else "C:/Windows/Fonts/batang.ttc"
    ink_h = float(sys.argv[3]) if len(sys.argv) > 3 else 18.0
    weight = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7

    f, vol, entries = walk(iso_path)
    s11_off = find(entries, "S11PKRES.BIN")[1] * 2048
    elf_off = find(entries, "SLPM_667.01")[1] * 2048
    f.close()
    print("ISO: S11PKRES.BIN @%#x  SLPM_667.01 @%#x" % (s11_off, elf_off))

    with open(iso_path, "rb") as r:
        r.seek(elf_off); elf = r.read(5242752)
    tmp = os.path.join(HERE, "_elf.tmp")
    open(tmp, "wb").write(elf)
    codec = Codec(tmp)
    os.remove(tmp)

    s11 = open(S11_SRC, "rb").read()
    offs, i = [], s11.find(SIG)
    while i != -1:
        offs.append(i); i = s11.find(SIG, i + 1)
    if len(offs) != 52:
        raise SystemExit("于禁 시그니처가 52벌이 아니다: %d" % len(offs))

    # ---- 사본마다 자기 이름을 읽어 번역 ----
    copies = []            # (base, stride, sei_off, [(rec, sKR, mKR, zKR)])
    warns = []
    for label, stride, sei_off, count in (GROUP_A, GROUP_B):
        grp = offs[:16] if label == "A" else offs[16:]
        assert len(grp) == count
        for o in grp:
            base = o - 6 * stride - sei_off
            recs = []
            for n in range(N_REC):
                r = base + n * stride + sei_off
                js, jm, jz = read_field(s11, r), read_field(s11, r + 5), read_field(s11, r + 10)
                if js is None or jm is None or jz is None:
                    warns.append((label, hex(base), n, "필드 파싱 실패"))
                    continue
                if not (js or jm):
                    continue                      # 빈 슬롯
                ks, km, kz, w = translate_name(js, jm, jz)
                if w:
                    warns.append((label, hex(base), n, "%s%s: %s" % (js, jm, w)))
                    continue
                recs.append((n, ks, km, kz))
            # ★범용 무장 1000·1001번(도적 장수·오환 무장) — 0~899 밖이라 일본어로 남아 있었다(2026-11-21 전수 조사).
            #   5바이트 칸(2음절)이라 한자 음 그대로.
            for n in EXTRA_REC:
                r = base + n * stride + sei_off
                js, jm, jz = read_field(s11, r), read_field(s11, r + 5), read_field(s11, r + 10)
                if js in EXTRA_NAMES and jm in EXTRA_NAMES:
                    recs.append((n, EXTRA_NAMES[js], EXTRA_NAMES[jm], EXTRA_NAMES.get(jz, jz or "")))
            copies.append((base, stride, sei_off, recs))
    print("로스터 사본 %d벌 (A16 stride0x98 / B36 stride0xcb), 레코드 %d개"
          % (len(copies), sum(len(c[3]) for c in copies)))
    if warns:
        print("⚠️ 번역 경고 %d건 (해당 이름은 건드리지 않음)" % len(warns))
        for w in warns[:10]:
            print("   ", w)

    places = load_places_kr()
    ui = load_ui_kr()
    e5names, e5skip = load_entry5_names(s11)
    scn_titles = load_scenario_titles(s11)
    print("시나리오 제목 %d개 (컨테이너 idx6~19)" % len(scn_titles))
    scn_kr = load_scenario_kr(s11)
    if scn_kr:
        from collections import Counter as _C2
        print("시나리오 개요·공략문 %d개 %s" % (len(scn_kr), dict(_C2(r[2] for r in scn_kr))))
    idx5_extra = load_idx5_extra_kr()
    if idx5_extra:
        from collections import Counter as _C3
        print("idx5 잔여필드 %d개 %s" % (len(idx5_extra), dict(_C3(r[1] for r in idx5_extra))))
    tokki = load_tokki_kr()
    if tokki:
        from collections import Counter as _C
        print("특기·기교·능력 %d개 %s" % (len(tokki), dict(_C(t[0] for t in tokki))))
    else:
        print("⚠️ work/tokki_kr.tsv 없음 — 특기·기교·능력 건너뜀")

    _sec = struct.unpack("<I", s11[8:12])[0]
    _n = struct.unpack("<I", s11[4:8])[0]        # ⚠️LINK: 0x04 개수 / 0x08 섹터크기
    _tab = [struct.unpack("<II", s11[0x10 + i * 8: 0x18 + i * 8]) for i in range(_n)]
    items = load_item_names(s11, _sec, _tab)
    ranks = load_rank_names(s11)
    print("아이템 %d칸(52벌 × %d슬롯, 고유 %d종) · 작위 %d개"
          % (len(items), ITEM_COUNT, len({r[1] for r in items}), len(ranks)))
    senpou = load_senpou_names(s11)
    print("전법 %d개(32슬롯 중 실사용, 고유 %d종)"
          % (len(senpou), len({r[1] for r in senpou})))
    kokugo = load_kokugo_names(s11, _sec, _tab)
    print("국호 %d칸(52벌, 고유 %d종)" % (len(kokugo), len({r[1] for r in kokugo})))
    print("지명 %d곳, UI %d개, entry5 이름(병장·관직) %d개%s"
          % (len(places), len(ui), len(e5names),
             (" (1:1 스킵 %d)" % len(e5skip)) if e5skip else ""))
    for s in e5skip:
        print("   ⚠️ 1:1불일치 스킵:", s)

    # 시설(施設) 이름 — 정본 매칭 + null종료 + 비CJK직전. 모든 복사본 위치.
    ent5 = s11[ENTRY5:ENTRY5 + ENTRY5_SIZE]
    fac_rows = []               # (rel_off, jp, kr, nbytes)
    for off, jp, nb in find_facility_offsets(ent5):
        kr, note = fac_kr(jp, to_hangul)
        if note in ("1:1불일치", "글자수 불일치(예산위험)"):
            print("   ⚠️ 시설 스킵:", jp, kr, note); continue
        fac_rows.append((off, jp, kr, nb))
    print("시설 %d위치(고유 %d종)" % (len(fac_rows), len({r[1] for r in fac_rows})))

    # 시설 효과 설명(산문) — 완전 문자열 매칭, 반각공백 예산맞춤. 전 복사본.
    desc_rows = []              # (rel_off, jp, kr_bytes, budget)
    # ★꼬리공유 잠금 게이트 — 다른 시설이 이 문자열의 중간을 자기 시작점으로 읽는다.
    #   어긋나면 그쪽 화면에서 첫 글자가 깨진다(2026-07-29 「토루 효과」 사고).
    for why in check_prefix_locks(codec):
        raise SystemExit("시설 설명 꼬리공유 위반 — " + why)
    for off, jp, bud in find_desc_offsets(ent5):
        b, kr = desc_kr(jp, codec)
        if b is None:
            print("   ⚠️ 설명 인코딩실패:", kr); continue
        if len(b) + 1 > bud:
            print("   ⚠️ 설명 예산초과 스킵:", jp, "->", kr); continue
        desc_rows.append((off, jp, b, kr))
    print("시설 설명 %d위치(고유 %d종)" % (len(desc_rows), len({r[1] for r in desc_rows})))

    # 하단바 도움말(idx=3) — 리빌드된 entry3_kr을 중복 엔트리 자리로 이사시킨다.
    # (반각 가나 1B → 한글 2B라 커져서 제자리 패치가 불가능. help_reloc 주석 참조.)
    help_path = os.path.join(REPO, "work/entry3_kr.bin")
    help_plan = None
    if os.path.exists(help_path):
        help_plan = help_reloc.plan(s11, open(help_path, "rb").read(), target=3)
        if help_plan["mode"] == "inplace":
            print("도움말 idx=3: %d B → 섹터 %d **제자리**(%d섹터, 원래 할당 그대로 = 디스크 배치 불변)"
                  % (len(help_plan["data"]), help_plan["sector"], help_plan["need"]))
        else:
            print("도움말 idx=3: %d B → 섹터 %d로 이사(%d섹터). 자리 = idx %d(idx %d와 내용동일, %d섹터 할당)"
                  % (len(help_plan["data"]), help_plan["sector"], help_plan["need"],
                     help_plan["victim"], help_plan["twin"], help_plan["victim_alloc"]))
    else:
        print("⚠️ work/entry3_kr.bin 없음 — 도움말 건너뜀 (tools/build_help.py 먼저)")

    # ---- 쓰이는 음절 ----
    # ★★번역문을 새로 넣는 곳이 생기면 **반드시 여기에도 등록해야 한다.** 안 하면 그 음절의
    #   운반체 한자 슬롯에 글리프가 안 그려져 **화면에 원본 한자가 그대로 비쳐 나온다**
    #   (「죽게 됩니다」→「죽게 喫니다」·「바꿀 수」→「바菓 수」). 빌드도 되읽기도 전부 통과하므로
    #   **실기에서만 드러난다** — 세션8이 entry4 파이프라인을 붙이며 이걸 빠뜨려 106자가 깨졌다.
    #   ※텍스트 삽입 경로(build_e4/build_help/entry5/…)와 글리프 경로는 별개다. 둘 다 손대라.
    syl = set()
    import io as _io

    def _syl_from_tsv(path, col=4):
        s = set()
        if not os.path.exists(path):
            return s
        for line in _io.open(path, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) > col and p[0].isdigit():
                s |= {c for c in p[col] if "가" <= c <= "힣"}
        return s

    if help_plan:                      # 도움말 번역문에 쓰인 음절도 글리프가 필요하다
        syl |= _syl_from_tsv(os.path.join(REPO, "work/help_kr.tsv"))
        # entry3 part1(0~415, 호칭·어미 조립 테이블)의 안전 예외 3개(msg 0·6·14)는 TSV가 아니라
        # build_help.py에 하드코딩돼 있어 위 스캔에 안 잡힌다 — 여기서 직접 끌어와야 한다.
        try:
            import build_help as _bh
            _reps = list(_bh.PART1_WORD_REPL) + [
                r for rs in _bh.PART1_MSG_REPL.values() for r in rs]
            syl |= {c for _old, rep in _reps for c in rep if "가" <= c <= "힣"}
        except Exception as e:
            print("⚠️ build_help.PART1_WORD_REPL 음절 수집 실패:", e)
    # entry4(LS11) 번역문 — sys·dict·bio·tutorial·kessen·dialogue. 미번역 TSV는 kr이 비어 있어
    # 자연히 0자를 낸다. 새 e4 TSV를 번역하면 여기 자동으로 잡힌다.
    e4_syl = set()
    for f in sorted(os.listdir(os.path.join(REPO, "work"))):
        if f.startswith("e4_") and f.endswith(".tsv"):
            e4_syl |= _syl_from_tsv(os.path.join(REPO, "work", f))
    if e4_syl:
        print("entry4 번역문 음절 %d자 (work/e4_*.tsv)" % len(e4_syl))
    syl |= e4_syl
    for _, _, _, recs in copies:
        for _, s, m, z in recs:
            syl |= {c for c in (s + m + z) if "가" <= c <= "힣"}
    for _, _, k in places:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k, _ in ui:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k, _ in e5names:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k, _ in fac_rows:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, _, k in desc_rows:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k in scn_titles:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, _, _, k, _ in scn_kr:      # 시나리오 개요문·공략문 (3f2)
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, _, k, _ in idx5_extra:     # idx5 잔여 필드 (3f3)
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, _, kn, kd in tokki:
        syl |= {c for c in (kn + kd) if "가" <= c <= "힣"}
    for _, _, k in items:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k in ranks:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k in senpou:
        syl |= {c for c in k if "가" <= c <= "힣"}
    for _, _, k, d, _ in kokugo:
        syl |= {c for c in k if "가" <= c <= "힣"}
        # ★설명문 음절도 반드시 등록해야 한다 — 안 하면 운반체 한자가 그대로
        #   비쳐 나온다([[feedback_kr_patch_verification]] "텍스트 경로 ≠ 글리프 경로").
        if d:
            syl |= {c for c in d if "가" <= c <= "힣"}
    syl = sorted(syl)
    # ★★한글 완성형 2,350자 «전부» 그린다(2026-11-21 하스피 — 이름 입력 등 아무 음절이나 나올 수 있는 곳 대비).
    #   운반체 배정은 Codec 에서 고정(음절 i ↔ i번째 한자 코드)이라 그리기만 하면 된다. 칸·크기·형식 불변.
    #   (옛: 번역에 쓰인 음절만 — 안 쓴 음절은 운반체 한자가 비쳐 나왔다)
    n_used = len(syl)
    syl = sorted(set(syl) | set(codec.syllables))
    print("글리프 대상: 번역에 쓰인 %d자 + 나머지 → 완성형 %d자 전부" % (n_used, len(syl)))
    syl += list(codec.jamo)          # 이름 입력 조합용 자모 40개(운반체 2350~2389, docs/17)

    # ---- 1. 글리프 ----
    em, ratio = autofit_size(fontpath, ink_h)
    font = ImageFont.truetype(fontpath, int(round(em * SS)))
    with open(iso_path, "r+b") as w:
        for ch in syl:
            slot = codec.slot_of[codec.code_for(ch)]
            if slot >= 3773:
                raise SystemExit("가이지 슬롯 %d를 운반체로 잡았다: %s" % (slot, ch))
            px = render_fixed(ch, font, YBASE, weight=weight)
            packed = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()
            assert len(packed) == PIX
            w.seek(s11_off + ATLAS_IN_S11 + slot * PER)
            w.write(packed)
    print("글리프 %d자 (%s ink=%.0f w=%.1f)" % (len(syl), os.path.basename(fontpath), ink_h, weight))

    def enc_field(t):
        b = codec.encode(t, halfwidth_space=False) if t else b""
        if len(b) + 1 > FIELD:
            raise SystemExit("필드 초과: %r = %dB" % (t, len(b)))
        return b + b"\x00" * (FIELD - len(b))

    # ---- 2. 로스터 ----
    n_rec = n_yomi = n_zyomi = 0
    with open(iso_path, "r+b") as w:
        for base, stride, sei_off, recs in copies:
            blk = bytearray(s11[base:base + N_REC * stride])
            for n, ks, km, kz in recs:
                if n >= N_REC:            # 범용 무장 칸 — 블록 밖이라 그 15바이트만 따로 쓴다
                    w.seek(s11_off + base + n * stride + sei_off)
                    w.write(enc_field(ks) + enc_field(km) + enc_field(kz))
                    n_rec += 1
                    continue
                r = n * stride + sei_off
                blk[r:r + FIELD] = enc_field(ks)
                blk[r + 5:r + 10] = enc_field(km)
                blk[r + 10:r + 15] = enc_field(kz)
                # 읽기(+0xF, 카타카나·NUL 끝) → 한글 성+이름 (2026-11-21 하스피: 읽기 칸 카타카나 거슬림 + 정렬 가나다순)
                #   한자 1자당 가나 ≥1자(2 B) ≥ 한글 1자(2 B) 라 원래 길이 안 — 넘으면 멈춤. 남는 자리는 0.
                rd = r + 15
                ln = blk.index(0, rd) - rd
                if ln and (ks or km):
                    nb = codec.encode(ks + km, halfwidth_space=False)
                    if len(nb) > ln:
                        raise SystemExit("읽기 칸 넘침: %r %dB > %dB" % (ks + km, len(nb), ln))
                    blk[rd:rd + ln] = nb + bytes(ln - len(nb))
                    n_yomi += 1
                # 자(字) 읽기(+0x28, 카타카나·NUL 끝 — 관우 ウンチョウ) → 한글 자 (2026-11-21 하스피 무장정보 «관우(ウンチョウ)»)
                zd = r + 0x28
                if kz and zd + 2 < len(blk) and blk[zd] == 0x83:
                    ze = zd
                    while ze + 1 < len(blk) and ((blk[ze] == 0x83 and 0x40 <= blk[ze + 1] <= 0x96) or (blk[ze] == 0x81 and blk[ze + 1] == 0x5b)):
                        ze += 2
                    if blk[ze] == 0:
                        zb = codec.encode(kz, halfwidth_space=False)
                        if len(zb) > ze - zd:
                            raise SystemExit("자 읽기 칸 넘침: %r %dB > %dB" % (kz, len(zb), ze - zd))
                        blk[zd:ze] = zb + bytes(ze - zd - len(zb))
                        n_zyomi += 1
                n_rec += 1
            w.seek(s11_off + base)
            w.write(bytes(blk))
    print("로스터 %d레코드 교체 (%d벌) · 읽기 한글 %d · 자 읽기 한글 %d" % (n_rec, len(copies), n_yomi, n_zyomi))

    # ---- 3. 지명 ----
    # 읽기(카타카나) 칸도 한글 이름으로(2026-11-21 하스피 «지명 가타카나도 한글로» — 정렬도 가나다순).
    #   읽기 = 이름 칸 뒤(都市·州·地方 +5 / 港·関 +7), 원본 읽기 바이트가 places_kr 読み 와 같은 자리만. 남는 자리 0.
    yomi = {}
    for line in open(os.path.join(REPO, "work/places_kr.tsv"), encoding="utf-8"):
        q = line.rstrip("\n").split("\t")
        if len(q) >= 5 and not line.startswith("#") and q[3]:
            yomi[int(q[1], 16)] = q[3].encode("cp932") + b"\x00"
    n_py = 0
    with open(iso_path, "r+b") as w:
        for off, jp, kr in places:
            w.seek(s11_off + ENTRY5 + off)
            w.write(codec.encode(kr, halfwidth_space=False) + b"\x00")
            y = yomi.get(off)
            src = s11[ENTRY5 + off:ENTRY5 + off + 40]
            pos = [k for k in (5, 7) if y and src[k:k + len(y)] == y]
            if not pos:
                raise SystemExit("지명 읽기 자리 못 찾음: %s" % jp)
            nb = codec.encode(kr, halfwidth_space=False)
            if len(nb) > len(y) - 1:
                raise SystemExit("지명 읽기 칸 넘침: %s %r" % (jp, kr))
            w.seek(s11_off + ENTRY5 + off + pos[0])
            w.write(nb + bytes(len(y) - len(nb)))
            n_py += 1
    print("지명 %d곳 교체 · 읽기 한글 %d" % (len(places), n_py))

    # ---- 3b. entry5 병장·관직 이름 (지명과 같은 테이블, 1:1 독음이라 바이트동일) ----
    with open(iso_path, "r+b") as w:
        for off, jp, kr, nb in e5names:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) != nb:          # 1:1 독음이라 원문 바이트수와 정확히 같아야 함
                raise SystemExit("entry5 이름 길이 불일치: %r(%dB)->%r(%dB)"
                                 % (jp, nb, kr, len(b)))
            w.seek(s11_off + ENTRY5 + off)
            w.write(b + b"\x00")
    print("entry5 병장·관직 %d개 교체" % len(e5names))

    # ---- 3c. entry5 시설 이름 (모든 복사본, 1:1 바이트동일) ----
    with open(iso_path, "r+b") as w:
        for off, jp, kr, nb in fac_rows:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) != nb:
                raise SystemExit("시설 길이 불일치: %r(%dB)->%r(%dB)" % (jp, nb, kr, len(b)))
            w.seek(s11_off + ENTRY5 + off)
            w.write(b + b"\x00")
    print("entry5 시설 %d위치 교체" % len(fac_rows))

    # ---- 3d. entry5 시설 효과 설명(산문) ----
    with open(iso_path, "r+b") as w:
        for off, jp, b, kr in desc_rows:
            w.seek(s11_off + ENTRY5 + off)
            w.write(b + b"\x00")
    print("entry5 시설 설명 %d위치 교체" % len(desc_rows))

    # ---- 3e. 시나리오 제목 (컨테이너 idx6~19 rel 0x5f) — 산문(0x70) 불변 ----
    with open(iso_path, "r+b") as w:
        for toff, idx, kr in scn_titles:
            b = codec.encode(kr, halfwidth_space=True)   # 반각 공백(1B, 하드웨어 검증)
            if len(b) + 1 > TITLE_FIELD:
                raise SystemExit("시나리오 제목 초과: idx%d %r %dB>16" % (idx, kr, len(b)))
            # 제목+널 + 나머지 널패딩 = 필드(17B) 전체를 깨끗이. 산문(0x70)은 안 건드림.
            w.seek(s11_off + toff)
            w.write(b + b"\x00" * (TITLE_FIELD - len(b)))
    print("시나리오 제목 %d개 교체 (idx6~19)" % len(scn_titles))

    # ---- 3f2. 시나리오 개요문·세력공략문 (컨테이너 idx6~21, docs/14) ----
    # 슬롯 전체를 널로 깨끗이 채우되, 각 절대 예산(282B/311B) 밖은 손대지 않는다
    # (개요문 꼬리 24B, 공략문 마지막 flag 1B — 실측상 항상 0/의미불명 값, 보존).
    if scn_kr:
        with open(iso_path, "r+b") as w:
            for off, idx, section, jp, kr, cap in scn_kr:
                b = codec.encode(kr, halfwidth_space=True)
                if len(b) + 1 > cap:
                    raise SystemExit("시나리오 %s 초과: idx%d %r %dB > %dB(예산 %dB)"
                                     % (section, idx, kr, len(b), cap - 1, cap))
                w.seek(s11_off + off)
                w.write(b + b"\x00" * (cap - len(b)))
        print("시나리오 개요·공략문 %d개 교체 (idx6~21)" % len(scn_kr))

    # ---- 3f3. idx5(entry5) 잔여 필드 — 전장시설·병장·지형·관직81 (docs/15) ----
    # 고정 오프셋 + 텍스트만 널종료로 쓴다(슬롯 전체를 밀지 않음 — budget은 PC KOR diff로
    # 실측한 안전 상한이지 슬롯 크기가 아니다. tokki와 같은 방식: 텍스트+널만 교체).
    if idx5_extra:
        with open(iso_path, "r+b") as w:
            for off, table, jp, kr, budget in idx5_extra:
                b = codec.encode(kr, halfwidth_space=True)
                if len(b) > budget:
                    raise SystemExit("idx5 %s 초과: %r->%r %dB > %dB" % (table, jp, kr, len(b), budget))
                w.seek(s11_off + ENTRY5 + off)
                w.write(b + b"\x00")
        print("idx5 잔여필드 %d개 교체" % len(idx5_extra))

    # ---- 3f. entry5 특기100 · 기교36 · 능력66 (이름 + 설명) ----
    # 이름/설명은 **고정 오프셋**으로 쓴다. 널을 따라 걷지 말 것 — 필드의 남는 꼬리에
    # 옛 레이아웃 찌꺼기가 남아 있어(게임은 \0까지만 읽으니 무해) 널추적은 2바이트
    # 어긋난다. 세션6의 work/tokki_raw.tsv가 통째로 깨졌던 원인이 이것이다.
    n_tok = 0
    with open(iso_path, "r+b") as w:
        for tbl, off, jp, kn, kd in tokki:
            n_off, n_cap, d_off, d_cap = TOKKI_SPEC[tbl]
            # ⚠️빈 값을 쓰면 널만 박혀 원본 이름/설명이 통째로 지워진다. 실제로 기교 36개가
            #   이렇게 날아간 적 있다(이름 사전을 TOKKI로만 찾아서 GIKOU가 전부 ''였다).
            if not kn or not kd:
                raise SystemExit("%s %r: 한글 이름/설명이 비었다 (이름=%r 설명=%r)"
                                 % (tbl, jp, kn, kd))
            nb = codec.encode(kn, halfwidth_space=False)
            if len(nb) > n_cap:
                raise SystemExit("%s 이름 초과: %r->%r %dB > %dB" % (tbl, jp, kn, len(nb), n_cap))
            db = codec.encode(kd)          # 반각 공백·숫자 그대로(원본도 「50％」로 쓴다)
            if len(db) > d_cap:
                raise SystemExit("%s 설명 초과: %r->%r %dB > %dB" % (tbl, jp, kd, len(db), d_cap))
            w.seek(s11_off + ENTRY5 + off + n_off)
            w.write(nb + b"\x00")
            w.seek(s11_off + ENTRY5 + off + d_off)
            w.write(db + b"\x00")
            n_tok += 1
    print("entry5 특기·기교·능력 %d개 교체 (이름+설명)" % n_tok)

    # ---- 3g. 아이템 이름 (시나리오 컨테이너 52벌) + 작위 (entry5) ----
    # 이름칸이 남으면 옛 바이트가 꼬리에 남지만 게임은 \0까지만 읽으니 무해하다.
    n_it = 0
    with open(iso_path, "r+b") as w:
        for off, jp, kr in items:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) > ITEM_NAME_CAP:
                raise SystemExit("아이템 이름 초과: %r->%r %dB > %dB"
                                 % (jp, kr, len(b), ITEM_NAME_CAP))
            w.seek(s11_off + off)
            w.write(b + b"\x00")
            n_it += 1
        for off, jp, kr in ranks:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) > RANK_NAME_CAP:
                raise SystemExit("작위 이름 초과: %r->%r %dB > %dB"
                                 % (jp, kr, len(b), RANK_NAME_CAP))
            w.seek(s11_off + off)
            w.write(b + b"\x00")
        from senpou_names import NAME_CAP as SEN_CAP           # noqa: E402
        for off, jp, kr in senpou:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) > SEN_CAP:
                raise SystemExit("전법 이름 초과: %r->%r %dB > %dB"
                                 % (jp, kr, len(b), SEN_CAP))
            w.seek(s11_off + off)
            w.write(b + b"\x00")
        # 국호 (시나리오 컨테이너 52벌) — 세력 표시명의 원천
        import kokugo_names as _kk                             # noqa: E402
        n_kd = 0
        for off, jp, kr, dkr, old_len in kokugo:
            b = codec.encode(kr, halfwidth_space=False)
            if len(b) > _kk.NAME_CAP:
                raise SystemExit("국호 이름 초과: %r->%r %dB > %dB"
                                 % (jp, kr, len(b), _kk.NAME_CAP))
            w.seek(s11_off + off)
            w.write(b + b"\x00")
            # 설명문(+0x12) — 반각 공백을 살린다(폭이 절반이라 예산·화면 둘 다 이득).
            if dkr:
                db = codec.encode_ui(dkr)
                if len(db) > _kk.DESC_CAP:
                    raise SystemExit("국호 설명 초과: %r %dB > %dB"
                                     % (jp, len(db), _kk.DESC_CAP))
                # 새 문자열이 더 짧으면 **옛 꼬리를 널로 덮는다**
                pad = max(0, old_len - len(db))
                w.seek(s11_off + off + _kk.DESC_OFF)
                w.write(db + b"\x00" * (1 + pad))
                n_kd += 1
    print("아이템 %d칸 · 작위 %d개 교체" % (n_it, len(ranks)))
    print("전법 %d개 교체 (entry5 0x8354)" % len(senpou))
    print("국호 %d칸 교체 (시나리오 컨테이너 52벌) · 설명문 %d칸" % (len(kokugo), n_kd))

    # ---- 3i. 일기토·설전 커맨드 단어 그래픽 (세션22) ----
    # s11pkres 안 **무압축 선형 PSMT8**을 제자리에 다시 써넣는다(크기 불변 = 안전).
    # ★아틀라스(글리프) 경로와 무관하다 — 픽셀을 직접 그려 넣으므로 「쓰이는 음절」
    #   등록이 필요 없다. 대신 팔레트(my files/gfx/팔레트)가 있어야 한다.
    import battle_words as _bwd                                  # noqa: E402
    n_bw = 0
    with open(iso_path, "r+b") as w:
        for _cfg, _words, _tag in ((_bwd.ILGITO, _bwd.ILGITO_WORDS, "일기토"),
                                   (_bwd.SETSU, _bwd.SETSU_WORDS, "설전")):
            _tex, _ = _bwd.build(_cfg, _words)
            assert _tex.shape == (_cfg["h"], _cfg["w"]), _tex.shape
            _write_boxes(w, s11_off + _cfg["off"], _tex, _cfg["w"], _words)
            n_bw += len(_words)
    print("전투 단어 그래픽 %d칸 교체 (일기토 24 + 설전 10)" % n_bw)

    # ---- 3j. 장식체(붓글씨) 글자 (세션22) ----
    # 궁서체 + 스타일 전이. 텍스처마다 자기 팔레트(my files/gfx/팔레트)가 필요하다.
    import ornate_words as _orn                                # noqa: E402
    n_or = 0
    with open(iso_path, "r+b") as w:
        for _job in _orn.JOBS:
            _, _off, _w2, _h2, _, _boxes = _job
            _, _after, _ = _orn.build(_job)
            assert _after.shape == (_h2, _w2), _after.shape
            _write_boxes(w, s11_off + _off, _after, _w2, _boxes)
            n_or += len(_boxes)
    print("장식체 %d자 교체 (선후수·합·확인·교대·무장·대·필살)" % n_or)

    # ---- 3z. 이름 칸 뒤 카타카나 «읽기» → 한글 이름 (2026-11-21 하스피 «지명 가타카나도 한글로» 후속) ----
    #   특기·기교·병장·관직(entry5) · 아이템·작위·전법·국호. 원본 레코드에서 이름 다음 «순수 카타카나+NUL» 덩어리만 읽기로 본다.
    #   능력 표는 이름 바로 뒤가 설명이라 제외. 한글이 원래 읽기보다 길면 그 칸은 건너뜀(보고).
    def _kata_run(buf, i):
        j = i
        while j + 1 < len(buf) and ((buf[j] == 0x83 and 0x40 <= buf[j + 1] <= 0x96) or (buf[j] == 0x81 and buf[j + 1] in (0x5b, 0x45))):
            j += 2
        return j if j - i >= 4 and j < len(buf) and buf[j] == 0 else None

    yomi_jobs = [(ENTRY5 + off, jp, kn) for tbl, off, jp, kn, kd in tokki if tbl in ("특기", "기교")]
    yomi_jobs += [(ENTRY5 + off, jp, kr) for off, jp, kr, nb in e5names]
    yomi_jobs += [(off, jp, kr) for off, jp, kr in items] + [(off, jp, kr) for off, jp, kr in ranks]
    yomi_jobs += [(off, jp, kr) for off, jp, kr in senpou] + [(r[0], r[1], r[2]) for r in kokugo]
    n_y = n_skip = 0
    with open(iso_path, "r+b") as w:
        for noff, jp, kr in yomi_jobs:
            jb = jp.encode("cp932", "replace")
            rec = s11[noff:noff + 0x40]
            st = None
            for i in range(len(jb) + 1, min(len(rec) - 4, len(jb) + 8)):
                e = _kata_run(rec, i)
                if e:
                    st = i
                    break
            if st is None or not kr:
                continue
            ln = e - st
            nb = codec.encode(kr, halfwidth_space=False)
            if len(nb) > ln:
                n_skip += 1
                continue
            w.seek(s11_off + noff + st)
            w.write(nb + bytes(ln - len(nb)))
            n_y += 1
    print("이름 뒤 읽기(카타카나) → 한글 %d칸 (한글이 길어 건너뜀 %d)" % (n_y, n_skip))

    # ---- 4. UI (SLPM_667.01) ----
    # 슬롯 예산 = 원문바이트 + 뒤널. 넘으면 다음 문자열을 밟는다.
    with open(iso_path, "r+b") as w:
        for off, jp, kr, bud in ui:
            # encode_ui = encode + 제어코드 토큰({ESC}=0x1b 색상, {N}=0x0a 줄바꿈).
            # 이 토큰이 든 서식 문자열 12개를 옛 추출기가 통째로 놓쳐서 화면에
            # 「設置：」가 일본어로 남아 있었다(세션5).
            b = codec.encode_ui(kr)       # 반각 공백·ASCII 그대로 (printf 서식 보존)
            if len(b) + 1 > bud:
                raise SystemExit("UI 예산 초과: %r -> %r %dB+1 > %dB" % (jp, kr, len(b), bud))
            w.seek(elf_off + off)
            w.write(b + b"\x00")
    print("UI %d개 교체" % len(ui))

    # ---- 4a. 도시 정보 창 «아이템» 들여쓰기 (UI 쓰기 뒤에 — 같은 칸 남는 자리를 쓴다) ----
    import item_indent                                            # noqa: E402
    with open(iso_path, "r+b") as w:
        item_indent.apply_to_iso(w, elf_off, codec)
    print("아이템 줄 들여쓰기 고침 (SLPM 코드 2줄 + 라벨 «아이템␣␣», 되읽기 통과)")

    # ---- 4a2. 조사 자동선택 훅 (문자열 그리기 입구 0x16c410, 죽은 함수 3곳에 코드·표) ----
    #   tools/josa_hook.py — 「을(를)·이(가)·은(는)·와(과)·(으)로·(이)」를 앞 글자 받침대로. 시험 = python tools/josa_hook.py test
    # ⛔2026-11-21 끔: 넣었던 자리 3곳(0x467220·0x47db20·0x4b04a0)을 OVERLAY2 가 jal 로 부른다(죽은 함수 아님) → 그 화면에서 뻗음.
    #   진짜 빈자리(실행 파일+OVERLAY1/2+RAM 전부 무참조)로 옮기기 전까지 넣지 않는다 — 원본 바이트 그대로.
    if JOSA_HOOK_ON:
        import josa_hook                                              # noqa: E402
        with open(iso_path, "r+b") as w:
            _nm, _na, _ns = josa_hook.apply_to_iso(w, elf_off, codec)
        print("조사 자동선택 훅: 동굴 조각 %d B (%d조각) + 받침 표(음절 %d), 되읽기 통과" % (_nm, _na, _ns))
    else:
        print("⚠️조사 자동선택 훅 꺼짐(자리 재선정 중) — 「을(를)」 등이 그대로 보인다")

    # ---- 4a3. 이름 입력 한글 조합 훅 (OVERLAY1 0x1f55f48 + 판 표: 자모·초성별 완성형, 가타카나·특수한자 빈 판) ----
    #   tools/name_hook.py — 시험 = python tools/name_hook.py test
    if NAME_HOOK_ON:
        import name_hook                                              # noqa: E402
        with open(iso_path, "r+b") as w:
            _nb, _np, _nd = name_hook.apply_to_iso(w, elf_off, codec)
        print("이름 입력 조합 훅: 코드·표 %d B (%d조각), 바뀐 바이트 %d, 되읽기 통과" % (_nb, _np, _nd))

    # ---- 4b. entry4 블록 압축 해제 버퍼 확대 (SLPM 즉시값 2B) ----
    # 한글이 원본 대비 +19.4% 라 blk0/1/26 이 원래 버퍼(0x13000=77,824)를 넘고,
    # 넘긴 오프셋의 메시지를 게임이 못 읽어 **이벤트가 대사 도중 끊긴다**.
    # 근거·실험표는 tools/e4_buffer.py 주석 참조 (2026-07-29 실기 이분 실험 14회).
    import e4_buffer                                              # noqa: E402
    with open(iso_path, "r+b") as w:
        old, new = e4_buffer.apply_to_iso(w, elf_off)
    if new != old:
        e4_buffer.verify_iso(iso_path, elf_off)                   # 독립 되읽기
        print("entry4 해제 버퍼 0x%x(%dB) → 0x%x(%dB) + 힙 용량 0x%x → 0x%x  (되읽기 검증 통과)"
              % (old, old, new, new, e4_buffer.OLD_CAP, e4_buffer.NEW_CAP))
    else:
        print("entry4 해제 버퍼 0x%x(%dB) — 확대 비활성" % (old, old))

    # ---- 5. 하단바 도움말 idx=3 (LINK 테이블 재지정 + 새 위치에 데이터) ----
    if help_plan:
        with open(iso_path, "r+b") as w:
            help_reloc.apply_to_iso(w, s11_off, help_plan)
        with open(iso_path, "rb") as r:      # 되읽기: 테이블·데이터가 실제로 들어갔나
            r.seek(s11_off + help_reloc.HDR + 3 * 8)
            o, b = struct.unpack("<II", r.read(8))
            assert (o, b) == help_plan["patches"][3], "idx3 LINK 엔트리 되읽기 불일치"
            r.seek(s11_off + o * help_plan["sec"])
            assert r.read(b) == help_plan["data"], "idx3 데이터 되읽기 불일치"
        print("도움말 762개 반영 (idx3 → 섹터 %d, 되읽기 검증 통과)" % help_plan["sector"])

    # ---- 6. 커맨드 그래픽 (idx=94) — 구운 스프라이트에 한글을 다시 그린다 ----
    # 일반 폰트가 아니라 별도 스프라이트라 아틀라스 한 번 칠하기로는 안 바뀐다(세션2 실기 확정).
    # 포맷은 메인 폰트와 동일한 4bpp·저니블=왼쪽픽셀(세션5 정정 — 옛 "8bpp" 기록은 틀렸다).
    # ★BOX(=격자 피치 50x28)를 통째로 0으로 밀고 그 안에 글자를 그린다. 잉크 경계만 덮으면
    #   원본 한자의 옅은 AA가 남아 화면에 가로줄 노이즈로 뜬다(실기에서 사용자가 발견).
    from cmd_graphics import PITCH_B, SS as CSS, autofit as c_autofit, \
        make_box, pack_rows, box_xy                                     # noqa: E402
    from cmd_words import words as cmd_words, kr_of as cmd_kr           # noqa: E402
    sec = struct.unpack("<I", s11[8:12])[0]
    e94_off = struct.unpack("<II", s11[0x10 + 94 * 8: 0x10 + 94 * 8 + 8])[0] * sec
    # EM/YBASE = 101음절 전체가 표시창(BOX y 4~23)에 꽉 차게 들어가는 값(cmd_graphics 참조).
    # ⚠️autofit(참조음절 4개로 em 역산)은 여기선 쓰면 안 된다 — 나머지 음절이 창을 넘어 잘렸다.
    from cmd_graphics import EM as C_EM
    c_size = C_EM
    c_font = ImageFont.truetype(fontpath, c_size * CSS)
    n_cmd = 0
    with open(iso_path, "r+b") as w:
        for c, r, jp in cmd_words():
            kr, src = cmd_kr(jp, to_hangul)
            if len(kr) != 2:
                print("   ⚠️ 커맨드 1:1 아님 스킵:", jp, kr); continue
            bx, by, bw, bh = box_xy(r, c)
            rows_b = pack_rows(make_box(kr, c_font, r, c, weight=0.5))
            for k in range(bh):
                w.seek(s11_off + e94_off + (by + k) * PITCH_B + bx // 2)
                w.write(rows_b[k].tobytes())
            n_cmd += 1
    # ※ 커맨드는 스프라이트에 픽셀을 직접 그리므로 폰트 아틀라스 글리프가 필요없다
    #   (일반 텍스트처럼 SJIS→슬롯을 안 거친다).
    print("커맨드 그래픽 %d단어 다시 그림 (idx=94)" % n_cmd)

    print('\ndone -- pcsx2-qt.exe -fastboot -- "%s"' % iso_path)
    print("(세이브스테이트 로드 금지 - 옛 폰트/데이터가 RAM에 남는다. 새로 부팅.)")


main()
