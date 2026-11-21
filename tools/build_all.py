# -*- coding: utf-8 -*-
"""한글 패치 **전체** 빌드 — 원본 ISO 사본부터 실기용 ISO까지 한 방에.

★★이 파일이 존재하는 이유: **ISO를 건드리는 도구가 여러 개인데 build_kr.py는 그중 일부만 한다.**
  세션9에 이걸 몰라서 두 번 깨졌다:
    ① `build_kr.py`가 `work/e4_*.tsv` 음절을 아틀라스에 안 넣어 **106자가 운반체 한자로 노출**
       (「죽게 됩니다」→「죽게 喫니다」). → build_kr.py 수집부에 e4_*.tsv 등록해서 고침.
    ② 원본에서 새로 빌드하면서 **`poke_hud.py`를 안 돌려 行/技·부대뱃지가 통째로 일본어로 복귀**.
  둘 다 **빌드도 되읽기도 전부 통과**하고 실기에서만 드러났다. 그래서 순서를 코드로 못박는다.

  ⚠️새 패치 경로(ISO를 쓰는 도구)를 만들면 **반드시 여기에 등록**하라. 안 그러면 다음 사람이
    원본에서 재빌드하는 순간 그 패치가 조용히 사라진다.

단계:
  1. 원본 ISO -> 사본            (--iso 로 목적지 지정)
  2. build_help.py   -> work/entry3_kr.bin   (도움말 idx=3)
  3. build_e4.py     -> work/entry4_kr.bin   (entry4 LS11 재압축)
  4. build_kr.py     -> 사본 in-place        (아틀라스·로스터·지명·UI·entry5·도움말·커맨드그래픽)
  5. poke_e4.py      -> 사본 in-place        (entry4 주입, 0패딩)
  6. poke_hud.py     -> 사본 in-place        (HUD 行/技 + 부대상태 뱃지 7종)
  7. verify_glyphs.py -> 검증               (번역문 음절에 글리프가 다 있는가)
  8. patch_kessen_titles.py -> 사본 in-place (KOEI%SAN11 55개 컨테이너의 시나리오/
                                              튜토리얼/결전제패 타이틀, 90곳 제자리 패치)
  9. xdelta                 -> San11pk_kr.xdelta (배포 패치 + 디코드 MD5 검증)

Usage:
  python tools/build_all.py [--iso <출력>] [--src <원본>] [--font <ttc>] [--ink 18] [--weight 0.7]
                            [--skip-copy]      # 사본 뜨기 생략(이미 원본 사본이 있을 때)
                            [--e4-only bio,dialogue,kessen,sys]  # entry4에 넣을 tsv 종류
                                                                  # (기본값 = dict·tutorial 제외)
                            [--xdelta <출력>]  # 배포 패치 경로(기본 San11pk_kr.xdelta)
                            [--no-verify-xdelta]  # 디코드 검증 생략(권장하지 않음)
"""
import os
import shutil
import subprocess
import sys
import time

# cp949 콘솔에서 ✅/⚠️ 등 이모지 출력 시 UnicodeEncodeError 방지 (빌드·검증은 정상이나 마지막 print가 크래시했었다)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r'C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan).iso'
ISO = r'C:/claude/roms/ps2/San11_kr.iso'
FONT = 'C:/Windows/Fonts/batang.ttc'
INK, WEIGHT = '18', '0.7'
# entry4 슬롯(710,656B)을 dict+tutorial까지 다 넣으면 못 맞춘다(세션17에 처음 실측:
# 전부 포함 718,486B, 7,830B 초과 — dict/tutorial 빼면 705,124B로 여유 4,144B 확보).
# build_all.py를 --only 없이 그냥 돌리면 build_e4.py가 work/e4_*.tsv 전부를 넣으려다
# 슬롯 초과로 거부하므로, 여기서 기본 제외를 못박는다. 필요하면 --e4-only로 덮어쓸 것.
# 2026-07-19 갱신: dialogue·kessen 자연문 유지한 채로 수동 다듬기(trim.txt 워크플로)를
# 거쳐 dict까지 여유를 만들었다(708,791B, 여유 477B). tutorial도 trim.txt 워크플로로
# 406줄+추가 163줄 축약. bio(무장열전, 795/802행 번역 + 이름 미번역 버그 33건 수정)도
# 편입 완료 — entry4_kr 709,215B(제자리 한계 709,268B 대비 여유 53B)로 전부 들어감.
E4_ONLY = 'bio,dialogue,kessen,sys,dict,tutorial'
# 9/9 배포 패치 — 빌드할 때 **항상** 같이 만든다(2026-07-19 사용자 지시).
XDELTA_EXE = r'C:/claude/utils/xdelta.exe'          # xdelta3 3.1.0
XDELTA = os.path.join(ROOT, 'San11pk_kr.xdelta')


def arg(name, default):
    for i, a in enumerate(sys.argv):
        if a == name:
            return sys.argv[i + 1]
    return default


