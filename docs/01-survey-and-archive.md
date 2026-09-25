# 01 — 초기 조사 & LINK 아카이브 포맷

## 매체·파일 구성
표준 코에이 PS2 타이틀. 디스크 루트:
- `SLPM_667.01` (5.2MB) — 메인 실행파일. **ELF, MIPS R5900 (little-endian)**.
- `Overlay1.bin` / `Overlay2.bin` — 코드 오버레이 (매직 `MWo3`, 각각 파일명 문자열 "Overlay1D.bin" 내장).
- `s11pkres.bin` (517MB) — **메인 리소스 아카이브 (LINK 포맷)**. 폰트·텍스트·그래픽 대부분 여기.
- `movieres.bin` (2GB) — 무비 (한글화 무관).
- `modules/` — IRX 시스템 모듈 (KOEISND.IRX, cdvdstm, hdd, pfs 등). 한글화 무관.
- `pkres/` — 메모리카드 아이콘·재킷 PNG. 한글화 무관.

### 실행파일 ELF 레이아웃
- 단일 LOAD 세그먼트: 파일 offset 0x100 → VA 0x100000, filesz 0x4ffc80.
- **VA = 파일오프셋 + 0xFFF00** (역: 파일 = VA − 0xFFF00).
- entry 0x100008. 코드영역 대략 VA 0x100000~0x440000, 데이터 0x440000~.
- R5900은 MIPS III/IV + MMI(멀티미디어) 확장. capstone `CS_MODE_MIPS64+LITTLE_ENDIAN`로 대부분 해독되나 MMI/branch-likely 일부는 오해독 → **갭 허용 디스어셈블**(실패 시 4바이트 스킵) 필수. (`tools/analysis/disasm2.py` 참고)

## LINK 아카이브 포맷 (s11pkres.bin) — 완전 해독
```
0x00  char[4]  "LINK"
0x04  u32      파일 수 = 9383
0x08  u32      섹터 크기 = 0x800 (2048)
0x0c  u32      0 (reserved)
0x10  엔트리 테이블: 8바이트 × 9383개
        u32 sector_offset   (파일오프셋 = sector_offset * 0x800)
        u32 byte_size
```
- 각 파일은 0x800 정렬. 테이블(9383×8=0x12538) 다음 0x12800(섹터37)부터 데이터.
- **파일명 없음 — 인덱스로만 식별.**
- 무손실 추출·재조립 자명. (`tools/analysis/scan.py` 없음; probe/locate 계열 참고. 파싱 로직은 여러 스크립트 상단에 동일.)

### 내부 리소스 타입 (39종, 대표)
- 중첩 `LINK` (1044개) — 서브아카이브
- `01000000` 헤더형 (7307개) — 그래픽/맵/텍스처 레코드 (동일문자 반복=채움패턴)
- `0000feff`(=0xfffe0000) + u32count + "KOEI%SAN11" — 이름표 컨테이너 (54개). **텍스트 산문이 여기**. idx=1,6,11 등.
- `GCOL` (4개, idx675-678, 789KB) — **raw 8bpp 그레이스케일 이미지** (배경/텍스처 CG). 압축 아님.
- idx=88/89 (11.7/13.3MB) — 월드맵 (연속톤, 16바이트 스트라이드).
- 기타: `FCVD`(376), `KSEF`(224, 사운드), `KM01`(188, 맵), `TOD2`(38), `K3ST`, `AIMG`, `NUNO`, `IECS`.

### 그래픽 저장 방식 핵심
이 게임 그래픽은 **대부분 raw(비압축) 8bpp 안티에일리어스**다. GCOL을 8bpp로 렌더하면 잉크워시 이미지가 나옴(`tools/analysis/gcol8.py`). idx=94는 그래픽으로 구워진 CJK 로고/텍스트(防·国·治…) → graphics-text 교체 대상. **raw 저장 = 편집 유리** (Terra의 VLZ2 같은 압축 함정 없음).
