# -*- coding: utf-8 -*-
"""장식체(붓글씨) 글자 그래픽 한글화 — 일기토·설전 연출용.

`battle_words.py`(작은 글자)와 **같은 스타일 전이 엔진**을 쓰되 두 가지가 다르다:
  ①폰트 = **궁서체(batang.ttc index 2)**. 원본이 붓글씨라 바탕체로는 결이 안 맞는다.
    ※본편 본문은 바탕체 유지 — 여긴 '장식체로 제작'하라는 사용자 방침에 따른 예외.
  ②각 텍스처마다 **자기 팔레트**가 필요하다(`my files/gfx/팔레트/`).
    팔레트는 GS 덤프의 업로드에서 뽑았다 — 없으면 색이 깨지므로 반드시 있어야 한다.

## 대상 (전부 s11pkres.bin, 무압축 선형 PSMT8 256x256)
  0x04b05730  설전 先/後/手      -> 선/후/수  (先手·後手를 '手' 공유로 조립 → 한글도 '수' 공유)
  0x04b26510  일기토 武將/対/必殺 -> 무장/대/필살
  0x04b57220  일기토 確認         -> 확인
  0x04b676a0  일기토 交代         -> 교대
  0x04b36990  일기토 合(512x256)  -> 합   ★단어 텍스처 안에 있지만 붓글씨라 장식체로 처리
  ⚠️오프셋은 **GS 업로드 역추적으로 실측한 값**이다. 슬롯 공식 추정값과 다르니 주의.

## 사용
  python tools/ornate_words.py --preview
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_words as bw                                    # noqa: E402

REPO = os.path.dirname(HERE)
PAL_DIR = os.path.join(REPO, 'my files/gfx/팔레트')
S11_SRC = bw.S11_SRC
FONT = 'C:/Windows/Fonts/batang.ttc'
FONT_INDEX = 2               # Gungsuh(궁서체) — 붓글씨 계열

# (텍스처이름, 오프셋, 폭, 높이, 팔레트파일, [(x, y, w, h, 한글[, 배율]), ...])
# ★6번째=배율(그 글자만 크기 조절) / 7번째=(dx, dy) 위치 이동(px).
#   박스는 **옛 글자를 덮어야** 하므로, 글자만 옮기고 싶을 땐 박스가 아니라 dx/dy를 쓴다.
JOBS = [
    ('설전_선수후수', 0x04b05730, 256, 256, '설전_선수후수_CLUT_unswizzled_RGBA256.bin',
     [(3, 6, 81, 95, '선'), (97, 5, 80, 96, '후'), (190, 6, 57, 77, '수')]),
    ('일기토_장식체', 0x04b26510, 256, 256, '일기토_장식체_CLUT_unswizzled_RGBA256.bin',
     # ⚠️'필살'(141,197,105,46)은 **보류**(사용자 지시) — 옛 획 잔재 처리 미확정
     # ★'필살' 박스는 x=133부터 — 왼쪽 ● 버튼 아이콘(x110~128)을 침범하지 않게
     #   잉크 프로파일로 골짜기(x=130)를 실측해 경계를 잡았다.
     # ★배율은 **PERBOX_TARGET 기준**(자기 원본 잉크높이)이다. 옛 공통 median(51)
     #   기준일 때 필살은 0.82였고, 자기 잉크(55) 기준으로 옮기며 0.76으로 환산했다
     #   (43.9x0.82 = 47.3x0.76 = 36.0, 결과 크기 동일). 대는 자기 잉크가 median과
     #   같아 1.45 그대로다.
     # ★★★무장 0.93 / 확인 1.10 = **실기에서 딱 맞은 조합**(2026-07-20 사용자 확인).
     #   건드리지 말 것. 텍스처 원본 잉크는 武将 34 / 確認 32로 거의 같지만
     #   **게임이 두 스프라이트를 다른 배율로 그려서**, 배율을 같게 주면 어긋난다
     #   (실측 비율 1.10/0.93 = 1.18배. 무장을 1.0으로 올리려면 확인이 1.18이어야
     #   하는데 그러면 확인이 66x32 박스를 넘어 잘린다 → 현 조합이 최선).
     #   ⚠️두 번 틀렸다: ①"원본 크기가 같으니 배율도 같게" ②스크린샷 바운딩박스로
     #     크기 비교. ②는 **글자 모양에 오염된다**('인'의 ㅣ는 길고 '장'의 ㅇ은 뭉친다)
     #     — 단어 전체 bbox로 재면 안 되고, 맞는지는 결국 눈으로 봐야 한다.
     [(30, 128, 80, 46, '무장', 0.93), (26, 186, 68, 62, '대', 1.45),
      (133, 188, 120, 60, '필살', 0.76, (10, 0))]),
    ('일기토_확인', 0x04b57220, 256, 256, '일기토_확인_CLUT_unswizzled_RGBA256.bin',
     # ⚠️⚠️박스를 (131,180,78,44)로 넓혔다가 **되돌렸다**(2026-07-20 실기).
     #   주변 알파가 낮아 "여유 있다"고 봤지만, restyle은 **박스 전체를 새로 칠하므로**
     #   넓힌 영역이 자기 글로우로 덮이고, 화면에서 그 자리의 **먹 배너가 지워져
     #   뿌연 사각형**이 됐다. 원래 박스가 글자에 딱 붙어 있던 건 이유가 있었다.
     #   → **박스는 옛 글자에 딱 맞춰라. 크기는 배율로만 조절한다.**
     # 배율 1.10 = 무장 0.93과 짝. 둘은 세트다(위 일기토_장식체 주석 참조).
     [(137, 186, 66, 32, '확인', 1.10)]),
    ('일기토_교대', 0x04b676a0, 256, 256, '일기토_교대필살_CLUT_unswizzled_RGBA256.bin',
     [(180, 205, 68, 36, '교대', 1.15),
      # 큰 必殺 컷인 — 배경이 투명이라 FEATHER 불필요.
      # ★'살' 박스 h는 112까지만 — 더 크면 아래 '交代'를 물고, 그쪽 알파가
      #   완전 불투명이라 최댓값을 가져가서 반투명한 殺이 검출에서 탈락한다.
      (0, 90, 136, 126, '필'), (136, 90, 120, 112, '살')]),
    ('일기토_합', 0x04b36990, 512, 256, '일기토_단어_CLUT_unswizzled_RGBA256.bin',
     [(480, 172, 32, 31, '합')]),
    # 설전 화면 오브에 크게 뜨는 붓글씨 3종. **작은 단어 10개와 같은 텍스처**라
    # battle_words(3i)와 대상이 겹친다 — build_kr._write_boxes(박스만 쓰기) 덕에 공존한다.
    # 좌표 실측: 세 단어 모두 x183..249, 세로 골짜기 y184/y220 으로 갈린다.
    ('설전_장식체', 0x04ab3d10, 256, 256, '설전_단어_CLUT_unswizzled_RGBA256.bin',
     # 박스를 x178..255(78)로 넓혔다 — 폭 제한(MARGIN_W)에 걸려 크기를 키워도
     # 자동으로 도로 줄어드는 걸 막기 위함. 왼쪽 x176~182는 이 밴드에서 비어 있다.
     [(178, 147, 78, 38, '시절'), (178, 185, 78, 36, '고사'),
      (178, 221, 78, 35, '도리')]),
]


def load_pal(name):
    p = os.path.join(PAL_DIR, name)
    if not os.path.exists(p):
        raise SystemExit('팔레트 없음: %s  (GS 덤프에서 먼저 뽑아야 한다)' % p)
    return np.frombuffer(open(p, 'rb').read(), dtype=np.uint8).reshape(256, 4)


bw.FONT_INDEX = FONT_INDEX        # 궁서체로 전환(모듈 전역)

# 텍스처별 색감 보정 override (battle_words 의 전역 상수를 잠시 바꿔 쓴다).
# ★선수후수는 원본이 **청록빛 획**인데 기본값으로는 흰색으로 씻겨 나온다 →
#   채도를 크게 올리고 밝기를 낮춰 청록을 살린다(사용자 요청, 2026-07-19).
# 'SCALE' 은 bw 전역이 아니라 목표 글자높이에 곱하는 값(1.0=원본 잉크높이의 86%)
# 크기가 제각각인 글자가 한 텍스처에 섞여 있으면 중앙값 하나로는 못 맞춘다.
# 이 목록의 텍스처는 **글자마다 자기 원본 잉크높이**를 목표로 쓴다.
# ★일기토_장식체도 편입(2026-07-20). 무장(잉크34)·대(51)·필살(55)이 한 텍스처에
#   섞여 있어 median 51을 공통 target으로 쓰면 **무장만 1.5배로 부푼다**(실기에서
#   "무장과 확인은 같은 크기여야 하는데 다르다"는 지적으로 드러났다).
PERBOX_TARGET = {'일기토_교대', '일기토_장식체'}

SCALE = {
    # 원본 붓글씨는 획이 가늘고 여백이 있는데, 원본 잉크높이를 그대로 목표로 잡으면
    # 한글이 박스에 꽉 차서 획이 뭉툭해지고 외곽선이 두꺼워진다(2026-07-20 미리보기).
    '설전_장식체': 1.08,
}

OVERRIDES = {
    # ★먹 배너·붓획 위에 얹힌 글자 → **밑그림 보존 합성**(COMPOSITE).
    #   옛 FEATHER=7.0 방식은 박스 안을 새로 칠하는 거라 **박스를 가로지르는
    #   붓획이 끊겼다**(2026-07-20 실기 지적). COMPOSITE는 원본을 바탕에 두므로
    #   배너가 온전하다.
    # ★★★ERASE_OLD=False 가 **붓획 끊김의 진짜 해법**이다(2026-07-20 실기).
    #   원인: ERASE_OLD가 옛 글자를 `bright_mask`(밝기)로 잡는데, 이 텍스처들은
    #   **배너 붓획 자체가 밝아서** 획이 통째로 "옛 글자"로 분류된다(실측: 무장
    #   박스의 30%, 대 42%, 필살 41%가 마스크에 들어갔고 그 대부분이 붓획이었다).
    #   그걸 지우니 화면에서 **배너의 붓획이 끊겨** 보였다.
    #   → 새 한글이 옛 한자를 덮으므로 애초에 지울 필요가 없다. 끄면 획이 산다.
    #   ⚠️COMPOSITE(원본 위에 획만 합성)·inpaint(국소 평균 채움)도 만들어봤으나
    #     둘 다 옛 글자의 **글로우**를 못 걷어내 더 뿌옇게 됐다 — 되살리지 말 것.
    #   → 다만 ERASE_OLD를 아예 끄면 **새 글자가 옛 글자보다 작을 때 옛 획이
    #     삐져나온다**(무장 0.88배에서 武의 왼쪽이 남았다). 그래서 지우되
    #     **테두리에 안 닿는 덩어리만**(ERASE_INTERIOR_ONLY) 지운다 = 글자만.
    '일기토_장식체': dict(FEATHER=7.0, ERASE_INTERIOR_ONLY=True),
    # 확인도 붓 소용돌이 위에 있다 → 박스 전체 repaint를 막게 FEATHER를 켠다.
    '일기토_확인': dict(FEATHER=9.0, ERASE_INTERIOR_ONLY=True),
    '설전_선수후수': dict(SAT=1.8, SAT_MAX=3.0, BRIGHT=1.20, CON=1.20,
                    TINT=dict(color=(90, 210, 235), lo=0.45, hi=1.00)),
    # ★한글 음절은 한자보다 속공간이 많아, 같은 굵기로 찍으면 획이 붙어 덩어리가 된다.
    #   원본 붓글씨의 두꺼운 회색 외곽선까지 얹히면 더 뭉툭해진다 → 합성 굵기를 뺀다.
    '설전_장식체': dict(WEIGHT=0.0),
}


# 박스(글자) 단위 override — 한 텍스처 안에서도 글자마다 조건이 다를 때.
# 키 = (텍스처이름, 글자).
BOX_OVERRIDES = {
    # ⚠️무장에 한때 dict(MASK_MODE='bright', FEATHER=16.0)을 걸었다가 **둘 다 되돌렸다**
    #   (2026-07-20 실기). 색 문제는 STYLE_FROM(확인 스타일 이식)으로 이미 해결되므로
    #   이 둘은 부작용만 남았다:
    #   ①MASK_MODE='bright'는 색뿐 아니라 **크기 측정(ink_h)까지** 바꾼다 — 배너 위
    #     글자는 글로우가 밝아서 박스 전체가 잉크로 잡히고(43), 목표가 29→37로 부풀어
    #     무장만 커졌다. **검출 방식을 바꿀 땐 그게 크기 측정에도 쓰인다는 걸 볼 것.**
    #   ②FEATHER=16은 ERASE_OLD의 채움색(박스 배경 중앙값)이 글로우 때문에 밝게
    #     나오는 바람에 **먹 배너에 흰 구멍**을 뚫었다. 텍스처 기본값 7이 맞다.
}

# 스타일을 다른 글자에서 빌려온다 — {(텍스처, 글자): (원본텍스처, 원본글자)}.
# ★화면에서 나란히 뜨는 「무장 확인」이 원본끼리 결이 달라서(武将=외곽선 없는 흰
#   글로우 / 確認=회색 외곽선) 한글로 바꾸면 짝이 안 맞는다. 사용자 지시(2026-07-20)로
#   무장이 확인의 스타일을 그대로 쓰게 했다. 색은 여전히 무장 스프라이트가 원래 쓰던
#   인덱스 안에서만 고른다(battle_words.restyle의 style 인자 참조).
STYLE_FROM = {
    ('일기토_장식체', '무장'): ('일기토_확인', '확인'),
}


def _find_box(tex_name, word):
    """(텍스처이름, 글자) -> (스프라이트 인덱스맵, 팔레트). STYLE_FROM 해석용."""
    for name, off, w, h, palf, boxes in JOBS:
        if name != tex_name:
            continue
        for b in boxes:
            if b[4] != word:
                continue
            x, y, bwid, bh = b[:4]
            s11 = open(S11_SRC, 'rb').read()
            tex = np.frombuffer(s11[off:off + w * h], dtype=np.uint8).reshape(h, w)
            return tex[y:y + bh, x:x + bwid].copy(), load_pal(palf)
    raise SystemExit('STYLE_FROM 대상 없음: %s / %s' % (tex_name, word))


def _apply(name, extra=None):
    base = dict(SAT=bw.SAT, SAT_MAX=bw.SAT_MAX, BRIGHT=bw.BRIGHT,
                CON=bw.CON, TINT=bw.TINT, FEATHER=bw.FEATHER,
                ERASE_OLD=bw.ERASE_OLD, MASK_MODE=bw.MASK_MODE,
                WEIGHT=bw.WEIGHT, COMPOSITE=bw.COMPOSITE,
                ERASE_INTERIOR_ONLY=bw.ERASE_INTERIOR_ONLY)
    for k, v in OVERRIDES.get(name, {}).items():
        setattr(bw, k, v)
    for k, v in (extra or {}).items():
        setattr(bw, k, v)
    return base


def _restore(base):
    for k, v in base.items():
        setattr(bw, k, v)


def build(job):
    """(원본 idx, 교체 idx, 팔레트) 반환"""
    name, off, w, h, palf, boxes = job
    s11 = open(S11_SRC, 'rb').read()
    pal = load_pal(palf)
    _saved = _apply(name)
    tex = np.frombuffer(s11[off:off + w * h], dtype=np.uint8).reshape(h, w)
    out = tex.copy()
    # 원본 글자 높이의 중앙값을 공통 목표로(작은 글자 쪽과 같은 원칙)
    def ink_h(x, y, bwid, bh):
        m = bw.shape_mask(tex[y:y + bh, x:x + bwid], pal)
        ys = np.where(m.any(axis=1))[0]
        return (ys.max() - ys.min() + 1) if len(ys) else None

    hs = []
    for b in boxes:
        v = ink_h(*b[:4])
        if v:
            hs.append(v)
    target = float(np.median(hs)) * bw.MARGIN / 0.86 if hs else None
    if target and name in SCALE:
        target *= SCALE[name]
    for b in boxes:
        x, y, bwid, bh, kr = b[:5]
        # 박스 단위 override는 **잉크높이 측정 전에** 걸어야 한다 —
        # MASK_MODE가 바뀌면 잉크 범위 자체가 달라지기 때문.
        _sb = _apply(name, BOX_OVERRIDES.get((name, kr)))
        if name in PERBOX_TARGET:
            own = ink_h(x, y, bwid, bh)
            t = (own * bw.MARGIN / 0.86) if own else None
        else:
            t = target
        t = t * (b[5] if len(b) > 5 else 1.0) if t else None
        offs = b[6] if len(b) > 6 else (0, 0)
        patch = tex[y:y + bh, x:x + bwid]
        sf = STYLE_FROM.get((name, kr))
        out[y:y + bh, x:x + bwid] = bw.restyle(
            patch, pal, kr, FONT, target_h=t, offset=offs,
            style=_find_box(*sf) if sf else None)
        _restore(_sb)          # 텍스처 override 상태로 복귀
    _restore(_saved)
    return tex, out, pal


def comp(idx, pal):
    h, w = idx.shape
    rgb = pal[idx][:, :, :3].astype(np.float32)
    a = np.clip(pal[idx][:, :, 3].astype(np.float32) / 128.0, 0, 1)[:, :, None]
    yy, xx = np.mgrid[0:h, 0:w]
    chk = np.where(((yy // 8 + xx // 8) % 2) == 0, 45, 70).astype(np.float32)[:, :, None]
    return (rgb * a + chk * (1 - a)).astype(np.uint8)


def preview():
    outdir = os.path.join(REPO, 'preview')
    os.makedirs(outdir, exist_ok=True)
    for job in JOBS:
        name, off, w, h = job[0], job[1], job[2], job[3]
        before, after, pal = build(job)
        SC = 2 if w <= 256 else 1
        sheet = Image.new('RGB', (w * SC, h * SC * 2 + 10), (16, 16, 22))
        sheet.paste(Image.fromarray(comp(before, pal)).resize((w * SC, h * SC),
                                                             Image.NEAREST), (0, 0))
        sheet.paste(Image.fromarray(comp(after, pal)).resize((w * SC, h * SC),
                                                             Image.NEAREST),
                    (0, h * SC + 10))
        p = os.path.join(outdir, 'ornate_%s.png' % name)
        sheet.save(p)
        print('미리보기: %s (위=원본/아래=한글)' % p)


if __name__ == '__main__':
    if '--preview' in sys.argv:
        preview()
    else:
        raise SystemExit('--preview 만 지원 (ISO 패치는 build_kr.py 에서)')
