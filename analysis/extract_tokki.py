"""특기(特技) 100개 추출 — 포맷 해독 완료판.

## 테이블
entry5 base **0x5210**, stride **0x5d**(93), **100개**, 0x5210 ~ 0x7664.
검산 4중:
  1. (0x7664 - 0x5210) / 0x5d = 정확히 100.0 (나머지 0)
  2. 끝 0x7664 = 기교 테이블 base와 정확히 일치(빈틈 0)
  3. 앞쪽 이웃 = 관직 테이블(0x4382 stride 0x2e × 80, 끝 0x51e2) — 겹침 없음
  4. 100 = 삼국지11의 알려진 특기 수

## 레코드(93B) — 열별 널/값분포 100개 전수로 확정(tokki_columns.py)
  +0x00  이름   4B + \0   ★+0x04가 100/100 널 = 모든 특기 이름이 정확히 2한자
  +0x05  읽기   ≤18B + \0 ★+0x05·+0x07이 100/100 0x83 = 카타카나 리드바이트
  +0x18  설명   \0 종료   ★+0x18~+0x37 널 0% & 짝수열만 값종류 16~22 = SJIS 리드
  +0x5b  플래그 2B        ★+0x5b는 값 3종뿐(0x02가 60/100)

⚠️★★**널을 따라 걷는 파서를 쓰지 말 것.** 읽기·설명 필드의 남는 꼬리에 옛 레이아웃의
찌꺼기가 그대로 남아 있어서(게임은 \0까지만 읽으니 무해), 널 추적 파서는 그 찌꺼기를
문자열 시작으로 오인해 2바이트 어긋난 채 디코드한다. 지난 세션의 `work/tokki_raw.tsv`가
「バ輸送部隊の…」「tロU撃した…」처럼 깨져 나온 게 전부 이 이유다. **필드는 고정 오프셋으로
직접 읽어라.**
"""
import io
import os
import re
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
BASE, STRIDE, COUNT = 0x5210, 0x5d, 100
F_NAME, F_READ, F_DESC, F_FLAG = 0x00, 0x05, 0x18, 0x5b

KATA = re.compile(r'^[ァ-ヶー・]+$')
# 찌꺼기 검출기: 어긋난 디코드는 항상 반각가나(ﾚ ﾍ ｺ…)나 라틴 문자로 튀어나온다.
# ⚠️반각 숫자·마침표·％는 찌꺼기가 아니다 — 게임 자체 문자열이 「50％」「1.5倍」로 쓴다
#   (encoding.py 참조: 반각 ASCII는 의도된 것). 처음에 이걸 찌꺼기로 잡아 9건 거짓양성이 났다.
JUNK = re.compile(r'[｡-ﾟA-Za-z�]')


def field(rec, off, limit):
    """고정 오프셋에서 \\0까지 읽는다. 필드를 넘어가면 자른다."""
    end = rec.find(b'\x00', off, off + limit)
    if end < 0:
        end = off + limit
    try:
        return rec[off:end].decode('cp932'), end - off
    except UnicodeDecodeError:
        return None, end - off


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    out.write('idx\toff\t이름\t읽기\t설명\t설명B\t여유B\n')

    bad_name = bad_read = bad_desc = 0
    maxdesc = 0
    for i in range(COUNT):
        off = BASE + i * STRIDE
        rec = blob[off:off + STRIDE]
        name, _ = field(rec, F_NAME, F_READ - F_NAME)
        read, _ = field(rec, F_READ, F_DESC - F_READ)
        desc, dlen = field(rec, F_DESC, F_FLAG - F_DESC)

        if not name or len(name) != 2:
            bad_name += 1
        if not read or not KATA.match(read):
            bad_read += 1
        if not desc or JUNK.search(desc):
            bad_desc += 1
        maxdesc = max(maxdesc, dlen)
        out.write('%d\t0x%04x\t%s\t%s\t%s\t%d\t%d\n'
                  % (i, off, name, read, desc, dlen, (F_FLAG - F_DESC) - dlen))

    out.write('\n# ===== 검증 =====\n')
    out.write('# 레코드 %d개\n' % COUNT)
    out.write('# 이름이 2한자가 아닌 것: %d\n' % bad_name)
    out.write('# 읽기가 순수 카타카나가 아닌 것: %d\n' % bad_read)
    out.write('# 설명에 이상문자가 섞인 것: %d\n' % bad_desc)
    out.write('# 설명 최대 길이 %d B / 필드 용량 %d B (+0x18~+0x%02x)\n'
              % (maxdesc, F_FLAG - F_DESC, F_FLAG))
    out.close()


if __name__ == '__main__':
    main()
