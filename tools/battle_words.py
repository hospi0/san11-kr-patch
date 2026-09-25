# -*- coding: utf-8 -*-
"""일기토·설전 커맨드 단어 그래픽 한글화 — 단일 진실.

## 대상 (세션22에 GS 덤프로 위치 확정, 전부 s11pkres.bin 안 무압축 선형 PSMT8 8bpp)
  일기토 단어  0x04b36990  512x256  (idx=92 rel 0x20990)  단어 12개 x 2색
  설전   단어  0x04ab3d10  256x256  (idx=91 rel 0x10510)  단어 10개 + 숫자
  ※ISO 오프셋 = s11pkres 오프셋 + s11_off(런타임 계산)

## ★★핵심 제약 — 인덱스를 지어내면 안 된다
8bpp 팔레트 텍스처라 인덱스는 **CLUT을 통해서만** 색이 된다. 임의 값을 쓰면 색이 깨진다.
게다가 **단어마다 색이 다르다**(설전: 道理 청록·故事 분홍·時節 하늘·大喝 노랑·再考 보라…
일기토: 흰색 벌 / 금색 벌). 공통 템플릿으로 찍으면 전부 틀린다.
→ **각 스프라이트가 자기 자신이 쓰던 인덱스만 재사용**한다(스타일 전이 방식).

## 방식 (style transfer)
원본 스프라이트에서 두 개의 램프를 뽑는다:
  ramp_out[d]  : 본체에서 거리 d 인 픽셀들이 쓰던 대표 인덱스 (= 외곽선 그라데이션)
  ramp_in[t]   : 본체 안쪽에서 세로 상대위치 t 인 픽셀들의 대표 인덱스 (= 본체 세로 그라데이션)
그 다음 한글 글리프 마스크를 만들고, 거리변환으로 같은 램프를 입힌다.
→ 색·외곽선 두께·그라데이션이 자동으로 보존된다.

## 사용
  python tools/battle_words.py --preview        # 미리보기 PNG만 (ISO 안 건드림)
  python tools/battle_words.py <iso>            # 실제 패치
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
S11_SRC = r'C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan)/s11pkres.bin'
PAL_DIR = os.path.join(REPO, 'my files/gfx/팔레트')
# ★★폰트는 **본편과 같은 바탕체**를 쓴다 — 게임 안 모든 한글이 바탕체라 여기만 다른
#   폰트를 쓰면 튄다(세션22에 맑은 고딕 Bold로 갔다가 사용자 지적으로 되돌림).
#   바탕체가 원본보다 가는 문제는 `font_build.render_fixed`와 **같은 방식**으로 푼다:
#   `stroke_width`로 합성 굵기 보정(윈도우엔 한글 볼드 명조가 없다).
FONT = 'C:/Windows/Fonts/batang.ttc'
# .ttc 안 폰트 선택: 0=Batang(본문) / 2=Gungsuh(궁서체, 장식체용).
# ornate_words.py 가 이 값을 바꿔 쓴다.
FONT_INDEX = 0
WEIGHT = 1.0            # 합성 굵기. 후보 비교(0/0.8/1.4/2.4) 후 사용자가 1.0으로 확정.
# 박스 대비 글자가 차지하는 비율. ★실기에서 "글자가 크다 / 잘리는 경우도 있다"는
#   지적을 받아 0.86 -> 0.74로 낮췄다. 원본 한자도 박스에 꽉 차 있지 않다.
MARGIN = 0.74           # 글자 '높이' 기준 여백
# 폭 제한은 따로 둔다. 스프라이트 박스는 **후광까지 포함한** 크기라 폭에 같은 여백을
# 주면 2글자 단어(공격·투지·방어·일발)만 폭에 걸려 작아진다(실제로 그렇게 됐다).
MARGIN_W = 0.94
# ★선명도/채도 — 램프가 전부 '평균'이라 경계가 뭉개지고 색이 죽는다.
#   EDGE = 층 전환 폭(작을수록 또렷) / SAT = 채도 배수 / CON = 명암 대비 배수
EDGE = 0.70
SAT = 1.35
SAT_MAX = 3.0          # 채도 배수 상한(장식체에서 더 올릴 때 override)
CON = 1.15
# 채움(획 안쪽)만 밝힌다. ★외곽선까지 같이 밝히면 대비가 죽어 다시 흐려진다.
BRIGHT = 1.60
# 색조 그라데이션(선택). dict(color=(R,G,B), lo=위쪽강도, hi=아래쪽강도).
# ★'획을 특정 색으로 물들이고 싶을 때' 쓴다 — 채도만 올리면 원래 색이 진해질 뿐
#   원하는 색조는 안 나온다(세션22, 선수후수의 청록이 그랬다).
TINT = None
# 박스 바깥을 원본으로 되돌리는 반경(px). 글자가 **밑그림 위에 얹힌** 경우
# 박스를 통째로 칠하면 **사각 후광 테두리**가 생긴다(무장이 그랬다).
# 이 값을 주면 글자에서 그만큼 떨어진 곳은 원본 픽셀을 유지한다.
FEATHER = None
ERASE_OLD = True       # FEATHER 사용 시 옛 글자를 밑그림 색으로 지울지
# 지우기 대상을 **박스 테두리에 안 닿는 덩어리**로 한정(= 배너 붓획 보호). interior_only 참조.
ERASE_INTERIOR_ONLY = False
# 세로 그라데이션 표본의 밝기 하한(중앙값 대비). 이보다 어두운 표본은 오염으로 보고
# 이웃에서 보간한다. build_ramp 의 '표본 정화' 주석 참조.
GRAD_FLOOR = 0.72
# 형태 검출 기준 — 'alpha'(기본) / 'bright'(불투명 밑그림 위 글자). shape_mask 참조.
MASK_MODE = 'alpha'
# ★★밑그림 보존 합성 — **먹 배너·붓획 위에 얹힌 글자**는 이걸 쓴다.
#   FEATHER는 "박스 안을 새로 칠하고 가장자리만 원본으로 되돌리는" 방식이라,
#   박스를 가로지르는 붓획이 통째로 지워져 **획이 끊긴다**(2026-07-20 실기에서
#   무장·확인·대·필살 전부 이 증상). COMPOSITE는 반대로 **원본을 바탕에 두고
#   새 글자만 자기 알파로 얹으므로** 박스 안이든 밖이든 밑그림이 살아남는다.
COMPOSITE = False

# ── 텍스처 ────────────────────────────────────────────────────────────
ILGITO = dict(off=0x04b36990, w=512, h=256,
              pal=os.path.join(PAL_DIR, '일기토_단어_CLUT_unswizzled_RGBA256.bin'))
SETSU = dict(off=0x04ab3d10, w=256, h=256,
             pal=os.path.join(PAL_DIR, '설전_단어_CLUT_unswizzled_RGBA256.bin'))

# ── 일기토 단어 24칸 (x, y, w, h, 한글) ───────────────────────────────
# 위 6 = 흰색(평상시) / 아래 6 = 금색(선택됨). 같은 단어가 2벌이므로 양쪽 다 고친다.
ILGITO_WORDS = [
    # 1행 흰색
    (3, 0, 78, 41, '무쌍'), (88, 1, 75, 40, '급소'), (175, 2, 72, 38, '암기'),
    (260, 0, 72, 40, '견수'), (341, 0, 76, 40, '기합'), (424, 0, 76, 40, '퇴각'),
    # 2행 금색
    (2, 43, 79, 41, '무쌍'), (87, 43, 76, 41, '급소'), (174, 43, 74, 41, '암기'),
    (259, 43, 74, 41, '견수'), (340, 43, 77, 41, '기합'), (423, 43, 78, 41, '퇴각'),
    # 3행 흰색
    (1, 85, 108, 39, '필살기'), (114, 85, 109, 39, '위퇴각'), (225, 87, 69, 37, '공격'),
    (300, 88, 63, 36, '투지'), (372, 88, 64, 37, '방어'), (443, 89, 66, 35, '일발'),
    # 4행 금색
    (0, 126, 110, 41, '필살기'), (114, 126, 110, 42, '위퇴각'), (224, 130, 71, 39, '공격'),
    (299, 131, 65, 38, '투지'), (371, 131, 66, 39, '방어'), (442, 132, 68, 37, '일발'),
]

# ── 설전 작은 단어 (32x32 격자, 2칸=1단어) ────────────────────────────
# y0  道理 故事 時節 大喝 / y32 詭弁 無視 鎮静 逆上 / y64 再考 / y128 話術
SETSU_WORDS = [
    (0, 0, 64, 32, '도리'), (64, 0, 64, 32, '고사'),
    (128, 0, 64, 32, '시절'), (192, 0, 64, 32, '호통'),
    (0, 32, 64, 32, '궤변'), (64, 32, 64, 32, '무시'),
    (128, 32, 64, 32, '진정'), (192, 32, 64, 32, '격앙'),
    (0, 64, 64, 32, '재고'),
    (32, 128, 64, 32, '화술'),
]


# ── 팔레트/거리변환 유틸 ──────────────────────────────────────────────
def load_pal(path):
    return np.frombuffer(open(path, 'rb').read(), dtype=np.uint8).reshape(256, 4)


def _edt1d(f):
    """1차원 제곱거리 변환 (Felzenszwalb). f = 시드값 배열."""
    n = len(f)
    d = np.empty(n)
    v = np.zeros(n, dtype=np.int64)
    z = np.empty(n + 1)
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf
    for q in range(1, n):
        while True:
            s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2.0 * q - 2.0 * v[k])
            if s <= z[k]:
                k -= 1
                if k < 0:
                    k = 0
                    break
            else:
                break
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        dx = q - v[k]
        d[q] = dx * dx + f[v[k]]
    return d


def edt(mask):
    """mask=True 까지의 **유클리드 거리**(float). 진짜 거리라야 글로우가 매끄럽다."""
    INF = 1e12
    f = np.where(mask, 0.0, INF)
    tmp = np.empty_like(f)
    for x in range(f.shape[1]):
        tmp[:, x] = _edt1d(f[:, x])
    out = np.empty_like(f)
    for y in range(f.shape[0]):
        out[y, :] = _edt1d(tmp[y, :])
    return np.sqrt(out)


def signed_dist(core, coverage=None):
    """음수=안쪽 / 양수=바깥쪽. coverage(0..1)가 있으면 경계에서 서브픽셀 보정."""
    sd = np.where(core, -edt(~core), edt(core))
    if coverage is not None:
        edge = (coverage > 0.02) & (coverage < 0.98)
        sd = np.where(edge, 0.5 - coverage, sd)
    return sd


def _otsu(vals):
    """이봉 분포의 골짜기를 찾는다(Otsu). ★(min+max)/2 같은 임의 상수 금지 —
    금색 스프라이트에서 그 방식이 임계 158을 내는 바람에 **연어살빛 채움 294px이
    외곽선으로 오분류**돼 그라데이션이 크림색만 남았다(세션22의 실제 버그)."""
    hist, edges = np.histogram(vals, bins=64, range=(0, 255))
    tot = hist.sum()
    if tot == 0:
        return 128.0
    p = hist.astype(np.float64) / tot
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * centers)
    mT = m0[-1]
    with np.errstate(invalid='ignore', divide='ignore'):
        var = (mT * w0 - m0) ** 2 / (w0 * (1 - w0))
    var = np.nan_to_num(var)
    return float(centers[int(np.argmax(var))])


def bright_mask(patch, pal):
    """밝기로 잡은 '글자 획' 마스크 — 밑그림(먹 배너) 위 글자를 지울 때 쓴다.

    body_mask는 알파로 잡아서 배너까지 글자로 본다. 배너 위 글자를 지우려면
    **밝기**로 갈라야 한다(배너=어둡다 / 글자=밝다).
    """
    rgba = pal[patch]
    lum = rgba[:, :, :3].astype(np.float32).mean(axis=2)
    fg = rgba[:, :, 3] > 8
    if not fg.any():
        return np.zeros(patch.shape, bool)
    return fg & (lum >= _otsu(lum[fg]))


def interior_only(mask):
    """박스 **가장자리에 닿는 덩어리를 뺀** 마스크.

    ★★옛 글자만 지우고 **배너 붓획은 살리는** 열쇠. 두 가지는 밝기로는 못 가르지만
      (붓획도 밝다 — 2026-07-20 실측: 무장 박스 마스크의 30%가 사실 붓획이었다)
      **기하로는 갈린다**: 붓획은 박스를 가로질러 지나가므로 반드시 테두리에 닿고,
      옛 글자는 박스 한가운데 홀로 있다.
    """
    h, w = mask.shape
    reach = np.zeros_like(mask)
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if mask[y, x] and not reach[y, x]:
                reach[y, x] = True
                stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if mask[y, x] and not reach[y, x]:
                reach[y, x] = True
                stack.append((y, x))
    while stack:
        y, x = stack.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not reach[ny, nx]:
                reach[ny, nx] = True
                stack.append((ny, nx))
    return mask & ~reach


def inpaint(rgba, mask, iters=24):
    """mask 픽셀을 주변 비-mask 픽셀 색으로 메운다(반복 팽창 평균).

    ★옛 글자를 지울 때 **박스 전체의 중앙값 한 색**으로 칠하면 밑그림(붓획)의
      농담이 뭉개져 네모난 얼룩이 남는다(2026-07-20 실기: 배너에 흰 구멍).
      국소 평균으로 메우면 획의 농담을 따라간다.
    """
    out = rgba.astype(np.float32).copy()
    todo = mask.copy()
    for _ in range(iters):
        if not todo.any():
            break
        known = ~todo
        acc = np.zeros_like(out)
        cnt = np.zeros(todo.shape, np.float32)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)):
            sh = np.roll(np.roll(out, dy, axis=0), dx, axis=1)
            sk = np.roll(np.roll(known, dy, axis=0), dx, axis=1)
            acc += sh * sk[:, :, None]
            cnt += sk
        fill = todo & (cnt > 0)
        if not fill.any():
            break
        out[fill] = (acc[fill] / cnt[fill][:, None])
        todo &= ~fill
    return out


def shape_mask(patch, pal, mode=None):
    """형태 검출 — MASK_MODE(또는 mode 인자)에 따라 알파/밝기 중 하나.

    ★★**배경이 투명한 스프라이트**(대부분)는 알파가 정답이다(body_mask 참조).
      그런데 **먹 배너처럼 불투명한 밑그림 위에 얹힌 글자**는 알파로 잡으면
      배너까지 '글자 덩어리'로 들어와, 그 **어두운 색이 램프 평균에 섞여
      새 글자가 회색으로 탁해진다**(2026-07-20 실기: 무장이 확인보다 칙칙했다).
      이 경우엔 밝기로 갈라야 한다(배너=어둡다 / 글자=밝다).
    """
    mode = MASK_MODE if mode is None else mode
    return bright_mask(patch, pal) if mode == 'bright' else body_mask(patch, pal)


def body_mask(patch, pal):
    """글자 덩어리(외곽선+채움) 마스크 — **알파**로 잡는다.

    ★★밝기로 채움/외곽선을 가르려던 시도는 전부 실패했다(세션22, 5회 반복):
      금색 벌의 연어살빛(밝기 153)과 갈색 외곽선이 밝기로 안 갈라져서, 임계값을
      어떻게 잡아도(고정 158·Otsu 158) **연어살빛이 외곽선으로 오분류**되고
      그라데이션 표본에서 빠져 금색이 창백한 베이지가 됐다.
    → 알파는 깨끗한 이봉이다(0~8 투명 / 121~128 불투명, 사이는 글로우).
      알파로 '글자 덩어리'를 잡고, 외곽선/채움 구분은 **부호거리 램프에 맡긴다**
      (바깥 링 = 외곽선, 깊은 안쪽 = 채움). 분류 문제를 아예 없앤 셈.
    """
    a = pal[patch][:, :, 3].astype(np.float32)
    if a.max() <= 0:
        return np.zeros(patch.shape, bool)
    return a >= a.max() * 0.75


# 램프 해상도: 부호거리를 이 간격으로 잘라 RGBA 평균을 낸다.
SD_MIN, SD_MAX, SD_STEP = -6.0, 14.0, 0.5      # 바깥 14px = 은은한 글로우까지 포함
TGRID = 64                                      # 세로 그라데이션 표본 수(연속 보간용)


def run_pos(mask):
    """각 픽셀이 **자기 세로 획 안에서** 위→아래 어디쯤인지(0..1). 밖은 -1.

    ★원본의 음영은 글자 전체의 세로 그라데이션이 아니라 **획마다 위=밝게 아래=어둡게**
      들어가는 입체(베벨) 음영이다. 글자 전체 y로 평균 내면 크림과 연어살빛이 섞여
      탁해진다(세션22에서 실기 확인 후 판명된 오모델링).
    """
    H, W = mask.shape
    out = np.full((H, W), -1.0, np.float32)
    for x in range(W):
        col = mask[:, x]
        y = 0
        while y < H:
            if not col[y]:
                y += 1
                continue
            s0 = y
            while y < H and col[y]:
                y += 1
            n = y - s0
            if n == 1:
                out[s0, x] = 0.5
            else:
                out[s0:y, x] = np.linspace(0.0, 1.0, n)
    return out


def build_ramp(patch, pal, mode=None):
    """원본 스프라이트 → (부호거리 → RGBA) 램프 + 본체 세로 그라데이션.

    ★거리마다 '최빈 인덱스 하나'를 고르면 계단이 생긴다(1차 시도의 실패 원인).
      **RGBA로 풀어서 평균**을 내야 글로우가 은은하게 재현된다.
    """
    rgba = pal[patch].astype(np.float32)
    core = shape_mask(patch, pal, mode)
    if not core.any():
        return None
    sd = signed_dist(core)
    nb = int(round((SD_MAX - SD_MIN) / SD_STEP)) + 1
    ramp = np.zeros((nb, 4), np.float32)
    cnt = np.zeros(nb, np.int64)
    b = np.clip(((sd - SD_MIN) / SD_STEP).round().astype(int), 0, nb - 1)
    for i in range(nb):
        sel = b == i
        if sel.any():
            ramp[i] = rgba[sel].mean(axis=0)
            cnt[i] = sel.sum()
    # 빈 구간은 양옆에서 보간
    idx = np.where(cnt > 0)[0]
    if len(idx) == 0:
        return None
    for c in range(4):
        ramp[:, c] = np.interp(np.arange(nb), idx, ramp[idx, c])

    # ── 세로 그라데이션 (글자 전체 기준) ──────────────────────────
    # ★획 단위 베벨(run_pos)로 모델링해봤으나 **가로획에서 세로 런이 2~3px뿐**이라
    #   그 안에서 색이 급변해 줄무늬가 생겼다(세션22, 흰색 벌이 아예 깨졌다).
    #   원본의 입체감을 완벽히 재현하진 못하지만, 글자 전체 세로 그라데이션이
    #   아티팩트 없이 가장 안정적이다.
    ys = np.where(core.any(axis=1))[0]
    y0, y1 = ys.min(), ys.max()
    inside = core & (sd <= -1.5)
    if inside.sum() < 20:
        inside = core
    ts, cs = [], []
    for y in range(y0, y1 + 1):
        sel = inside[y]
        if sel.any():
            ts.append((y - y0) / max(1, (y1 - y0)))
            cs.append(rgba[y][sel].mean(axis=0))
    if not ts:
        return ramp, None, 2.0, ramp[0]
    grad = np.stack([np.interp(np.linspace(0, 1, TGRID), np.asarray(ts),
                               np.asarray(cs)[:, c]) for c in range(4)], axis=1)
    k = 5
    padg = np.pad(grad, ((k // 2, k // 2), (0, 0)), mode='edge')
    grad = np.stack([np.convolve(padg[:, c], np.ones(k) / k, 'valid')
                     for c in range(4)], axis=1)

    # ★★그라데이션 표본 정화 — 박스 안에 **글자가 아닌 불투명 덩어리**(검은 판·
    #   아이콘)가 섞이면 그 높이대 표본이 통째로 어두워지고, 새 글자의 그 부분이
    #   **먹빛으로 잘린 것처럼** 보인다. 2026-07-20 실기: 큰 '살'의 ㅏ 세로획 윗부분
    #   (실측 t=0.00 밝기 **3** vs 나머지 128~187 — 박스 우상단 검은 판이 원인).
    #   ⚠️알파로 글자를 잡는 한 이 오염은 계속 생긴다 → 표본 단계에서 걸러낸다.
    #   ★기준값 0.45로는 부족했다 — 오염이 한 표본에 그치지 않고 **위쪽 10%대에
    #     걸쳐 번져** 있어서, 문턱을 넘긴 어중간한 표본(밝기 83 vs 본체 190~228)이
    #     남아 여전히 어두웠다. 실측으로 0.72까지 올려야 사라진다.
    glum = grad[:, :3].mean(axis=1)
    gmed = float(np.median(glum))
    bad = glum < gmed * GRAD_FLOOR
    if bad.any() and not bad.all():
        ok = np.where(~bad)[0]
        for c in range(4):
            grad[:, c] = np.interp(np.arange(TGRID), ok, grad[ok, c])

    # ★외곽선 두께 실측 — 원본 '덩어리'는 글자획+외곽선이라 획보다 두껍다.
    #   한글도 같은 관계를 만들려면 획을 이만큼 부풀려야 한다(안 하면 얇은 한글 획이
    #   통째로 외곽선 색에 잠겨 채움이 안 보인다).
    lo_i = int(round((-4.0 - SD_MIN) / SD_STEP))
    hi_i = int(round((-0.5 - SD_MIN) / SD_STEP))
    seg = ramp[lo_i:hi_i + 1, :3].mean(axis=1)
    dilate = abs(-4.0 + SD_STEP * int(np.argmin(seg))) if len(seg) else 2.0
    # ★외곽선 색은 밴드 '평균'이면 채움·글로우가 섞여 흐려진다(실기에서 테두리가
    #   거의 안 보였던 원인). 실제 어두운 픽셀들만 골라 평균낸다.
    band = core & (sd > -4.0) & (sd <= -0.5)
    if band.sum() >= 5:
        bl = rgba[band][:, :3].mean(axis=1)
        cut = np.percentile(bl, 25)
        dark = rgba[band][bl <= cut].mean(axis=0)
    else:
        dark = ramp[int(np.argmin(ramp[:, :3].mean(axis=1)))]
    return ramp, grad, float(np.clip(dilate, 0.0, 4.0)), dark


def quantize(rgba_img, pal, allowed):
    """RGBA → 이 스프라이트가 원래 쓰던 인덱스 중 가장 가까운 것.

    ★색을 지어내지 않는다 — allowed(원본이 쓰던 인덱스 집합) 안에서만 고른다.
    """
    cand = pal[allowed].astype(np.float32)
    flat = rgba_img.reshape(-1, 4)
    # 알파 가중을 높게: 투명/불투명을 틀리면 눈에 확 띈다
    wt = np.array([1.0, 1.0, 1.0, 2.2], np.float32)
    d = ((flat[:, None, :] - cand[None, :, :]) * wt) ** 2
    return allowed[d.sum(axis=2).argmin(axis=1)].reshape(rgba_img.shape[:2])


def render_coverage(text, w, h, fontpath=FONT, margin=None, weight=None,
                    target_h=None, offset=(0, 0)):
    """박스 안에 한글 렌더 → **안티에일리어스 커버리지**(0..1 float).

    ★이진 마스크를 쓰면 가장자리가 계단이 된다 — 원본은 전부 AA다.
    margin = 박스 대비 글자가 차지할 비율(원본도 여백이 있다).
    weight = 합성 굵기(stroke_width). font_build.render_fixed와 같은 방식.
    """
    SS = 4
    if weight is None:
        weight = WEIGHT
    if margin is None:
        margin = MARGIN
    sw = int(round(weight * SS / 2))
    tw_lim, th_lim = w * MARGIN_W, h * margin
    sw_fit = max(1, int(round(weight / 2)))
    best = None
    if target_h is not None:
        # ★모든 단어를 **같은 글자 크기**로 찍는다 — 박스마다 따로 맞추면 폭이 좁은
        #   2글자 단어(공격·투지·방어·일발)만 작아진다(실기·미리보기에서 지적됨).
        #   원본도 한 가지 크기로 찍고 박스 폭만 다르다.
        for size in range(6, 300):
            f = ImageFont.truetype(fontpath, size, index=FONT_INDEX)
            bb = f.getbbox(text, stroke_width=sw_fit)
            if (bb[3] - bb[1]) > target_h:
                break
            best = size
        # 그 크기로 폭이 넘치면 그 단어만 줄인다(잘리는 것보다 낫다)
        while best and best > 6:
            f = ImageFont.truetype(fontpath, best, index=FONT_INDEX)
            bb = f.getbbox(text, stroke_width=sw_fit)
            if (bb[2] - bb[0]) <= tw_lim:
                break
            best -= 1
    else:
        for size in range(6, 300):
            f = ImageFont.truetype(fontpath, size, index=FONT_INDEX)
            bb = f.getbbox(text, stroke_width=sw_fit)
            if (bb[2] - bb[0]) > tw_lim or (bb[3] - bb[1]) > th_lim:
                break
            best = size
    if best is None:
        return np.zeros((h, w), np.float32)
    f = ImageFont.truetype(fontpath, best * SS, index=FONT_INDEX)
    img = Image.new('L', (w * SS, h * SS), 0)
    dr = ImageDraw.Draw(img)
    l, t, r, b = dr.textbbox((0, 0), text, font=f, stroke_width=sw)
    dr.text(((w * SS - (r - l)) / 2 - l + offset[0] * SS,
             (h * SS - (b - t)) / 2 - t + offset[1] * SS),
            text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    small = img.resize((w, h), Image.LANCZOS)
    return np.clip(np.asarray(small).astype(np.float32) / 255.0, 0, 1)


def restyle(patch, pal, text, fontpath=FONT, target_h=None, offset=(0, 0),
            style=None):
    """원본 스프라이트의 스타일(색·외곽선·글로우·그라데이션)을 유지한 채 한글로 교체.

    style = (patch_src, pal_src) — 스타일을 **다른 스프라이트에서 빌려온다**.
      ★화면에 나란히 뜨는 글자인데 원본끼리 결이 다를 때 쓴다(2026-07-20: 武将은
        외곽선 없는 흰 글로우, 確認은 회색 외곽선 → 사용자가 "무장을 확인과 똑같이"
        요청). 램프·채도·대비 기준만 빌리고, **실제 색은 대상 스프라이트가 원래
        쓰던 인덱스 안에서만** 고른다(quantize의 allowed는 그대로 대상 기준) —
        팔레트가 서로 다르므로 이 제약을 깨면 색이 깨진다.
      ⚠️박스 크기가 서로 달라도 된다(램프는 부호거리 기준이라 크기 무관).
    """
    h, w = patch.shape
    # ⚠️스타일 원본은 **자기 텍스처의 검출 방식**으로 읽어야 한다. 대상(무장)이
    #   'bright'라고 원본(확인)까지 bright로 읽으면 원본 형태를 오검출한다.
    s_patch, s_pal, s_mode = (patch, pal, None) if style is None else (
        style[0], style[1], style[2] if len(style) > 2 else 'alpha')
    built = build_ramp(s_patch, s_pal, s_mode)
    if built is None:
        return patch.copy()
    ramp, grad, dilate, dark = built
    cov = render_coverage(text, w, h, fontpath, target_h=target_h, offset=offset)
    if cov.max() < 0.2:
        return patch.copy()
    core = cov >= 0.5
    if not core.any():
        return patch.copy()
    sd = signed_dist(core, cov)

    # ── 3층 조립: 채움 / 외곽선 / 후광 ────────────────────────────
    # ★램프를 부호거리로 그냥 조회하면, 원본의 '덩어리'(획+외곽선)와 한글 획의
    #   두께 관계가 달라 얇은 획이 외곽선 색에 잠긴다. 획을 부풀려 보정하려 했더니
    #   이번엔 한글 속공간이 메워져 덩어리가 됐다(세션22, 두 방식 다 실패).
    #   → 세 층을 **명시적으로 조립**한다. 두께와 무관하게 구조가 보장된다.
    nb = ramp.shape[0]

    def ramp_at(v):
        pos = np.clip((v - SD_MIN) / SD_STEP, 0, nb - 1)
        lo = np.floor(pos).astype(int)
        hi = np.clip(lo + 1, 0, nb - 1)
        fr = (pos - lo)[..., None]
        return ramp[lo] * (1 - fr) + ramp[hi] * fr

    # 채움색 — 글자 전체 세로 그라데이션
    ys = np.where(core.any(axis=1))[0]
    y0, y1 = ys.min(), ys.max()
    yy = np.indices((h, w))[0]
    t = np.clip((yy - y0) / max(1, (y1 - y0)), 0, 1)
    gi = t * (TGRID - 1)
    g0 = np.floor(gi).astype(int)
    g1 = np.clip(g0 + 1, 0, TGRID - 1)
    gf = (gi - g0)[:, :, None]
    fill = grad[g0] * (1 - gf) + grad[g1] * gf if grad is not None else ramp_at(-3.0)

    D = max(dilate, 1.0)                      # 외곽선 두께(실측)
    out_rgba = fill.copy()
    a1 = np.clip(sd / EDGE, 0, 1)[:, :, None]           # 획 -> 외곽선
    out_rgba = out_rgba * (1 - a1) + dark[None, None, :] * a1
    glow = ramp_at(np.maximum(sd - D, 0.0))
    a2 = np.clip((sd - D) / EDGE, 0, 1)[:, :, None]     # 외곽선 -> 후광
    out_rgba = out_rgba * (1 - a2) + glow * a2

    # ── 강도 보정 ────────────────────────────────────────────────
    # ★램프가 전부 '평균'이라 채도와 불투명도가 체계적으로 깎인다(평균은 중간으로
    #   수렴한다). 실측: 금색 최대채도 139->101, 흰색 불투명픽셀 1195->819.
    #   → 원본 값을 재서 **거기에 맞춘다**(임의 상수 아님).
    # rgba_o = **스타일 기준**(빌려온 쪽) / rgba_t = 실제로 덮어쓸 대상 박스.
    # 둘을 섞으면 안 된다 — 강도 보정은 스타일 기준, 밑그림 보존은 대상 기준이다.
    rgba_o = s_pal[s_patch].astype(np.float32)
    rgba_t = pal[patch].astype(np.float32)
    amax = float(rgba_t[:, :, 3].max())

    # (1) 글자+외곽선 영역은 원본처럼 불투명하게
    solid = np.clip((D + 0.6 - sd) / 1.2, 0, 1)
    out_rgba[:, :, 3] = np.maximum(out_rgba[:, :, 3], solid * amax)

    # (2) 채도 복원 — 원본의 채도 분포에 맞춘다
    def chroma(a):
        return a[..., :3].max(axis=-1) - a[..., :3].min(axis=-1)

    fg_o = rgba_o[:, :, 3] > 8
    if fg_o.any():
        co = np.percentile(chroma(rgba_o)[fg_o], 95)
        fg_n = out_rgba[:, :, 3] > 8
        if fg_n.any():
            cn = np.percentile(chroma(out_rgba)[fg_n], 95)
            if cn > 1.0 and co > 1.0:
                k = float(np.clip((co / cn) * SAT, 1.0, SAT_MAX))
                g = out_rgba[:, :, :3].mean(axis=2, keepdims=True)
                out_rgba[:, :, :3] = np.clip(g + (out_rgba[:, :, :3] - g) * k, 0, 255)
    # 명암 대비 — 전경 밝기 중앙값을 축으로 벌린다(흰 글자가 회색으로 죽는 걸 막는다)
    fgm = out_rgba[:, :, 3] > 8
    if fgm.any():
        lum = out_rgba[:, :, :3].mean(axis=2)
        piv = float(np.median(lum[fgm]))
        out_rgba[:, :, :3] = np.clip(
            piv + (out_rgba[:, :, :3] - piv) * CON, 0, 255)
    # 밝기 — 획 안쪽일수록 강하게, 외곽선은 그대로
    inner = np.clip((0.5 - sd) / 1.2, 0, 1)[:, :, None]
    out_rgba[:, :, :3] = np.clip(
        out_rgba[:, :, :3] * (1.0 + (BRIGHT - 1.0) * inner), 0, 255)

    # 색조 그라데이션 — 획 안쪽을 지정색으로, 위→아래로 강도를 키운다
    if TINT:
        ys2 = np.where(core.any(axis=1))[0]
        if len(ys2):
            ya, yb = ys2.min(), ys2.max()
            tt = np.clip((np.indices((h, w))[0] - ya) / max(1, (yb - ya)), 0, 1)
            stg = (TINT['lo'] + (TINT['hi'] - TINT['lo']) * tt)[:, :, None]
            col = np.asarray(TINT['color'], np.float32)[None, None, :]
            wgt2 = stg * inner
            out_rgba[:, :, :3] = np.clip(
                out_rgba[:, :, :3] * (1 - wgt2) + col * wgt2, 0, 255)

    # ★밑그림 보존 합성 — 원본을 바탕에 두고 **새 글자만 자기 알파로** 얹는다.
    #   박스를 가로지르는 붓획이 그대로 살아남는다(FEATHER는 이걸 못 한다).
    if COMPOSITE:
        base = rgba_t.astype(np.float32)
        oldm = bright_mask(patch, pal)
        if oldm.any():
            base = inpaint(base, oldm)      # 옛 글자만 국소 평균으로 지운다
        wgt = np.clip(out_rgba[:, :, 3:4] / max(1.0, amax), 0, 1)
        out_rgba = out_rgba * wgt + base * (1 - wgt)

    # 밑그림 보존(구식) — 글자 주변만 새로 그리고 바깥은 원본 유지
    if FEATHER:
        base = rgba_t.copy()
        if ERASE_OLD:
            # ★페더링만 하면 **옛 글자가 그대로 남는다**(새 글자가 더 좁을 때).
            #   옛 획을 주변 밑그림 색으로 먼저 지운 뒤 새 글자를 얹는다.
            # ★★채움색은 배경 중에서도 **어두운 쪽**(밝기 하위 30%)의 평균이다.
            #   그냥 중앙값을 쓰면 **옛 글자의 글로우가 배경에 섞여** 실제 배너보다
            #   밝은 색이 나오고, 그 자리가 **흰 구멍**으로 보인다(2026-07-20 실기).
            #   ⚠️국소 평균(inpaint)도 시도했으나 글로우를 이웃에서 퍼올려 더 나빴다.
            oldm = bright_mask(patch, pal)
            if ERASE_INTERIOR_ONLY:
                oldm = interior_only(oldm)     # 배너 붓획 제외 (interior_only 참조)
            bg_sel = (~oldm) & (rgba_t[:, :, 3] > 8)
            if bg_sel.any() and oldm.any():
                bgp = rgba_t[bg_sel]
                bl = bgp[:, :3].mean(axis=1)
                dark_sel = bl <= np.percentile(bl, 30)
                base[oldm] = bgp[dark_sel].mean(axis=0)
        mk = np.clip((FEATHER - sd) / 2.5, 0, 1)[:, :, None]
        out_rgba = out_rgba * mk + base * (1 - mk)

    allowed = np.unique(patch)
    return quantize(out_rgba, pal, allowed).astype(np.uint8)


# ── 실행 ──────────────────────────────────────────────────────────────
def build(tex_cfg, words, fontpath=FONT):
    s11 = open(S11_SRC, 'rb').read()
    off, w, h = tex_cfg['off'], tex_cfg['w'], tex_cfg['h']
    pal = load_pal(tex_cfg['pal'])
    tex = np.frombuffer(s11[off:off + w * h], dtype=np.uint8).reshape(h, w).copy()
    # 원본 글자(획 덩어리)의 실제 높이 중앙값 = 공통 목표 크기
    hs = []
    for (x, y, bw, bh, kr) in words:
        m = body_mask(tex[y:y + bh, x:x + bw], pal)
        ys = np.where(m.any(axis=1))[0]
        if len(ys):
            hs.append(ys.max() - ys.min() + 1)
    target = float(np.median(hs)) * MARGIN / 0.86 if hs else None
    for (x, y, bw, bh, kr) in words:
        patch = tex[y:y + bh, x:x + bw]
        tex[y:y + bh, x:x + bw] = restyle(patch, pal, kr, fontpath, target_h=target)
    return tex, pal


def preview(tag, tex_cfg, words, fontpath=FONT):
    s11 = open(S11_SRC, 'rb').read()
    off, w, h = tex_cfg['off'], tex_cfg['w'], tex_cfg['h']
    pal = load_pal(tex_cfg['pal'])
    before = np.frombuffer(s11[off:off + w * h], dtype=np.uint8).reshape(h, w)
    after, _ = build(tex_cfg, words, fontpath)

    def comp(idx):
        rgb = pal[idx][:, :, :3].astype(np.float32)
        a = np.clip(pal[idx][:, :, 3].astype(np.float32) / 128.0, 0, 1)[:, :, None]
        yy, xx = np.mgrid[0:h, 0:w]
        chk = np.where(((yy // 8 + xx // 8) % 2) == 0, 55, 85).astype(np.float32)[:, :, None]
        return (rgb * a + chk * (1 - a)).astype(np.uint8)

    sheet = Image.new('RGB', (w * 2, h * 2 * 2 + 12), (16, 16, 22))
    sheet.paste(Image.fromarray(comp(before)).resize((w * 2, h * 2), Image.NEAREST), (0, 0))
    sheet.paste(Image.fromarray(comp(after)).resize((w * 2, h * 2), Image.NEAREST),
                (0, h * 2 + 12))
    outp = os.path.join(REPO, 'preview', 'battle_%s.png' % tag)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    sheet.save(outp)
    print('미리보기 저장: %s  (위=원본 / 아래=한글)' % outp)
    return after


def main():
    font = FONT
    for i, a in enumerate(sys.argv):
        if a == '--font':
            font = sys.argv[i + 1]
    if '--preview' in sys.argv:
        preview('ilgito', ILGITO, ILGITO_WORDS, font)
        preview('setsuden', SETSU, SETSU_WORDS, font)
        return
    raise SystemExit('실제 ISO 패치는 build_kr.py 에서 호출한다. '
                     '단독 실행은 --preview 만 지원.')


if __name__ == '__main__':
    main()
