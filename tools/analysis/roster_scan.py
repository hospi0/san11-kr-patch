# -*- coding: utf-8 -*-
"""Anti-detector 로스터 스캔.
아카이브 전 엔트리를 (1) 단일 성씨-한자 밀도 (2) 가이지(0xF0 리드) 밀도로 랭크.
성+명 연속이 아니라 단일 글자 밀도를 봐서 성/명분리·가이지혼합 로스터도 잡는다.
"""
import os, struct, mmap

ARC = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\s11pkres.bin"

# 게임 내 최다 등장 성씨 (조조·유비·손권 일족 = 로스터라면 반드시 밀집)
SURNAMES = ["曹","劉","孫","張","司","夏","諸","袁","馬","王","李","陳","趙","周","呂","関","黄"]
SUR_B = [s.encode("cp932") for s in SURNAMES]

f = open(ARC,"rb")
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
magic = mm[0:4]; count = struct.unpack_from("<I", mm, 4)[0]
sec = struct.unpack_from("<I", mm, 8)[0]
print(f"magic={magic} count={count} sector={sec}")

entries=[]
for i in range(count):
    so, sz = struct.unpack_from("<II", mm, 0x10 + i*8)
    entries.append((i, so*sec, sz))

def count_sur(buf):
    n=0
    for sb in SUR_B:
        c=buf.count(sb)
        n+=c
    return n

def count_gaiji(buf):
    # 0xF0 다음 바이트 0xB0..0xFF = 가이지 후보
    n=0; i=buf.find(b"\xf0")
    while i!=-1 and i < len(buf)-1:
        if 0xB0 <= buf[i+1] <= 0xFF: n+=1
        i=buf.find(b"\xf0", i+1)
    return n

rank_sur=[]; rank_g=[]
for i, off, sz in entries:
    if sz < 256 or sz > 4_000_000: continue
    buf = mm[off:off+sz]
    cs = count_sur(buf)
    cg = count_gaiji(buf)
    if cs: rank_sur.append((cs, i, sz))
    if cg: rank_g.append((cg, i, sz))

rank_sur.sort(reverse=True); rank_g.sort(reverse=True)
print("\n=== 성씨-한자 밀도 top20 (cnt, idx, size) ===")
for c,i,sz in rank_sur[:20]:
    print(f"  cnt={c:5d}  idx={i:5d}  size={sz:,}  density={c*2/sz:.3f}")
print("\n=== 가이지(0xF0리드) 밀도 top20 ===")
for c,i,sz in rank_g[:20]:
    print(f"  cnt={c:5d}  idx={i:5d}  size={sz:,}  density={c/sz:.4f}")
