"""화면 표시 폭(전각 단위)을 재고, 실기에서 잘린/멀쩡한 샘플로 한계를 역산한다.

## 왜 바이트가 아니라 폭인가
바이트 예산(특기 66B)은 통과했는데 **특기일람 화면에서 설명이 잘렸다**(2026-07-17 실기,
사용자 스크린샷). 능력표는 워드랩을 하지만 **특기일람은 고정 폭 열이라 그냥 자른다**
— 화면마다 동작이 다르다. "능력표에서 워드랩되더라"로 일반화한 게 오판이었다.

## 폭 단위
전각(한글·「」···（）) = 1.0 / 반각(ASCII 공백·숫자·쉼표·마침표) = 0.5

## 실기 근거 (사용자 스크린샷 3장, 특기일람)
잘림   : 연환 · 경국 · 안력
안잘림 : 비장 · 강행 · 반계 · 미도 · 발명 · 조선 · 논객 … (약 30개)
→ 이 둘을 가르는 임계값을 찾는다. **한두 샘플로 역산하지 말 것** — 세션5에서
  참조 4개로 폰트크기 역산했다가 나머지 97개가 잘렸다. [[feedback_kr_patch_verification]]
"""
import io
import os
import sys

HERE = os.path.dirname(__file__)

# 실기에서 확인된 것 (사용자 스크린샷 20260717_1638xx)
CLIPPED = {'連環', '傾国', '眼力'}
OK = {'飛将', '遁走', '強行', '長駆', '推進', '操舵', '踏破', '運搬', '解毒', '掃討',
      '威風', '看破', '洞察', '火神', '神算', '百出', '鬼謀', '深謀', '反計', '妖術',
      '名声', '能吏', '繁殖', '発明', '造船', '指導', '論客', '富豪', '米道', '徴税'}


def width(s):
    """전각 단위 표시 폭."""
    w = 0.0
    for ch in s:
        w += 0.5 if 0x20 <= ord(ch) <= 0x7E else 1.0
    return w


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    rows = [l.rstrip('\n').split('\t') for l
            in io.open(os.path.join(HERE, '..', 'work', 'tokki_kr.tsv'), encoding='utf-8')
            if l.strip() and not l.startswith('#') and not l.startswith('table\t')]

    tok = [(f[3], f[8], width(f[8])) for f in rows if f[0] == '특기']
    cl = sorted(w for n, k, w in tok if n in CLIPPED)
    ok = sorted(w for n, k, w in tok if n in OK)
    out.write('===== 특기일람 표시 폭 역산 =====\n')
    out.write('잘린 것 %d개 : 폭 %s\n' % (len(cl), cl))
    out.write('안잘린 것 %d개: 폭 최대 %.1f (분포 %s)\n' % (len(ok), max(ok), ok))
    out.write('→ 한계는 %.1f 초과 ~ %.1f 이하 사이\n' % (max(ok), min(cl)))
    sep = (max(ok) + min(cl)) / 2
    out.write('→ 두 집합이 겹치나? %s\n'
              % ('❌ 겹침 = 폭 가설 틀림' if max(ok) >= min(cl) else '✅ 안 겹침 = 폭이 원인 맞음'))

    limit = max(ok)          # 실기에서 통과가 확인된 최대폭 = 보수적 안전선
    out.write('\n안전선 = %.1f (실기 통과 최대). 이걸 넘는 특기:\n' % limit)
    bad = sorted([(w, n, k) for n, k, w in tok if w > limit], reverse=True)
    for w, n, k in bad:
        mark = ' ← 실기에서 잘림 확인' if n in CLIPPED else ''
        out.write('  %4.1f  %-4s %s%s\n' % (w, n, k, mark))
    out.write('총 %d개 / 100\n' % len(bad))

    # 기교 효과 — 스크린샷상 「사용가능」 마지막 글자가 테두리에 닿았다(폭 20.0)
    gik = sorted([(width(f[8]), f[3], f[8]) for f in rows if f[0] == '기교'], reverse=True)
    out.write('\n===== 기교 효과 폭 (실기: 투석개발 20.0이 테두리에 딱 붙음) =====\n')
    for w, n, k in gik[:8]:
        out.write('  %4.1f  %-6s %s\n' % (w, n, k))

    nou = sorted([(width(f[8]), f[3], f[8]) for f in rows if f[0] == '능력'], reverse=True)
    out.write('\n===== 능력 설명 폭 (능력표는 워드랩됨 — 실기 확인) =====\n')
    for w, n, k in nou[:4]:
        out.write('  %4.1f  %-8s %s\n' % (w, n, k))
    out.close()


if __name__ == '__main__':
    main()
