# -*- coding: utf-8 -*-
"""entry3(도움말)를 키워서 넣기 — 중복 엔트리를 비워 그 자리로 이사시킨다.

문제: 반각 가나 1B가 한글 2B라 entry3가 121,593 → 127,884 B로 커진다(+3섹터). 그런데
아카이브는 **빈틈이 정확히 0**이다(헤더+테이블 75,776B + 엔트리 517,677,056B = 파일크기
517,752,832B 정확히 일치, 엔트리 간 gap 0곳). 제자리에서 키우면 뒤가 전부 밀려 오버플로.

해법: **LINK 엔트리는 (섹터오프셋, 바이트크기) 쌍일 뿐이라 두 엔트리가 같은 섹터를
가리켜도 된다.** 아카이브엔 내용이 바이트 동일한 중복 엔트리가 4,145개(≈110MB) 있다.
  1. 중복 엔트리 V를 그 쌍둥이 T의 섹터로 재지정 → V는 여전히 같은 바이트를 읽는다(무변화)
  2. 비워진 V의 섹터에 새 entry3를 쓰고, entry3의 LINK 엔트리를 그리로 재지정

★근거: 원본 아카이브에도 **이미 같은 (오프셋,크기)를 공유하는 엔트리 그룹이 1개 있다**
  = 이 포맷이 공유를 실제로 쓰고 있다는 증거.
★결과 diff: LINK 테이블 16 B + 새 데이터 63섹터뿐. 나머지 517MB와 파일 크기는 불변이라
  ISO in-place가 유지된다. 남는 여유 ≈110MB = 앞으로 산문 38만 자를 넣고도 남는다.
⚠️쓰기 전용 아카이브라 공유가 안전하다(게임은 읽기만 한다). 내용 동일은 SHA-1로 확인한다.
"""
import hashlib
import struct

HDR = 0x10


def parse(s11):
    """(entries, sec) — entries[i] = (섹터오프셋, 바이트크기)."""
    assert s11[:4] == b"LINK", "LINK 아카이브가 아니다"
    n, sec = struct.unpack("<I", s11[4:8])[0], struct.unpack("<I", s11[8:12])[0]
    ent = [struct.unpack("<II", s11[HDR + i * 8: HDR + i * 8 + 8]) for i in range(n)]
    return ent, sec


def plan(s11, new_data, target=3):
    """entry3 배치 계획. → dict(mode, sector, patches, data_off, data, ...)

    ★**제자리가 최우선이다.** 새 데이터의 섹터 수가 원래 할당과 같으면 디스크 배치를 전혀
      건드리지 않는다 — 원본 레이아웃이 확실히 부팅한다는 걸 아는 이상 그게 제일 안전하다.
      (entry3는 압축 후 122,358 B = 60섹터 = 원래와 동일 → 제자리로 끝난다.)
    ⚠️**단, RAM 슬롯 한계는 별개다**: entry3는 RAM 0x1cd6400에 읽히고 그 뒤 0x1cf4400에
      entry4가 딱 붙어 있어 **122,880 B(0x1E000)를 넘기면 깔아뭉개고 죽는다**(실기 확정).
      섹터를 옮기든 말든 이 한계는 안 변한다 — 크기는 호출부(build_help.py)가 막는다.

    아래 이사 경로는 **그보다 커질 때를 위한 것**이고, 실기로 안전이 확인돼 있다(테스트 A):
    victim 선택은 결정적 — 새 데이터가 들어가는 중복 엔트리 중 할당이 가장 작은 것, 동률이면
    인덱스가 작은 쪽.
    """
    ent, sec = parse(s11)
    need = (len(new_data) + sec - 1) // sec
    old_o, old_b = ent[target]
    if need <= (old_b + sec - 1) // sec:          # ★제자리 — 디스크 배치 불변
        return {
            "mode": "inplace", "victim": None, "twin": None, "sector": old_o, "need": need,
            "victim_alloc": (old_b + sec - 1) // sec, "old": (old_o, old_b),
            "patches": {target: (old_o, len(new_data))},
            "data_off": old_o * sec, "data": new_data, "sec": sec,
        }

    # 내용 해시 → 같은 내용 엔트리 묶기
    seen, twin = {}, {}
    for i, (o, b) in enumerate(ent):
        h = hashlib.sha1(s11[o * sec: o * sec + b]).digest()
        if h in seen:
            twin[i] = seen[h]          # i는 seen[h]의 중복 → 비워도 된다
        else:
            seen[h] = i

    cand = [i for i in twin
            if i != target and (ent[i][1] + sec - 1) // sec >= need]
    if not cand:
        raise SystemExit("이사 보낼 중복 엔트리가 없다 (필요 %d섹터)" % need)
    victim = min(cand, key=lambda i: ((ent[i][1] + sec - 1) // sec, i))
    t = twin[victim]
    assert s11[ent[victim][0] * sec: ent[victim][0] * sec + ent[victim][1]] == \
           s11[ent[t][0] * sec: ent[t][0] * sec + ent[t][1]], "쌍둥이 내용이 다르다"

    new_sector = ent[victim][0]
    # 이사 뒤 겹침 검사: 새 데이터가 victim 할당을 넘으면 안 된다
    assert need <= (ent[victim][1] + sec - 1) // sec, "victim 자리가 모자란다"

    patches = {
        victim: ent[t],                       # 쌍둥이 섹터를 가리키게(크기는 쌍둥이 것 = 동일)
        target: (new_sector, len(new_data)),  # entry3 → 비워진 자리
    }
    return {
        "mode": "relocate", "victim": victim, "twin": t, "sector": new_sector, "need": need,
        "victim_alloc": (ent[victim][1] + sec - 1) // sec,
        "old": ent[target], "patches": patches,
        "data_off": new_sector * sec, "data": new_data, "sec": sec,
    }


def apply_to_iso(w, s11_off, p):
    """ISO 사본에 in-place 적용. w = 'r+b'로 연 ISO, s11_off = ISO 안 s11pkres 시작."""
    for idx, (o, b) in p["patches"].items():
        w.seek(s11_off + HDR + idx * 8)
        w.write(struct.pack("<II", o, b))
    w.seek(s11_off + p["data_off"])
    w.write(p["data"])
    pad = p["need"] * p["sec"] - len(p["data"])      # 섹터 꼬리는 0으로
    if pad:
        w.write(b"\x00" * pad)
