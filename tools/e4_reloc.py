# -*- coding: utf-8 -*-
"""entry4 를 S11PKRES 안의 **더 넓은 자리로 이사**시켜 압축 예산을 늘린다.

★★배경 (2026-07-29 세션28 규명)
  entry4 의 RAM 슬롯은 코드 상수가 아니라 **LINK 크기 필드를 섹터 올림한 값**이다:

      0x2216c8  jal 0x166a60(핸들, 0, idx=4)      ; LINK 엔트리 4번
      0x2216d0  lw  $v0, 4($v0)                   ; 크기 필드
      0x2216d4~e8  (크기+2047)>>11<<11            ; 섹터 올림
      0x2216f0  jal 0x21f060(a1=올림한 크기)       ; 힙에서 할당
      0x221720  jal 0x166c00(..., 길이=올림한 크기) ; 그 길이만큼 읽기

  즉 **파일을 키우면 슬롯이 저절로 커진다.** 코드는 안 건드려도 되고,
  힙 용량 상수만 같이 올리면 된다([[e4_buffer]]).

  RAM 배치(스테이트 실측): 힙 0x1CD6400 = entry3 0x1E000 + entry4 0xAD800 + 블록버퍼.
  힙 천장(다음 데이터 0x1DDBE04)까지 entry4 슬롯을 ~850 KB 까지 키울 수 있다.

★디스크 자리 만들기 — S11PKRES(517.8 MB) 안엔 빈 섹터가 37개(LINK 테이블)뿐이다.
  대신 **내용이 바이트까지 같은 중복 엔트리가 4,144개(110.6 MB)** 있다. 여분 사본을
  쌍둥이 쪽으로 재지정하면 그 섹터가 빈다(help_reloc 이 idx3 용으로 설계한 수법).
  연속 433섹터를 victim **3개**만으로 확보할 수 있어 그 자리를 쓴다.

  ⚠️이 재지정 경로는 idx3 가 결국 제자리로 끝나서 **실기에서 처음 도는 길**이다.
    되돌리기는 LINK 4엔트리(32 B) 복원이면 끝난다(--restore).

Usage:
  python tools/e4_reloc.py <iso> [--src work/entry4_kr.bin] [--dry] [--restore]
"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import walk, find                                      # noqa: E402
import help_reloc                                               # noqa: E402

SEC = 0x800
HDR = help_reloc.HDR

# ── 이사 계획 (2026-07-29 실측으로 고정) ─────────────────────────────────────
# ★victim 선정 기준: 「내용이 같은 여분 사본」인 것만으로는 부족하다. **그 자산이 무엇인지
#   동정하고, 가장 안 쓰일 것을 고른다.** KM01 3D 모델 계열(idx1032~2059)은
#   **모델 인덱스 = 무장 ID + 1032** 로 매핑된다(로스터 900 + 예비 128 = 1,028; 남만 12명·
#   문관 11명이 한 모델을 공유하는 등 중복 구조가 의미론과 정확히 맞는다).
#     1차 후보였던 1784·1785·1786 = 町娘·童子·童女 = **실제 등장하는 이벤트 단역**이었다.
#     → 같은 조건을 만족하면서 **이벤트 예비 슬롯**인 아래로 교체했다(사용자 판단).
NEW_SECTOR = 174384          # victim 3개(イベ65·66·67)가 비우는 연속 474섹터의 시작
SLOT_SECTORS = 380           # 확보할 슬롯 = 778,240 B (원래 347섹터/710,656 B)
SLOT_MAX = SLOT_SECTORS * SEC
VICTIMS = {1796: 1795, 1797: 1795, 1798: 1795}      # イベ65/66/67 -> 전부 イベ64 와 동일
ORIG_E4 = (632, 709268)      # 원래 LINK[4]

# 힙 용량 요구치 = entry3(0x1E000) + 이 슬롯 + 블록버퍼(0x18000)  → e4_buffer 가 검증
HEAP_NEED = 0x1E000 + SLOT_MAX + 0x18000


def _md5_at(f, base, o, b):
    f.seek(base + o * SEC)
    return hashlib.md5(f.read(b)).hexdigest()


def apply_to_iso(iso_path, src, dry=False, restore=False):
    fh, vol, entries = walk(iso_path)
    fh.close()
    s11 = find(entries, 'S11PKRES.BIN')[1] * SEC

    with open(iso_path, 'r+b') as f:
        f.seek(s11)
        ent, sec = help_reloc.parse(f.read(1 << 20))
        assert sec == SEC, sec

        if restore:
            f.seek(s11 + HDR + 4 * 8)
            f.write(struct.pack('<II', *ORIG_E4))
            print('LINK[4] 원복 → 섹터 %d, %d B' % ORIG_E4)
            print('  ⚠️victim 엔트리는 원본 ISO 에서 다시 복사해야 한다(원래 섹터를 모름).')
            return

        data = open(src, 'rb').read()
        if len(data) > SLOT_MAX:
            raise SystemExit('entry4 가 새 슬롯(%d B)보다 크다: %d B' % (SLOT_MAX, len(data)))

        # 1) victim 재지정 — 내용 동일을 **매번 확인**하고 나서만 건드린다
        moved = 0
        for v, keep in sorted(VICTIMS.items()):
            vo, vb = ent[v]
            ko, kb = ent[keep]
            if (vo, vb) == (ko, kb):
                continue                                   # 이미 재지정됨
            if vb != kb or _md5_at(f, s11, vo, vb) != _md5_at(f, s11, ko, kb):
                raise SystemExit('victim idx%d 와 쌍둥이 idx%d 의 내용이 다르다 — 중단' % (v, keep))
            if not dry:
                f.seek(s11 + HDR + v * 8)
                f.write(struct.pack('<II', ko, kb))
            moved += 1
            print('  victim idx%-5d 섹터%d(%d섹터) → 쌍둥이 idx%d 섹터%d  [내용 동일 확인]'
                  % (v, vo, (vb + SEC - 1) // SEC, keep, ko))
        print('victim 재지정 %d개 (이미 적용 %d개)' % (moved, len(VICTIMS) - moved))

        # 2) entry4 를 새 자리에 기록 (슬롯 꼬리는 0 패딩)
        if not dry:
            f.seek(s11 + NEW_SECTOR * SEC)
            f.write(data + b'\x00' * (SLOT_MAX - len(data)))
            # 3) LINK[4] 재지정
            f.seek(s11 + HDR + 4 * 8)
            f.write(struct.pack('<II', NEW_SECTOR, len(data)))
        print('entry4 %d B → 섹터 %d (슬롯 %d섹터 = %d B, 여유 %d B)'
              % (len(data), NEW_SECTOR, SLOT_SECTORS, SLOT_MAX, SLOT_MAX - len(data)))
        alloc = (len(data) + SEC - 1) // SEC * SEC
        print('게임이 잡을 힙 크기 = %d B (섹터 올림) / 힙 요구 총합 %d B' % (alloc, 0x1E000 + alloc + 0x18000))
        if dry:
            print('(--dry: 안 씀)')


def verify(iso_path, src):
    """빌드된 ISO 를 독립적으로 되읽어 검증."""
    fh, vol, entries = walk(iso_path)
    fh.close()
    s11 = find(entries, 'S11PKRES.BIN')[1] * SEC
    data = open(src, 'rb').read()
    with open(iso_path, 'rb') as f:
        f.seek(s11)
        ent, _ = help_reloc.parse(f.read(1 << 20))
        if ent[4] != (NEW_SECTOR, len(data)):
            raise SystemExit('LINK[4] 되읽기 불일치: %s' % (ent[4],))
        for v, keep in VICTIMS.items():
            if ent[v] != ent[keep]:
                raise SystemExit('victim idx%d 재지정 안 됨: %s vs %s' % (v, ent[v], ent[keep]))
        f.seek(s11 + NEW_SECTOR * SEC)
        if f.read(len(data)) != data:
            raise SystemExit('새 자리의 entry4 데이터 불일치')
    return True


if __name__ == '__main__':
    iso_path = sys.argv[1]
    src = 'work/entry4_kr.bin'
    for i, a in enumerate(sys.argv):
        if a == '--src':
            src = sys.argv[i + 1]
    apply_to_iso(iso_path, src, dry='--dry' in sys.argv, restore='--restore' in sys.argv)
    if '--dry' not in sys.argv and '--restore' not in sys.argv:
        verify(iso_path, src)
        print('✅ 되읽기 검증 통과 (LINK[4] + victim %d개 + 데이터)' % len(VICTIMS))
