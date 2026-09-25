# -*- coding: utf-8 -*-
"""RAM 특정 영역을 16바이트 단위로 hex+SJIS디코드해서 레코드구조를 본다."""
import sys
RAM=r"work\state01\eeMemory.bin"
ram=open(RAM,"rb").read()
start=int(sys.argv[1],0); length=int(sys.argv[2],0) if len(sys.argv)>2 else 0x200
width=int(sys.argv[3],0) if len(sys.argv)>3 else 16
for off in range(start,start+length,width):
    row=ram[off:off+width]
    hx=row.hex(" ")
    try: txt=row.decode("cp932",errors="replace")
    except: txt="?"
    print(f"0x{off:07x}: {hx:<{width*3}} |{txt}")
