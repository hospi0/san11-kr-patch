"""HUD 뱃지(좌상단 行/技) 렌더·패치 — idx=94의 **8bpp / 피치 512B** 구역.

세션8 발견. 세션5·6이 이 구역을 8bpp W256으로 읽어 "노이즈=없음"으로 접었던 자리다.
커맨드 그리드(4bpp/W512, cmd_graphics.py)와는 **다른 포맷이고 명암도 반대**다:

  셀 = 21x20 둥근 버튼, 셀 피치 26px
    行 = 행 57..76, x 77..97   파일 오프셋 0x724D
    技 = 행 57..76, x 103..123 파일 오프셋 0x7267
  값 = 팔레트 인덱스지만 **인덱스가 곧 밝기**(그레이스케일로 읽힌다) → CLUT을 몰라도
       원본이 쓰는 값만 재사용하면 색이 정확히 맞는다.
    0xF3 = 테두리 링 / 0xEA = 버튼 면 / 0x12 = 글자 잉크(가장 어두움) / 그 사이 = AA

테두리는 行/技 두 셀에서 **바이트까지 동일**해서 빈 버튼을 정확히 복원할 수 있다(BLANK).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PITCH = 512
CW, CH = 21, 20            # 셀 크기
FACE, INK, RING = 0xEA, 0x12, 0x12  # RING은 아래 BLANK가 들고 있음
EDGE = 0xF3

CELLS = {'行': 77, '技': 103}
ROW0 = 57
KR = {'行': '행', '技': '기'}       # 행동력 / 기교P


def blank_button():
    """빈 둥근 버튼 21x20. 원본 두 셀에서 공통인 테두리를 그대로 재현한다."""
    b = np.full((CH, CW), FACE, np.uint8)
    b[0] = [0x37, 0x41] + [EDGE] * 17 + [0x41, 0x34]
    b[19] = [0x34, 0x41] + [EDGE] * 17 + [0x41, 0x34]
    b[1, 0] = b[1, 20] = 0x41
    b[18, 0] = b[18, 20] = 0x41
    b[2:18, 0] = b[2:18, 20] = EDGE
    b[18, 2] = b[18, 18] = 0xEE
    return b


def read_cell(data, x):
    a = np.frombuffer(data[:len(data) // PITCH * PITCH], np.uint8).reshape(-1, PITCH)
    return a[ROW0:ROW0 + CH, x:x + CW].copy()


def render_syllable(ch, fontpath, em, weight=0.0, stretch=False):
    """음절 -> alpha(0..1). 8배 오버샘플 후 BOX 축소.

    stretch=False면 **비율을 보존**해 em 상자 안에 맞춘다(가로가 좁은 '기'가 안 퍼진다).
    stretch=True면 원본 한자처럼 em x em 정사각을 꽉 채운다.
    """
    SS = 8
    pad = em * SS
    im = Image.new('L', (pad * 3, pad * 3), 0)
    f = ImageFont.truetype(fontpath, em * SS)
    ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255,
                            stroke_width=int(round(weight * SS)), stroke_fill=255)
    g = im.crop(im.getbbox())
    if stretch:
        return np.asarray(g.resize((em, em), Image.BOX), np.float32) / 255.0
    s = min(em / g.width, em / g.height)
    w, h = max(1, round(g.width * s)), max(1, round(g.height * s))
    small = np.asarray(g.resize((w, h), Image.BOX), np.float32) / 255.0
    out = np.zeros((em, em), np.float32)
    y, x = (em - h) // 2, (em - w) // 2
    out[y:y + h, x:x + w] = small
    return out


def make_cell(ch, fontpath, em=15, weight=0.0, dx=0, dy=0, stretch=False):
    """빈 버튼 + 한글. 원본 한자의 잉크범위(rows 2..16 x cols 3..18)에 맞춰 중앙 배치."""
    cell = blank_button().astype(np.int16)
    a = render_syllable(ch, fontpath, em, weight, stretch)
    y0 = (CH - em) // 2 + dy
    x0 = (CW - em) // 2 + dx
    reg = cell[y0:y0 + em, x0:x0 + em].astype(np.float32)
    val = FACE + a * (INK - FACE)
    cell[y0:y0 + em, x0:x0 + em] = np.rint(np.minimum(reg, val))
    return cell.astype(np.uint8)


# ── 부대 상태 뱃지 (行/技와 **명암이 반대**: 어두운 면 / 밝은 글자) ──────────────
# 스크린샷으로 확인: 부대 정보 팝업의 상태 표시자.
#   未=미행동 / 済=행동완료 / 停=정지 / 委=위임  (한 줄, 행 55~72, 셀 20x18, 피치 20)
#   偽=위보 / 混=혼란  (상태이상, 행 44~62)
# ⚠️셀마다 **자기 밝기**를 쓴다(테두리 0x7A~0x96, 면 0x1E~0x2B, 잉크 0xED~0xFF) —
#   4셀 공통 픽셀이 4/360뿐이라 行/技식 공통템플릿이 안 통한다. 값은 셀별로 잰다.
# 전부 20x18. 내부 글자상자 = rows 1..16 x cols 2..17 (16x16).
# ★경계는 열/행 프로파일로 실측했다 — 눈대중 21px로 잡았다가 4셀 공통이 4/360으로 나와 들켰다.
BADGE_BOX = (1, 17, 2, 18)
BADGES = {                     # 글자 -> (row0, x, 한글)
    '偽': (45, 20, '위'),   # 위보 (상태이상)
    '混': (45, 40, '혼'),   # 혼란 (상태이상)
    '委': (37, 148, '위'),  # 위임 (별개 사본)
    '未': (55, 160, '미'),  # 미행동
    '停': (55, 180, '정'),  # 정지
    '委2': (55, 200, '위'),  # 위임
    '済': (55, 220, '완'),  # 행동완료 — 未=미와 쌍(세션5 결정)
}


def badge_cell(data, row0, x):
    a = np.frombuffer(data[:len(data) // PITCH * PITCH], np.uint8).reshape(-1, PITCH)
    return a[row0:row0 + 18, x:x + 20].copy()


def badge_levels(cell, box=BADGE_BOX):
    """셀 자신의 면색(최빈값)과 잉크(최대값)를 잰다."""
    from collections import Counter
    r0, r1, c0, c1 = box
    inter = cell[r0:r1, c0:c1]
    face = Counter(inter.ravel().tolist()).most_common(1)[0][0]
    return int(face), int(inter.max())


def make_badge(cell, ch, fontpath, em=14, weight=0.0, box=BADGE_BOX, stretch=False):
    """빈 뱃지(테두리 보존) + 밝은 한글. 명암이 反이라 max로 합성한다."""
    face, ink = badge_levels(cell, box)
    r0, r1, c0, c1 = box
    out = cell.copy()
    out[r0:r1, c0:c1] = face
    a = render_syllable(ch, fontpath, em, weight, stretch)
    y = r0 + ((r1 - r0) - em) // 2
    x = c0 + ((c1 - c0) - em) // 2
    reg = out[y:y + em, x:x + em].astype(np.float32)
    out[y:y + em, x:x + em] = np.rint(np.maximum(reg, face + a * (ink - face)))
    return out


def cell_offset(x):
    return ROW0 * PITCH + x


def poke(data, x, cell):
    """셀을 8bpp/피치512로 제자리 기록. data는 bytearray."""
    assert cell.shape == (CH, CW)
    for i in range(CH):
        o = (ROW0 + i) * PITCH + x
        data[o:o + CW] = cell[i].tobytes()
    return data
