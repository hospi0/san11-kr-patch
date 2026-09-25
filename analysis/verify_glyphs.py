"""ISO에 실제로 들어간 한글 텍스트의 **모든 음절에 글리프가 그려졌는지** 독립 검증한다.

★이 검사가 없어서 세션9에 106자가 깨진 채 실기까지 갔다.
  build_e4.py(텍스트 삽입)와 build_kr.py(글리프 렌더)는 **경로가 다르다.** 텍스트만 넣고
  아틀라스에 음절을 등록하지 않으면 그 자리에 **운반체 한자가 그대로 비쳐 나온다**
  (「죽게 됩니다」→「죽게 喫니다」·「바꿀 수」→「바菓 수」). 빌드·되읽기는 전부 통과한다.

방법: 번역 TSV가 쓰는 음절마다 아틀라스 슬롯을 **패치본 ISO와 원본 ISO에서 각각 읽어**
      바이트가 같으면 = 안 그려진 것 = 깨짐.

Usage: python analysis/verify_glyphs.py [<kr.iso> <orig.iso>]
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from encoding import Codec                      # noqa: E402

ELF = r'C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\SLPM_667.01'
KR = r'C:/claude/roms/ps2/San11_kr.iso'
ORIG = r'C:/claude/roms/ps2/Sangokushi 11 with Power-Up Kit (Japan).iso'
S11_OFF, ATLAS, PER = 0x73e000, 0x49810, 224


def syls_of(path, col=4):
    s = set()
    for ln in io.open(path, encoding='utf-8'):
        p = ln.rstrip('\n').split('\t')
        if len(p) > col and p[0].isdigit():
            s |= {c for c in p[col] if '가' <= c <= '힣'}
    return s


def main():
    kr_iso = sys.argv[1] if len(sys.argv) > 2 else KR
    or_iso = sys.argv[2] if len(sys.argv) > 2 else ORIG
    codec = Codec(ELF)

    sources = {}
    w = os.path.join(ROOT, 'work')
    for f in sorted(os.listdir(w)):
        if f.endswith('.tsv') and (f.startswith('e4_') or f in ('help_kr.tsv',)):
            sources[f] = syls_of(os.path.join(w, f))

    # entry3 part1(msg 0·6·14)의 안전 예외는 TSV가 아니라 build_help.py에 하드코딩돼 있어
    # 위 스캔에 안 잡힌다 — 독립검증이 「독립」이려면 여기서도 직접 끌어와야 한다.
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import build_help as _bh                       # noqa: E402
    _reps = list(_bh.PART1_WORD_REPL) + [
        r for rs in _bh.PART1_MSG_REPL.values() for r in rs]
    sources['build_help.PART1_WORD_REPL'] = {
        c for _old, rep in _reps for c in rep if '가' <= c <= '힣'}

    fk, fo = open(kr_iso, 'rb'), open(or_iso, 'rb')

    def drawn(ch):
        slot = codec.slot_of[codec.code_for(ch)]
        fk.seek(S11_OFF + ATLAS + slot * PER)
        a = fk.read(PER)
        fo.seek(S11_OFF + ATLAS + slot * PER)
        return a != fo.read(PER)

    total_bad = 0
    for f, syl in sorted(sources.items()):
        if not syl:
            continue
        bad = sorted(c for c in syl if not drawn(c))
        total_bad += len(bad)
        print('%-18s 음절 %4d자 / 글리프 없음 %3d자 %s'
              % (f, len(syl), len(bad), ''.join(bad) if bad else '✓'))
    print()
    if total_bad:
        print('★★%d자가 글리프 없이 나간다 — 화면에 운반체 한자가 그대로 뜬다.' % total_bad)
        print('   → tools/build_kr.py의 「쓰이는 음절」 수집에 그 TSV를 등록하고 다시 빌드하라.')
    else:
        print('✓ 번역문이 쓰는 모든 음절에 글리프가 있다.')
    return 1 if total_bad else 0


if __name__ == '__main__':
    sys.exit(main())
