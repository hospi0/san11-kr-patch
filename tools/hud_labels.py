"""気力·耐久·治安 라벨 — idx=94의 **8bpp / 피치 256B** 구역 (세션8).

⚠️같은 파일 안에서 **구역마다 피치가 다르다**. 여기는 256이고, HUD 뱃지 구역은 512다.
   (인접행 상관 스윕으로 실측: 이 구역 256=0.678 / 뱃지 구역 512=0.752)

레이아웃 — 두 글자가 **지그재그 합성**이라 셀 단위로 못 자른다. 구역을 통째로 지우고 다시 그린다.
  구역   = 행 907..944, x 120..239 (120x38). 정확히 세 라벨만 들어 있다:
           아래 행 945~946이 완전히 비어 있어 디더 스트립(947~)과 갈리고,
           왼쪽 x119는 통 아이콘의 어두운 가장자리(≤0x11)라 라벨 잉크가 아니다.
  위 글자 = x 120 + 40k, 행 907  (26x26)
  아래글자 = x 136 + 40k, 행 919  (26x26)   ← +16x, +12y 어긋남
  스타일  = 배경 0x00 / **어두운 획 0x12 / 흰 후광 0xFF** (뱃지와도 또 다르다)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PITCH = 256
# 원본 잉크는 x120..239에서 끝나지만 x240..249가 완전히 비어 있어(행 907..944 전수 0)
# 마지막 글자 26px가 x241까지 나가도 안전하다. 위 행 900..906의 다른 요소는 행 범위가 달라 무관.
REGION = (907, 945, 120, 246)      # r0, r1, x0, x1
TOP_Y, BOT_Y = 907, 919
TOP_X0, BOT_X0, LABEL_PITCH = 120, 136, 40
EM = 26
BG, STROKE, HALO = 0x00, 0x12, 0xFF

LABELS = [('気力', '기력'), ('耐久', '내구'), ('治安', '치안')]


def read_region(data):
    a = np.frombuffer(data[:len(data) // PITCH * PITCH], np.uint8).reshape(-1, PITCH)
    r0, r1, x0, x1 = REGION
    return a[r0:r1, x0:x1].copy()


def _masks(ch, fontpath, em, weight, halo_px):
    """음절 -> (stroke, halo) alpha 쌍. 오버샘플해서 후광을 팽창시킨 뒤 축소한다."""
    SS = 8
    pad = em * SS
    im = Image.new('L', (pad * 3, pad * 3), 0)
    f = ImageFont.truetype(fontpath, em * SS)
    ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255,
                            stroke_width=int(round(weight * SS)), stroke_fill=255)
    bb = im.getbbox()
    g = im.crop(bb)
    # 비율 보존해 em 상자에 맞춤
    s = min(em / g.width, em / g.height)
    w, h = max(1, round(g.width * s * SS)), max(1, round(g.height * s * SS))
    g = g.resize((w, h), Image.BOX)
    big = Image.new('L', (em * SS, em * SS), 0)
    big.paste(g, ((em * SS - w) // 2, (em * SS - h) // 2))
    r = int(round(halo_px * SS))
    hl = big.filter(ImageFilter.MaxFilter(2 * r + 1)) if r > 0 else big
    to = lambda i: np.asarray(i.resize((em, em), Image.BOX), np.float32) / 255.0
    return to(big), to(hl)


def draw_syllable(canvas, ch, fontpath, x, y, em=EM, weight=0.0, halo_px=2.0):
    """구역 캔버스(정수좌표는 REGION 기준)에 한 음절을 그린다. 뒤에 그린 게 위로 온다."""
    st, hl = _masks(ch, fontpath, em, weight, halo_px)
    inner = HALO * (1 - st) + STROKE * st          # 흰 후광 위에 어두운 획
    val = inner * hl + BG * (1 - hl)               # 그걸 검은 배경에 합성
    reg = canvas[y:y + em, x:x + em].astype(np.float32)
    canvas[y:y + em, x:x + em] = np.rint(np.where(hl > 0.02, val, reg))
    return canvas


def make_region(fontpath, em=EM, weight=0.0, halo_px=2.0, kr=True):
    """세 라벨을 원본과 같은 지그재그로 새로 그린 구역(120x38)을 반환."""
    r0, r1, x0, x1 = REGION
    canvas = np.full((r1 - r0, x1 - x0), BG, np.uint8)
    for k, (jp, ko) in enumerate(LABELS):
        word = ko if kr else jp
        draw_syllable(canvas, word[0], fontpath,
                      TOP_X0 - x0 + LABEL_PITCH * k, TOP_Y - r0, em, weight, halo_px)
        draw_syllable(canvas, word[1], fontpath,
                      BOT_X0 - x0 + LABEL_PITCH * k, BOT_Y - r0, em, weight, halo_px)
    return canvas
