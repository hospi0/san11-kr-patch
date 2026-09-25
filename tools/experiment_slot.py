# -*- coding: utf-8 -*-
"""entry4 슬롯 확대 실기 이분 실험 (2026-07-18 세션9).

목적: entry4를 슬롯(710,656 B) 너머로 키우면 RAM 압축해제 버퍼(0x1da1c00)가
      **밀리는가(동적, 안전) / 자기 자리에 고정이라 크래시하는가**를 실기로 판별한다.

방법(유일 변수 = entry4 크기): entry4 **내용은 원본 그대로** 두고 뒤에 0패딩해 크기만
  709,268 → 목표(기본 720,000)로 키운다. LS11은 블록테이블 오프셋으로 찾으므로 꼬리 0패딩은
  디코드에 무해하다(poke_e4와 같은 원리). LINK 엔트리[5] 크기필드도 목표로 고친다.
  → 게임이 entry4를 목표 크기로 RAM에 로드 → 버퍼 자리(0x1da1c00) 침범 → 화면으로 판정.

⚠️**파괴적**: entry4 자리 뒤 시나리오 산문 영역(섹터979~)을 목표-709,268 만큼 덮어쓴다.
  실험 중 시나리오 텍스트는 깨진다. 우리가 볼 건 **환경설정(block23)·지도(block0)·무장열전**
  화면이 정상인가뿐이다. 정상이면 버퍼 동적 → dict/bio/... 슬롯 확대 가능.
  백업(.expbak)으로 완전 복구된다.

판정:
  - 세 화면 정상        → 버퍼 동적. entry4를 목표 크기까지 키워도 안전(= 슬롯 확대 가능).
  - 크래시/화면 깨짐    → 버퍼가 그 자리 고정. 슬롯 710,656은 하드 한계.

Usage:
  python tools/experiment_slot.py <iso> [--size 720000] [--restore]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import walk, find                                    # noqa: E402

ORIG_SIZE = 709268
LINK_ENTRY5_SIZE_OFF = 0x34        # s11 + 0x34 = entry4 크기필드 (엔트리[5])


def main():
    iso = sys.argv[1]
    size = ORIG_SIZE
    for i, a in enumerate(sys.argv):
        if a == '--size':
            size = int(sys.argv[i + 1])
    restore = '--restore' in sys.argv

    f, vol, ents = walk(iso)
    _, lba, _sz = find(ents, 'S11PKRES.BIN')
    s11 = lba * 2048
    e4_off = s11 + 0x13c000        # entry4 = 섹터632
    bak = iso + '.expbak'

    if restore:
        if not os.path.exists(bak):
            raise SystemExit('백업 %s 없음 — 복구 불가' % bak)
        b = open(bak, 'rb').read()
        # 형식: [8B size필드원본][8B 덮은영역 시작off][나머지 = 덮은영역 원본]
        sizefield = b[:8]
        ovl_off = struct.unpack('<Q', b[8:16])[0]
        ovl = b[16:]
        with open(iso, 'r+b') as w:
            w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
            w.write(sizefield[:4])
            w.seek(ovl_off)
            w.write(ovl)
        print('복구 완료: 크기필드 + 시나리오 영역 %d B 원상복귀' % len(ovl))
        return

    # 순수 실험: 크기필드만 키우고 디스크 데이터는 **아무것도 안 건드린다**(변수 완전 격리).
    #   entry4 뒤 시나리오 데이터가 그대로라 엔트리[6] 읽기는 정상 → 시나리오 변수 제거.
    #   게임은 entry4를 목표 크기로 RAM 로드 → 슬롯 침범 = RAM 슬롯 순수 테스트.
    #   LS11은 블록테이블 오프셋으로 찾으므로 꼬리 잉여(시나리오)는 디코드에 무시된다.
    if '--size-only' in sys.argv:
        with open(iso, 'r+b') as w:
            w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
            sizefield = w.read(8)
            cur = struct.unpack('<I', sizefield[:4])[0]
            if not os.path.exists(bak):
                with open(bak, 'wb') as bf:
                    bf.write(sizefield)
                    bf.write(struct.pack('<Q', e4_off + ORIG_SIZE))   # overlay 없음(len 0)
                print('백업 저장: %s (크기필드만)' % bak)
            w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
            w.write(struct.pack('<I', size))
        print('순수 실험: 크기필드 %d → %d (디스크 데이터 불변, 시나리오 온전)' % (cur, size))
        print('  RAM entry4 끝: 0x%x (버퍼 0x1da1c00 %s)'
              % (0x1cf4400 + size, '침범' if 0x1cf4400 + size > 0x1da1c00 else '이내'))
        print('  → 부팅 정상=RAM슬롯 유연(dict 가능) / 검은화면=RAM슬롯 고정(dict 불가)')
        print('  ⚠️ 복구: python tools/experiment_slot.py "%s" --restore' % iso)
        return

    # 대조 실험: 크기는 원본 유지, 시나리오만 덮는다(변수 격리).
    # 이게 정상 부팅되면 → 검은화면 원인 = 크기 초과 확정. 이것도 검은화면이면 → 시나리오 덮음이 원인.
    if '--overlay-only' in sys.argv:
        ovl_len = 20732        # 730000 실험과 같은 양
        ovl_off = e4_off + ORIG_SIZE
        with open(iso, 'r+b') as w:
            w.seek(ovl_off)
            ovl_orig = w.read(ovl_len)
            if not os.path.exists(bak):
                w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
                sizefield = w.read(8)
                with open(bak, 'wb') as bf:
                    bf.write(sizefield)
                    bf.write(struct.pack('<Q', ovl_off))
                    bf.write(ovl_orig)
                print('백업 저장: %s (%d B)' % (bak, len(ovl_orig)))
            w.seek(ovl_off)
            w.write(b'\x00' * ovl_len)
        print('대조 실험: entry4 크기 원본 %d 유지 + 시나리오 %d B만 덮음' % (ORIG_SIZE, ovl_len))
        print('  → 부팅해서 확인. 정상=크기초과가 검은화면 원인 / 검은화면=시나리오덮음이 원인')
        print('  ⚠️ 복구: python tools/experiment_slot.py "%s" --restore' % iso)
        return

    if size <= ORIG_SIZE:
        raise SystemExit('--size는 %d 초과여야 실험 의미가 있다' % ORIG_SIZE)

    with open(iso, 'r+b') as w:
        # 현재 크기필드 읽어서 검증
        w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
        cur = struct.unpack('<I', w.read(4))[0]
        print('현재 LINK 크기필드: %d (원본 %d)' % (cur, ORIG_SIZE))

        # 덮어쓸 영역 = entry4 원본 끝 ~ 목표 끝
        ovl_off = e4_off + ORIG_SIZE
        ovl_len = size - ORIG_SIZE
        w.seek(ovl_off)
        ovl_orig = w.read(ovl_len)

        # 백업 저장 (한 번만 — 이미 있으면 덮지 않음)
        if not os.path.exists(bak):
            w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
            sizefield = w.read(8)
            with open(bak, 'wb') as bf:
                bf.write(sizefield)
                bf.write(struct.pack('<Q', ovl_off))
                bf.write(ovl_orig)
            print('백업 저장: %s (%d B)' % (bak, len(ovl_orig)))
        else:
            print('백업 이미 있음 (재실행) — 유지')

        # 1) entry4 뒤를 0으로 (LS11 꼬리 0패딩 = 디코드 무해)
        w.seek(ovl_off)
        w.write(b'\x00' * ovl_len)
        # 2) LINK 크기필드를 목표로
        w.seek(s11 + LINK_ENTRY5_SIZE_OFF)
        w.write(struct.pack('<I', size))

    print('실험 적용: entry4 크기 %d → %d B (슬롯 710,656 %s)'
          % (ORIG_SIZE, size, '초과 +%d' % (size - 710656) if size > 710656 else '이내'))
    print('  RAM entry4 끝: 0x%x (버퍼 0x1da1c00 %s)'
          % (0x1cf4400 + size, '침범' if 0x1cf4400 + size > 0x1da1c00 else '이내'))
    print('  → 부팅해서 환경설정·지도·무장열전 화면 확인.')
    print('  ⚠️ 복구: python tools/experiment_slot.py "%s" --restore' % iso)


if __name__ == '__main__':
    main()
