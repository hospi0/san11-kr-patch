"""환경설정 도움말을 RAM에서 찾는다.

## 지금까지
화면: 「必ずプレイヤーが一騎討ちを見た上で操作を担当します」
  운반체 깨짐(一→고 · 操→젰 · 担→천)이 보임 = **일반 폰트로 그려지는 진짜 2바이트 SJIS 텍스트**.
디스크: s11pkres **전 9,383 엔트리** + SLPM + Overlay1/2 + modules/ + pkres/ 어디에도 평문 없음.
        entry3(도움말) 1,179개 메시지도 전부 디코드해봤으나 없음(0~415는 정말 호칭 조립테이블).

## 이 스크립트
**"디스크엔 없는데 RAM엔 있다" = 압축 소스 신호**([[feedback_compressed_corpus_scan]], Shining
파티이름 사건과 같은 패턴). 세이브스테이트 eeMemory에서 찾아 그 사실을 먼저 확정한다.
RAM에 있으면 → 압축/생성이 확정이고, 다음 수는 그 RAM 주소를 쓰는 코드나 압축 엔트리 추적.
RAM에도 없으면 → 그 화면을 안 띄운 스테이트라 당연하므로, 환경설정 화면 스테이트가 필요하다.
"""
import io
import os
import sys

HERE = os.path.dirname(__file__)
STATES = ['state_map', 'state_desc', 'state_fac', 'state_str', 'state_test']
NEEDLES = ['操作を担当', '一騎討ちを見た', 'プレイヤー', '必ずプレイヤー',
           '物資面', '難易度', '見た上で', '担当します']


def find_all(buf, b, cap=20):
    out, i = [], buf.find(b)
    while i >= 0 and len(out) < cap:
        out.append(i)
        i = buf.find(b, i + 1)
    return out


def main():
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    for st in STATES:
        p = os.path.join(HERE, '..', 'work', st, 'eeMemory.bin')
        if not os.path.exists(p):
            continue
        ram = open(p, 'rb').read()
        out.write('\n===== %s (eeMemory %d B) =====\n' % (st, len(ram)))
        for nd in NEEDLES:
            hits = find_all(ram, nd.encode('cp932'))
            out.write('  %-16s %d개 %s\n'
                      % (nd, len(hits), ' '.join('0x%x' % h for h in hits[:6])))
    out.close()


if __name__ == '__main__':
    main()
