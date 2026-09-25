"""사용자 번역 TSV(`my files/tokki_desc_kr.tsv`)를 받아 검증 → 정본 `work/tokki_kr.tsv`.

★**예산 검사는 반드시 실제 인코더(Codec.encode)로 한다.** 손으로 len(s)*2를 세면
인코더와 어긋나 거짓 통과/거짓 초과가 난다 — 세션3(ASCII 전각 거짓통과)·세션5({ESC}를
5B로 세서 거짓초과)에서 같은 버그가 정반대로 두 번 났다. [[feedback_kr_patch_verification]]

## 예산 두 줄
- jpB  = 원문 바이트. 이하면 **무조건 안전**(원본이 그 자리에 그만큼 썼다).
- capB = 옆 필드 위치로 **추론한** 용량(특기 67 / 기교 42 / 능력 31). **미검증**.
  jpB < len ≤ capB 인 줄은 '아마 되지만 실기 확인 필요' 구간이다.
  capB 초과는 옆 필드를 깔아뭉개므로 **무조건 거부**.
"""
import io
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from encoding import Codec   # noqa: E402

ELF = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01"
SRC = os.path.join(HERE, '..', 'my files', 'tokki_desc_kr.tsv')

CAP = {'특기': 0x43, '기교': 0x2a, '능력': 0x1f}


def main():
    codec = Codec(ELF)
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    rows = []
    for ln in io.open(SRC, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if not ln or ln.startswith('#') or ln.startswith('table\t'):
            continue
        f = ln.split('\t')
        rows.append(f)

    out.write('# 받은 줄 %d\n' % len(rows))

    empty, unenc, over_cap, over_jp = [], [], [], []
    for f in rows:
        tbl, idx, off, name, jpb, capb, jp = f[0], f[1], f[2], f[3], int(f[4]), int(f[5]), f[6]
        kr = f[7].strip() if len(f) > 7 else ''
        if not kr:
            empty.append((tbl, idx, name))
            continue
        try:
            enc = codec.encode(kr)        # ★검사기 = 인코더
        except Exception as e:
            unenc.append((tbl, idx, name, kr, str(e)))
            continue
        n = len(enc)
        cap = CAP[tbl]
        if n > cap:
            over_cap.append((tbl, idx, name, kr, n, cap))
        elif n > jpb:
            over_jp.append((tbl, idx, name, kr, n, jpb, cap))

    out.write('\n===== 1. 커버리지 =====\n')
    out.write('빈 kr: %d\n' % len(empty))
    for e in empty:
        out.write('  %s\n' % (e,))

    out.write('\n===== 2. 인코딩 불가 =====\n')
    out.write('%d건\n' % len(unenc))
    for u in unenc:
        out.write('  %s\n' % (u,))

    out.write('\n===== 3. capB 초과 (거부 — 옆 필드 침범) =====\n')
    out.write('%d건\n' % len(over_cap))
    for o in over_cap:
        out.write('  %-4s idx%-3s %-6s %dB > cap %dB : %s\n'
                  % (o[0], o[1], o[2], o[4], o[5], o[3]))

    out.write('\n===== 4. jpB 초과 but capB 이내 (미검증 구간) =====\n')
    out.write('%d건 — 원본보다 길다. capB가 추론값이라 실기 확인 전엔 보증 못 함.\n'
              % len(over_jp))
    for o in sorted(over_jp, key=lambda x: -x[4])[:20]:
        out.write('  %-4s idx%-3s %-6s %dB (원본 %dB, cap %dB) : %s\n'
                  % (o[0], o[1], o[2], o[4], o[5], o[6], o[3]))
    if len(over_jp) > 20:
        out.write('  … 외 %d건\n' % (len(over_jp) - 20))

    # 테이블별 최대치 (인코딩 되는 줄만)
    out.write('\n===== 5. 테이블별 번역 최대 바이트 =====\n')
    for tbl in CAP:
        got = []
        for f in rows:
            if f[0] != tbl or len(f) <= 7 or not f[7].strip():
                continue
            try:
                got.append(len(codec.encode(f[7].strip())))
            except Exception:
                pass          # 2번 절이 이미 잡았다
        if got:
            out.write('%s: 최대 %dB / cap %dB / cap초과 %d건\n'
                      % (tbl, max(got), CAP[tbl], sum(1 for g in got if g > CAP[tbl])))
    out.close()


if __name__ == '__main__':
    main()
