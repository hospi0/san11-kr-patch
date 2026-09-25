# -*- coding: utf-8 -*-
"""entry4 블록 **압축 해제 버퍼** 확대 — SLPM 즉시값 2바이트 패치.

★★★2026-07-29, 실기 이분 실험 14회로 규명. 「외교 동맹파기 사신 이벤트가 대사 도중 끊긴다」

증상의 진짜 변수는 **블록 크기가 아니라 메시지 오프셋**이었다(둘이 같이 움직여 오래 헷갈렸다).
결정타 = 크기를 **더 키우면서** 문제 메시지의 오프셋만 고정한 실험:

    앞540줄        크기 88,848  idx619 오프셋 77,599  → 통과
    앞540+뒤100줄  크기 92,329  idx619 오프셋 77,599  → **통과**  ← 크기 무죄 확정
    앞556줄        크기 89,087  idx619 오프셋 77,838  → 실패
    전체686줄      크기 93,736  idx619 오프셋 78,974  → 실패

  통과 최대 오프셋 77,599 / 실패 최소 오프셋 77,838  →  임계 ∈ (77,599, 77,838]

SLPM 전체에서 그 범위의 값을 만드는 곳은 **한 군데뿐**이다:

    VA 0x22174c   lui $v0,0x1            ; v0 = 0x10000
    VA 0x22175c   jal 0x21f060           ; 블록 로드/해제
    VA 0x221760   ori $a1,$v0,0x3000     ; a1 = 0x13000 = 77,824  ← 버퍼 크기 인수

한국어는 원본 대비 +19.4% 라 blk0(93,736)·blk1(97,545)·blk26(91,805)이 이 한계를 넘는다.
즉 **번역을 줄이는 문제가 아니라 상수 하나** 문제였다.

RAM 실측(세이브스테이트): 블록은 0x1da1c00 에 풀리고 그 뒤로 **162,866 B가 널**이다.
0x1C000(114,688)을 써도 다음 데이터(0x1ddbe04)까지 여유가 남는다.
"""
import struct

# ★★★2026-07-29 후반 — **할당 지점을 찾았다.** 위 「부팅 불가」의 정체는 힙 고갈이었다.
#
#   VA 0x21f060 = 범프 얼로케이터
#       힙 베이스 0x01CD6400 / 용량 0x000DEC00 (912,384 B) / 커서 [0x01CD4320]
#       if (커서 + 요청 >= 용량) return 0;      ← 실패하면 NULL 을 준다
#       ptr = 베이스 + 커서;  memset(ptr,0,요청);  커서 += 요청
#
#   세이브스테이트 4개(일본어 2 + 한글 2) 전부 **커서 0xDE800 = 911,360 / 912,384, 잔여 1,024 B**.
#   블록 버퍼가 마지막 할당이고 0x1DA1C00~0x1DB4C00 을 차지한다(힙 끝 0x1DB5000).
#   → a1 만 0x18000 으로 키우면 0xCB800+0x18000 = 0xE3800 > 0xDEC00 이라 **할당 실패 → NULL**.
#     그래서 부팅이 안 됐던 것이다. **용량 상수를 같이 키워야 한다.**
#
#   덤: 해제 루틴(0x181e30)에는 **크기 인자가 없다** — 경계검사 자체가 없다. 실제로 한글
#   스테이트는 버퍼 끝을 넘어 데이터가 이어져 있다(버퍼끝~힙끝 1,022/1,024 B 비제로).
#   일본어 원판은 그 자리가 전부 0(원본 blk0 = 75,218 B라 안 넘친다).
#   즉 「잘려서 없다」가 아니라 **할당 안 된 땅에 써 놓아 보호를 못 받는다**가 진상이다.
#
# slpm.bin 오프셋 = VA − 0xFFF00 (ui_kr.tsv 의 off/VA 관계와 동일)
VA_DELTA = 0xFFF00
PATCH_VA = 0x221760
PATCH_OFF = PATCH_VA - VA_DELTA          # 0x121860

# 힙 용량 상수 (lui/ori 두 워드로 0x000DEC00 을 만든다)
CAP_VA_LUI = 0x21f08c                    # lui $v1, 0xd
CAP_VA_ORI = 0x21f094                    # ori $v0, $v1, 0xec00
CAP_OFF_LUI = CAP_VA_LUI - VA_DELTA      # 0x11f18c
CAP_OFF_ORI = CAP_VA_ORI - VA_DELTA      # 0x11f194
CAP_ORIG = (0x3c03000d, 0x3462ec00)      # → 0x000DEC00 = 912,384
CAP_NEW = (0x3c03000f, 0x34624000)       # → 0x000F4000 = 999,424 (+87,040)
OLD_CAP = 0x000DEC00
NEW_CAP = 0x000F4000
HEAP_BASE = 0x01CD6400
# 힙 배치(스테이트 실측): entry3 0x1E000 + entry4 슬롯 + 블록버퍼. entry4 슬롯은
# e4_reloc 의 이사로 0xAD800(347섹터) → 0xBE000(380섹터)로 넓어진다.
ENTRY3_SLOT = 0x1E000
E4_SLOT = 380 * 0x800                    # e4_reloc.SLOT_MAX 와 같은 값
CURSOR_AT_ALLOC = ENTRY3_SLOT + E4_SLOT  # 블록버퍼 할당 직전 커서(최악값)

