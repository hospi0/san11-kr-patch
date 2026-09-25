# -*- coding: utf-8 -*-
"""줄 끝 `{01}C{xx}` 매크로가 일본어 어미를 뱉는 줄들을 정리한다 (2026-07-29 세션28).

배경: 번역이 어미를 한국어에 녹였는데 매크로를 지우면 **고아 인수 바이트**가 남아 파서가 멈춘다
      (사신 이벤트 조기종료 사건). 해법은 **매크로를 살린 채 참조 테이블 쪽 일본어를 비우는 것**.
      그런데 그러려면 그 줄의 한국어가 **어미까지 완결**돼 있어야 한다 — 어간으로 끝나 있으면
      비운 순간 문장이 잘린다. 이 파일이 그 완결 작업이다.

  대상 매크로(모두 줄 끝에서만 쓰임 → 비워도 다른 자리에 영향 없음):
    {01}C{88} = msg[136] 「です/だ」        8줄
    {01}C{93} = msg[147] 「ですね/ですな/だな」 5줄
    {01}C{80} = msg[128] 「あります/ございます/ある」 1줄
  ⛔`{01}C{ec}` = msg[236] 「お見せなさい/ろ/くだされ」는 **본문 중간 19곳**에서 동사 자체를
    공급하므로 비우면 안 된다. 별도 과제.

  어투 판단: `{01}C{0e}`(= 貴公류 호칭)로 부르는 쪽은 **군주 → 신하**라 하대로,
            신하가 아뢰는 줄은 존대로 맞췄다.

Usage: python tools/fix_ctoken_endings.py [--dry]
"""
import io
import os
import shutil
import sys

SRC = 'work/e4_dialogue.tsv'

# (block, index): [(원래 꼬리, 고칠 꼬리)]
EDITS = {
    # ── {01}C{88} = です/だ ────────────────────────────────────────────
    (24, 46):  [('기다리는 게 ', '기다리는 게 좋겠습니다')],      # 신하→군주, 존대
    (24, 215): [('이곳으로 데려오는 게 ', '이곳으로 데려오너라')],  # 군주 명령, 하대
    (24, 811): [('병상에 누워 계시다', '병상에 누워 계시다고 합니다')],
    (24, 834): [('철저히 승부를 내거', '철저히 승부를 내거라')],   # 어간으로 끊겨 있었다
    (24, 884): [('여기까지인 것 ', '여기까지인 듯합니다')],
    (24, 885): [('힘이 필요한 ', '힘이 필요합니다')],
    (24, 888): [('천하만민을 이끄는 게 ', '천하만민을 이끄는 것이 옳습니다')],
    # idx742 「…………잘 있거라」는 이미 완결형이라 손대지 않는다.
    # ── {01}C{93} = ですね/ですな/だな (군주가 신하에게 = 하대) ──────────
    (24, 224): [('뭔가 진언이 있다', '뭔가 진언이 있다고 하는군')],
    (24, 804): [('중대사가 있다', '중대사가 있다고 하는군')],
    (24, 939): [('뭔가 할 말이 있다', '뭔가 할 말이 있다고 하는군')],
    (24, 963): [('뭔가 할 말이 있다', '뭔가 할 말이 있다고 하는군')],
    (24, 986): [('뭔가 할 말이 있다', '뭔가 할 말이 있다고 하는군')],
    # ── {01}C{80} = あります/ある ─────────────────────────────────────
    (24, 893): [('중대한 이야기가 ', '중대한 이야기가 있습니다')],
}


def main():
    dry = '--dry' in sys.argv
    lines = io.open(SRC, encoding='utf-8').read().split('\n')
    idxmap = {}
    for i, ln in enumerate(lines):
        c = ln.rstrip('\r').split('\t')
        if len(c) >= 5 and c[0].isdigit():
            idxmap[(int(c[0]), int(c[1]))] = i
    ok, fails = 0, []
    for key, subs in EDITS.items():
        if key not in idxmap:
            fails.append((key, '행 없음', ''))
            continue
        i = idxmap[key]
        c = lines[i].split('\t')
        for old, new in subs:
            n = c[4].count(old)
            if n != 1:
                fails.append((key, 'old %d회' % n, old))
                continue
            c[4] = c[4].replace(old, new)
            ok += 1
        lines[i] = '\t'.join(c)
    print('수정 %d곳 / 실패 %d곳' % (ok, len(fails)))
    for f in fails:
        print('   ⚠️', f)
    if fails:
        raise SystemExit('실패가 있어 중단한다 — 원문이 바뀌었는지 확인할 것')
    if dry:
        print('(--dry: 파일 안 씀)')
        return
    shutil.copy(SRC, SRC + '.bak_ctoken0729')
    io.open(SRC, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('%s 갱신 (백업 %s)' % (SRC, SRC + '.bak_ctoken0729'))


if __name__ == '__main__':
    main()
