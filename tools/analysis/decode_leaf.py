# -*- coding: utf-8 -*-
"""path(예 2023.9)로 leaf 추출 → offset부터 SJIS 디코드해서 보여준다."""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from link import Link
from deep_census import parse_link

ARC = r"C:\claude\roms\ps2\Sangokushi 11 with Power-Up Kit (Japan)\s11pkres.bin"

def get_leaf(arc, path):
    b = arc.read(path[0])
    for p in path[1:]:
        subs = parse_link(b)
        off,sz = subs[p]
        b = b[off:off+sz]
    return b

arc = Link(ARC)
path = [int(x) for x in sys.argv[1].split(".")]
off = int(sys.argv[2],0) if len(sys.argv)>2 else 0
length = int(sys.argv[3],0) if len(sys.argv)>3 else 400
b = get_leaf(arc, path)
print(f"leaf {sys.argv[1]} size={len(b)}")
seg = b[off:off+length]
# hex + decode
try:
    print("decode:", seg.decode("cp932", errors="replace")[:300])
except Exception as e:
    print("err", e)
print("hex:", seg[:96].hex())
