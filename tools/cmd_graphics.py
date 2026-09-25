# -*- coding: utf-8 -*-
"""커맨드 그래픽(s11pkres idx=94) — 구운 스프라이트 시트에 한글을 다시 그린다.

왼쪽 세로 커맨드 메뉴(都市/軍事/人材…)와 액션 커맨드는 일반 폰트가 아니라 **idx=94에 구운
스프라이트**다(세션2 실기 확정: 일반폰트 都·市 글리프를 도·시로 바꿔도 커맨드는 안 바뀜).

★★세션5 정정 — 옛 기록의 「8bpp 그레이스케일」은 틀렸다.
  **4bpp · 피치 256 B = 512 px · 저니블 = 왼쪽 픽셀** = 메인 폰트 아틀라스와 **완전히 같은 포맷**.
  8bpp로 읽으면 바이트당 픽셀 2개가 1개로 뭉개져 한자가 가로로 눌려 보였다(그래서 "글자폭 ~22px"
  기록과 렌더가 안 맞았다). 인덱스 0=투명, 1~15 AA 램프도 메인 폰트와 같은 관례.

## 격자 (실측 확정)
**지우는 상자(BOX)와 글자를 그리는 자리(GLYPH)를 구분한다.**

    BOX  행 : y = 563 + 28*r,  높이 27    (r = 0..8, 9행)
    BOX  열 : x = 64 + 50*c,   폭  50     (c = 0..8, 9열).  좌측 세로메뉴 열 = x 0, 폭 50
    GLYPH   : BOX 안쪽 (+2, +2) 에 46 x 23  = 23x23 글자 2개

⚠️★**셀 경계는 임계값 없이(>0) 재야 한다.** 처음엔 잉크를 `>128`로 재서 y=565..587 / x=66..111로
  잡았는데, 그 밖에 **옅은 AA 픽셀이 남아 있었다**(행 588에 59px!). 그대로 패치하니 한글 위에
  원본 한자의 획이 가로줄로 떠서 실기 화면에 노이즈로 보였다(사용자 발견).
  진짜 경계 = **완전히 빈 행/열**로 잡는다: 빈 행 590·618·646·674·702·730·758·786 / 빈 열
  113~114·162~164·212~214·262~264·312~314·362~364·412~414·462~464.
  BOX는 그 빈 여백까지 덮고(바이트 정렬도 맞음), 글자는 원래 자리에 그린다.

     행0: 都市 待機 開発 輸送 同盟 新設 追放 鎮静 乱突
     행1: 軍事 攻撃 徴兵 移動 破棄 再編 勢力 伏兵 二段
     행2: 人材 一斉 兵装 呼寄 停戦 解散  --  同討 熊手
     행3: 外交 戦法 巡察 探索 勧告 評定 武将 妖術 横撃
     행4: 計略 一騎 商人 登用 交換 軍師 火計 落雷 旋風
     행5: 軍団 設置 技巧 褒賞 二虎 官職 消火 部隊 火矢
     행6: 君主 補修 訓練 授与 駆虎 結義 偽報  --  貫矢
     행7: 情報 退却 出陣 親善 流言 婚姻 撹乱 突出 乱射
     행8: 育成 合併 研究 能力 適性 待技
     열0: 突撃 突破 突進 破砕 投石 放射 激突

전부 2글자 → 한국어 2음절 1:1이라 **같은 셀 크기에 그대로 들어간다**(도시·군사·인재·외교…).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PITCH_B = 256              # 바이트/행 (= 512 px)
WIDTH = 512
CELL_W, CELL_H = 46, 26    # 글자 2개가 차지하는 넓이
CHAR_W = 23
YBASE = 21                 # 베이스라인. EM/YBASE는 autofit이 아니라 **101음절 전체의 실제
EM = 19                    # 잉크범위**로 잡았다 — autofit은 참조음절 4개만 봐서 나머지가 넘쳤다.
BOX_W, BOX_H = 50, 28      # 지울 상자 = 격자 피치와 동일 → 빈틈없이 타일링된다
                           # (27로 두면 행 사이 여백 줄에 잔챙이 픽셀이 남는다)
GLYPH_DX, GLYPH_DY = 2, 0  # BOX 안에서 글자가 시작하는 위치
# ★★**게임이 화면에 보여주는 창 ≈ BOX의 y 4~23 (20줄)** — 실기 2회로 역산했다:
#     ink19 → 잉크 y 5~24 → "위아래 조금 잘림"(24가 잘림)
#     ink22 → 잉크 y 3~25 → "좀 잘리고 너무 큼"(3과 24~25가 잘림)
#   원본 한자는 y 0~25로 더 넓지만 **양 끝은 획 끝이라 잉크가 희박**해(행별 평균 6.7px/6.8px)
#   잘려도 티가 안 난다. 한글은 획이 굵어 바로 드러난다 → **잉크를 y 4~23에 가둔다**.
#   ⚠️'원본이 0~25를 채우니 나도 그러면 된다'가 함정이었다 — 원본의 0~3·24~25는 안 보이는 부분이다.
Y0, YP = 563, 28           # BOX 원점
X0, XP = 64, 50
COL0_X = 0                 # 좌측 세로메뉴 열의 BOX
SS = 8                     # 슈퍼샘플


def box_xy(row, col):
    """지울 상자의 (픽셀 x, 픽셀 y, 폭, 높이). col=-1이면 좌측 세로메뉴 열."""
    x = COL0_X if col < 0 else X0 + XP * col
    return x, Y0 + YP * row, min(BOX_W, WIDTH - x), BOX_H


def cell_xy(row, col):
    """글자를 그릴 (픽셀 x, 픽셀 y). BOX 안쪽 +2,+2."""
    x, y, _, _ = box_xy(row, col)
    return x + GLYPH_DX, y + GLYPH_DY


def unpack(d):
    """4bpp 바이트열 → (행, 512) 인덱스 배열. 저니블 = 왼쪽 픽셀."""
    a = np.frombuffer(d, dtype=np.uint8)
    px = np.empty(len(a) * 2, np.uint8)
    px[0::2] = a & 0x0F
    px[1::2] = a >> 4
    return px[:len(px) // 512 * 512].reshape(-1, 512)


def render_syllable(ch, font, ybase=YBASE, weight=0.0):
    """한글 1자 → 23x23 인덱스(0~15) 배열. 전 글자 공통 em·공통 베이스라인."""
    pad = CHAR_W * SS
    im = Image.new("L", (CHAR_W * SS + 2 * pad, CELL_H * SS + 2 * pad), 0)
    dr = ImageDraw.Draw(im)
    # 앵커 ms = 가로 중앙 / 베이스라인
    dr.text((pad + CHAR_W * SS // 2, pad + ybase * SS), ch, font=font, fill=255,
            anchor="ms", stroke_width=int(round(weight * SS)), stroke_fill=255)
    im = im.crop((pad, pad, pad + CHAR_W * SS, pad + CELL_H * SS))
    a = np.asarray(im, np.float32).reshape(CELL_H, SS, CHAR_W, SS).mean((1, 3))
    return np.clip(np.rint(a / 255.0 * 15), 0, 15).astype(np.uint8)


def autofit(fontpath, ink_h):
    """참조 음절들의 잉크 높이가 ink_h가 되는 공통 em을 역산(글자마다 맞추면 안 된다)."""
    for size in range(8, 60):
        f = ImageFont.truetype(fontpath, size * SS)
        hs = []
        for ch in "동시군국":
            pad = CHAR_W * SS
            im = Image.new("L", (CHAR_W * SS + 2 * pad, CELL_H * SS + 2 * pad), 0)
            ImageDraw.Draw(im).text((pad, pad + YBASE * SS), ch, font=f, fill=255, anchor="ls")
            bb = im.getbbox()
            if bb:
                hs.append((bb[3] - bb[1]) / SS)
        if hs and sum(hs) / len(hs) >= ink_h:
            return size
    return 24


def make_cell(word, font, weight=0.0):
    """2음절 → 46x23 인덱스 배열."""
    assert len(word) == 2, "커맨드 셀은 2글자다: %r" % word
    return np.hstack([render_syllable(c, font, weight=weight) for c in word])


def pack_rows(cell):
    """인덱스 배열 → 행마다 폭/2 바이트(저니블=왼쪽)."""
    lo, hi = cell[:, 0::2], cell[:, 1::2]
    return (lo | (hi << 4)).astype(np.uint8)


def make_box(word, font, row, col, weight=0.0):
    """단어 → 지울 상자 전체를 채운 인덱스 배열 (여백은 0으로 지우고 글자는 제자리에).

    ★상자 전체를 0으로 밀어야 원본 한자의 옅은 AA 잔재가 안 남는다.
    """
    x, y, bw, bh = box_xy(row, col)
    assert x % 2 == 0 and bw % 2 == 0, "BOX가 바이트 경계에 안 맞는다 (x=%d w=%d)" % (x, bw)
    box = np.zeros((bh, bw), np.uint8)
    g = make_cell(word, font, weight=weight)               # 46 x 23
    box[GLYPH_DY:GLYPH_DY + CELL_H, GLYPH_DX:GLYPH_DX + CELL_W] = g[:, :bw - GLYPH_DX]
    return box
