# -*- coding: utf-8 -*-
"""RAM 로스터(0x1c2f560, 1150개 × 0xF0) 전체 추출.
필드: +0x58 姓 / +0x5d 名 / +0x62 字 / +0x67 읽기(카타카나).
가이지(0xf0xx)는 [Gxxxx]로 표시."""
import struct
RAM=r"work\state02\eeMemory.bin"
ram=open(RAM,"rb").read()
START=0x1c2f560; STRIDE=0xF0; N=1150

def decode_field(b):
    """5바이트 필드에서 2바이트 SJIS/가이지 문자 추출."""
    out=[]; i=0
    while i < len(b)-1:
        if b[i]==0 and b[i+1]==0: i+=1; continue
        hi=b[i]; lo=b[i+1]
        pair=bytes([hi,lo])
        if 0xf0<=hi<=0xf1:  # 가이지
            out.append(f"[G{hi:02x}{lo:02x}]"); i+=2; continue
        try:
            out.append(pair.decode("cp932")); i+=2; continue
        except: pass
        i+=1
    return "".join(out)

def read_kana(b):
    """읽기 필드: null까지 카타카나."""
    z=b.find(b"\x00\x00")
    if z<0: z=len(b)
    seg=b[:z].rstrip(b"\x00")
    try: return seg.decode("cp932")
    except: return seg.hex()

rows=[]
gaiji_count=0
for n in range(N):
    r=START+n*STRIDE
    sei=decode_field(ram[r+0x58:r+0x5d])
    mei=decode_field(ram[r+0x5d:r+0x62])
    azana=decode_field(ram[r+0x62:r+0x67])
    yomi=read_kana(ram[r+0x67:r+0x67+0x20])
    name=sei+mei
    if "[G" in name+azana: gaiji_count+=1
    rows.append((n,sei,mei,azana,yomi))

# 출력
import io
with io.open(r"work\roster_ram.txt","w",encoding="utf-8") as f:
    f.write(f"# RAM 로스터 {N}명 @0x{START:x} stride 0x{STRIDE:x}\n")
    f.write(f"# idx\t姓\t名\t字\t読み\n")
    for n,sei,mei,az,yomi in rows:
        f.write(f"{n}\t{sei}\t{mei}\t{az}\t{yomi}\n")

# 통계
nonempty=[r for r in rows if r[1] or r[2]]
print(f"총 {N} 슬롯 중 이름있음 {len(nonempty)}, 가이지포함 {gaiji_count}")
print("\n처음 15명:")
for n,sei,mei,az,yomi in rows[:15]:
    print(f"  #{n:4d} {sei}{mei}  ({az})  {yomi}")
print("\n이름있는 마지막 5명:")
for n,sei,mei,az,yomi in nonempty[-5:]:
    print(f"  #{n:4d} {sei}{mei}  ({az})  {yomi}")
print("\nwork/roster_ram.txt 저장")