# ⛔2026-07-29 실기: NEW_IMM=0xC000(0x1C000=114,688)로 키우자 **부팅 자체가 안 됐다.**
#   → a1 은 「버퍼 크기를 알려주는 값」이고 **버퍼 실체는 다른 곳에서 0x13000으로 잡힌다**는 뜻.
#     이 값만 키우면 버퍼를 넘어 써서 인접 데이터를 파괴한다.
#     버퍼 할당 지점(a0 = s0+0xE54 가 가리키는 곳)을 먼저 찾아 함께 키워야 한다.
#   0x18000(98,304, 최대블록이 딱 들어가는 최소값)로 **절반만** 키워도 역시 부팅 실패.
#   → 이 즉시값만으로는 확대 불가. ⚠️당시 결론(「버퍼 실체가 다른 곳에서 고정」)은 **틀렸다**.
#     진짜 이유는 힙 고갈이었고, 용량 상수를 같이 키우면 된다(위 참조). 2026-07-29 재개.
ENABLED = True

ORIG_WORD = 0x34453000                   # ori $a1,$v0,0x3000  → 0x13000 = 77,824
NEW_IMM = 0x8000                         # → 0x18000 = 98,304 (최대블록 97,545 가 딱 들어가는 최소값)
NEW_WORD = (ORIG_WORD & ~0xFFFF) | NEW_IMM

OLD_SIZE = 0x13000
NEW_SIZE = 0x10000 | NEW_IMM

# 로드 주소와 그 뒤 여유(세이브스테이트 실측) — 확대 상한의 근거
LOAD_ADDR = 0x1DA1C00
NEXT_DATA = 0x1DDBE04


def check(elf_bytes):
    """패치 전 원본 명령이 그대로인지. (ok, 현재워드)"""
    w = struct.unpack_from("<I", elf_bytes, PATCH_OFF)[0]
    return w in (ORIG_WORD, NEW_WORD), w


def _poke(w, elf_off, off, orig, new, what):
    """한 워드 교체. 이미 새 값이면 통과, 둘 다 아니면 중단."""
    w.seek(elf_off + off)
    cur = struct.unpack("<I", w.read(4))[0]
    if cur == new:
        return False                                 # 이미 적용됨
    if cur != orig:
        raise SystemExit("%s 패치 지점이 예상과 다르다: 0x%08x @ slpm 0x%x" % (what, cur, off))
    w.seek(elf_off + off)
    w.write(struct.pack("<I", new))
    return True


def apply_to_iso(w, elf_off):
    """ISO 안 SLPM 의 **버퍼 크기 + 힙 용량**을 함께 확대. (이전크기, 새크기) 반환.

    ★둘 중 하나만 하면 안 된다 — 크기만 키우면 힙이 모자라 할당이 NULL 을 뱉고 부팅이 죽는다.
    """
    if not ENABLED:
        return OLD_SIZE, OLD_SIZE
    # 새 요청이 힙에 들어가는지 정적 검증 (스테이트 실측 커서 기준)
    if CURSOR_AT_ALLOC + NEW_SIZE > NEW_CAP:
        raise SystemExit("새 버퍼가 새 힙 용량에도 안 들어간다: 0x%x + 0x%x > 0x%x"
                         % (CURSOR_AT_ALLOC, NEW_SIZE, NEW_CAP))
    if HEAP_BASE + NEW_CAP > NEXT_DATA:
        raise SystemExit("힙 확대가 뒤 데이터를 침범한다 (0x%x > 0x%x)"
                         % (HEAP_BASE + NEW_CAP, NEXT_DATA))
    _poke(w, elf_off, CAP_OFF_LUI, CAP_ORIG[0], CAP_NEW[0], "힙 용량(lui)")
    _poke(w, elf_off, CAP_OFF_ORI, CAP_ORIG[1], CAP_NEW[1], "힙 용량(ori)")
    _poke(w, elf_off, PATCH_OFF, ORIG_WORD, NEW_WORD, "블록 버퍼 크기")
    return OLD_SIZE, NEW_SIZE


def verify_iso(path, elf_off):
    """빌드된 ISO 를 **독립적으로 되읽어** 세 워드가 실제로 들어갔는지 확인."""
    want = ((CAP_OFF_LUI, CAP_NEW[0]), (CAP_OFF_ORI, CAP_NEW[1]), (PATCH_OFF, NEW_WORD))
    with open(path, "rb") as r:
        for off, exp in want:
            r.seek(elf_off + off)
            got = struct.unpack("<I", r.read(4))[0]
            if got != exp:
                raise SystemExit("버퍼 패치 되읽기 불일치 @slpm 0x%x: %08x != %08x"
                                 % (off, got, exp))
    return True


def max_block_ok(blocks):
    """블록 해제크기 목록이 새 버퍼에 들어가는지. (ok, 최대블록, 여유)"""
    m = max(blocks)
    return m <= NEW_SIZE, m, NEW_SIZE - m