def run(step, args):
    print('\n' + '=' * 68)
    print('[%s] %s' % (step, ' '.join(os.path.basename(a) for a in args[1:3])))
    print('=' * 68)
    env = dict(os.environ, PYTHONIOENCODING='utf-8')   # cp949 콘솔에서 ✓ 등 출력 크래시 방지
    r = subprocess.run([sys.executable] + args, cwd=ROOT, env=env)
    if r.returncode:
        raise SystemExit('★[%s] 실패 (exit %d) — 중단한다.' % (step, r.returncode))


def _md5(path, buf=1 << 22):
    import hashlib
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(buf)
            if not b:
                return h.hexdigest()
            h.update(b)


def make_xdelta(src, iso, out):
    """9/9 배포용 xdelta 패치 생성 + **디코드 검증**.

    ⚠️생성만 하고 끝내면 안 된다 — 패치를 원본에 되먹여 나온 ISO가 방금 빌드한
      ISO와 **MD5까지 같은지** 확인해야 진짜 배포 가능한 물건이다(세션21에 수동으로
      하던 검증을 여기로 승격). `--no-verify-xdelta`로 끌 수 있지만 기본은 켠다.
    """
    print('\n' + '=' * 68)
    print('[9/9 xdelta] %s' % os.path.basename(out))
    print('=' * 68)
    if not os.path.exists(XDELTA_EXE):
        print('⚠️ xdelta.exe 없음(%s) — 패치 생성 건너뜀' % XDELTA_EXE)
        return
    t = time.time()
    r = subprocess.run([XDELTA_EXE, '-e', '-f', '-s', src, iso, out])
    if r.returncode:
        raise SystemExit('★[9/9] xdelta 생성 실패 (exit %d)' % r.returncode)
    print('생성 %s (%s B, %.0f초)'
          % (os.path.basename(out), format(os.path.getsize(out), ','), time.time() - t))

    if '--no-verify-xdelta' in sys.argv:
        print('⚠️ 디코드 검증 생략(--no-verify-xdelta) — 배포 전 반드시 따로 확인할 것')
        return
    t = time.time()
    tmp = out + '.verify.iso'
    try:
        r = subprocess.run([XDELTA_EXE, '-d', '-f', '-s', src, out, tmp])
        if r.returncode:
            raise SystemExit('★[9/9] xdelta 디코드 실패 (exit %d)' % r.returncode)
        a, b = _md5(tmp), _md5(iso)
        if a != b:
            raise SystemExit('★[9/9] ❌MD5 불일치 — 패치가 빌드본을 재현하지 못한다\n'
                             '   디코드본 %s\n   빌드본   %s' % (a, b))
        print('✅디코드 검증 통과 (MD5 %s, %.0f초)' % (a, time.time() - t))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    iso, src = arg('--iso', ISO), arg('--src', SRC)
    font, ink, weight = arg('--font', FONT), arg('--ink', INK), arg('--weight', WEIGHT)
    e4_only = arg('--e4-only', E4_ONLY)
    t0 = time.time()

    if '--skip-copy' not in sys.argv:
        print('[1/9] 원본 사본: %s -> %s' % (os.path.basename(src), os.path.basename(iso)))
        shutil.copy(src, iso)
    else:
        print('[1/9] 사본 생략(--skip-copy)')

    run('2/9 도움말', ['tools/build_help.py'])
    run('3/9 entry4', ['tools/build_e4.py', '--only', e4_only])
    run('4/9 본빌드', ['tools/build_kr.py', iso, font, ink, weight])
    # entry4 는 원래 자리(347섹터)를 넘어서므로 **이사**시킨다(e4_reloc). 옛 제자리 주입은
    # poke_e4.py 로 남아 있으나 709,268 B 이하일 때만 쓸 수 있다.
    run('5/9 entry4 이사·주입', ['tools/e4_reloc.py', iso, '--src', 'work/entry4_kr.bin'])
    run('6/9 HUD', ['tools/poke_hud.py', iso])
    run('7/9 글리프 검증', ['analysis/verify_glyphs.py', iso, src])
    run('8/9 결전제패 타이틀', ['tools/patch_kessen_titles.py', iso])
    run('8b/9 타이틀 로고(큰·작은, 하스피 그림)', ['tools/title_logo_kr.py', 'apply', iso])
    if '--no-movie' in sys.argv:                     # 빠른 시험 빌드(하스피 2026-11-21) — 동영상은 원본 그대로
        print('[8c/9] 동영상 생략(--no-movie) — 자막 없는 시험본')
    else:
        run('8c/9 동영상 한글 자막', ['tools/movie_install.py', iso, src])
    run('8d/9 승리·패배·제패 그림(하스피 그림)', ['tools/result_words_kr.py', 'apply', iso])
    run('8e/9 그림 글자 281장 + 일기토 장식 글자 깨끗한 판', ['tools/gfx_text_install.py', iso])
    make_xdelta(src, iso, arg('--xdelta', XDELTA))

    print('\n' + '=' * 68)
    print('done (%.0f초) -- pcsx2-qt.exe -fastboot -- "%s"' % (time.time() - t0, iso))
    print('(세이브스테이트 로드 금지 - 옛 폰트/데이터가 RAM에 남는다. 새로 부팅.)')


if __name__ == '__main__':
    main()
