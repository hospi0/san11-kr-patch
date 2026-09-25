"""기교(技巧) 테이블과 능력연구 테이블을 stride로 열거한다.

기교: base 0x7664, stride 0x5c.
  rec+0x00  이름\\0 (SJIS)
  이어서    읽기(카타카나)\\0 — ★단 이름 바로 뒤가 아닐 때가 있다(奇襲: 사이에 2B 필드).
            그래서 '이름 다음' 대신 '레코드 안 첫 순수 카타카나'로 잡는다.
  rec+0x55  u16 금
  rec+0x57  u16 필요기교P
  ★검산: 槍兵鍛錬 = 금1000/기교P1000 — 사용자 스크린샷(기교표)과 일치해야 한다.
  나머지 필드(관여능력·선행조건)는 미해독.

능력연구: base 0xa7a4, stride 0x4a, 66개.
  rec+0x00 이름\\0, rec+0x0d 「X」を武将に習得させる
  ★검산: 0xa7a4 + 66*0x4a = 0xbab8 = entry5 크기와 정확히 일치(파일 끝에서 떨어진다).

경계는 stride를 가정해 놓고 "이름 크립이 깨지는 곳"으로 잡되, 커버리지를 같이 찍는다
([[feedback_scan_coverage_and_detectors]]).
"""
import io
import os
import re
import struct
import sys

ENTRY5 = os.path.join(os.path.dirname(__file__), '..', 'work', 'entry5.bin')
KATA = re.compile(r'^[ァ-ヶー・]+$')
# 이름은 상용한자/전각 기호만. 카타카나·히라가나·제어문자가 섞이면 테이블 밖.
NAME_OK = re.compile(r'^[一-鿿０-ｚ]{2,6}$')


def cstr(blob, off):
    end = blob.find(b'\x00', off)
    if end < 0:
        return None, len(blob)
    try:
        return blob[off:end].decode('cp932'), end + 1
    except UnicodeDecodeError:
        return None, end + 1


def first_kata(blob, lo, hi):
    """레코드 안에서 첫 순수 카타카나 문자열(3자 이상)을 찾는다."""
    off = lo
    while off < hi:
        s, nxt = cstr(blob, off)
        if s and len(s) >= 2 and KATA.match(s):
            return s
        if nxt <= off:
            break
        off = nxt
    return ''


def walk_gikou(blob, out):
    base, stride = 0x7664, 0x5c
    out.write('===== 기교(技巧): base 0x%x stride 0x%x =====\n' % (base, stride))
    out.write('#\toff\t이름\t읽기\t금\t기교P\n')
    n, off = 0, base
    while off + stride <= len(blob):
        name, nxt = cstr(blob, off)
        if not name or not NAME_OK.match(name):
            break
        rec = blob[off:off + stride]
        gold, pts = struct.unpack('<HH', rec[0x55:0x59])
        out.write('%2d\t0x%04x\t%-6s\t%-14s\t%d\t%d\n'
                  % (n, off, name, first_kata(blob, nxt, off + stride), gold, pts))
        n += 1
        off += stride
    out.write('# 기교 %d개, 0x%x ~ 0x%x (끊긴 이유: 0x%x의 이름 크립 실패)\n'
              % (n, base, off, off))
    nm, _ = cstr(blob, off)
    out.write('# 0x%x 자리 문자열 = %r\n' % (off, nm))
    return n


def walk_nou(blob, out):
    base, stride = 0xa7a4, 0x4a
    out.write('\n===== 능력연구: base 0x%x stride 0x%x =====\n' % (base, stride))
    n, off = 0, base
    names = []
    while off + stride <= len(blob):
        name, _ = cstr(blob, off)
        if not name or not NAME_OK.match(name):
            break
        desc, _ = cstr(blob, off + 0xd)
        names.append(name)
        out.write('%2d\t0x%04x\t%-6s\t%s\n' % (n, off, name, desc))
        n += 1
        off += stride
    out.write('# 능력연구 %d개, 0x%x ~ 0x%x / 파일크기 0x%x → %s\n'
              % (n, base, off, len(blob), '끝에서 정확히 떨어짐' if off == len(blob) else '어긋남!'))
    out.write('# 고유 이름 %d개 (중복 %d = 트리에 같은 특기가 여러 노드)\n'
              % (len(set(names)), len(names) - len(set(names))))
    return n


def main():
    blob = open(ENTRY5, 'rb').read()
    out = io.open(sys.argv[1], 'w', encoding='utf-8')
    walk_gikou(blob, out)
    walk_nou(blob, out)
    out.close()


if __name__ == '__main__':
    main()
