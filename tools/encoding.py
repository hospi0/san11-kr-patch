"""Korean text codec for San11 PUK (PS2).

Strategy
--------
The game looks a 2-byte SJIS code up in the table at SLPM_667.01+0x4389E0 and
gets a glyph slot. We do not touch that lookup at all -- we keep the game's own
code->slot mapping and simply repaint the glyphs those slots point at.

So a kanji codepoint becomes an opaque carrier for a Hangul syllable:
  Hangul syllable i  <->  the i-th kanji SJIS code (in ascending SJIS order)

Kept as-is (their glyphs stay untouched, and Korean needs them):
  punctuation, full-width alnum, symbols, greek, enclosed numbers, kana.
Census (tools/analysis/slot_census.py): 3,442 kanji vs 2,350 KS X 1001 syllables
-> 1,092 codes spare.

This keeps the encoder trivial and means NO executable patching for text: only
glyph pixels in s11pkres.bin and the string bytes themselves change.
"""
import re
import struct
import unicodedata

TABLE_OFF, TABLE_N = 0x4389E0, 0x2c00
SPACE = b'\x81\x40'          # ideographic space; the renderer special-cases it

# Korean punctuation -> the twin the game's font already carries.
# 가운뎃점 in particular: Korean uses U+00B7, the font has U+30FB (・).
PUNCT_ALIAS = {
    '·': '・', '‧': '・', '•': '・',
    '“': '”', '”': '”', '‘': '”', '’': '”',
    '—': '－', '–': '－', '−': '－',
    '～': '～', '~': '～',
    '《': '《', '》': '》', '「': '「', '」': '」',
    '『': '『', '』': '』', '【': '【', '】': '】',
    '…': '…', '⋯': '…',
}
REV_ALIAS = {'・': '·'}


def _idx(c):
    if 0x8100 <= c <= 0x9fff: return c - 0x8100
    if 0xe000 <= c <= 0xeaff: return c - 0xC100
    if 0xed00 <= c <= 0xeeff: return c - 0xC300
    return c - 0xC400


def _sjis_codes():
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0)):
        for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            yield (lead << 8) | trail


def ks_syllables():
    """KS X 1001 완성형 2350 Hangul syllables, in standard (EUC-KR) order."""
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try:
                ch = bytes([hi, lo]).decode('euc-kr')
            except Exception:
                continue
            if len(ch) == 1 and 0xAC00 <= ord(ch) <= 0xD7A3:
                out.append(ch)
    return out


JAMO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ' + 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'


class Codec:
    def __init__(self, elf_path):
        d = open(elf_path, 'rb').read()
        tab = struct.unpack('<%dH' % TABLE_N, d[TABLE_OFF:TABLE_OFF + TABLE_N * 2])
        self.slot_of = {}
        kanji, keep = [], {}
        for code in _sjis_codes():
            i = _idx(code)
            if not (0 <= i < TABLE_N) or tab[i] == 0xffff:
                continue
            try:
                ch = struct.pack('>H', code).decode('cp932')
            except Exception:
                continue                      # unassigned code aliasing a slot
            self.slot_of[code] = tab[i]
            if 0x4E00 <= ord(ch) <= 0x9FFF:
                kanji.append(code)
            else:
                keep.setdefault(ch, code)     # first code wins

        kanji.sort()
        syl = ks_syllables()
        if len(kanji) < len(syl):
            raise SystemExit('only %d kanji codes for %d syllables' % (len(kanji), len(syl)))
        self.kanji_pool = kanji
        self.syllables = syl
        self.enc = {ch: kanji[i] for i, ch in enumerate(syl)}   # Hangul -> carrier code
        # 이름 입력 조합용 자모 40개(초성 19 + 중성 21) = 운반체 2350~2389 (2026-11-21, docs/17)
        self.jamo = JAMO
        for j, ch in enumerate(JAMO):
            self.enc[ch] = kanji[len(syl) + j]
        self.keep = keep                                        # kept char -> its own code
        self.dec = {v: k for k, v in self.enc.items()}

    def code_for(self, ch):
        if ch in self.enc:
            return self.enc[ch]
        if ch in self.keep:
            return self.keep[ch]
        # Korean punctuation that has a Japanese twin already in the font
        alias = PUNCT_ALIAS.get(ch)
        if alias and alias in self.keep:
            return self.keep[alias]
        # Full-width fallback for ASCII. encode() emits half-width bytes instead
        # (see below) -- this path is only for callers that want the wide form.
        if 0x21 <= ord(ch) <= 0x7E:
            fw = chr(ord(ch) + 0xFEE0)
            if fw in self.keep:
                return self.keep[fw]
        return None

    def encode(self, text, halfwidth_space=True, halfwidth_ascii=True):
        """Korean text -> SJIS-carrier bytes. Raises on any unmappable char.

        Space is the single-byte ASCII 0x20 by default: verified on hardware
        2026-07-16 (main menu build). It costs 1 B instead of 2 AND looks right --
        the ideographic space is visibly too wide for Korean word spacing.
        Pass halfwidth_space=False only if some context needs the wide space.

        ASCII 0x21-0x7E is likewise emitted as the raw single byte. This is not an
        optimisation, it is REQUIRED: the game's own strings use half-width ASCII
        ("%3d年%2d月%2d日" is 25 33 64 ..., "SELECT", "三國志11 with"), and printf
        only recognises a half-width '%'. Widening it to '％３ｄ' would print the
        spec literally instead of substituting -- and cost 2 B per char on slots
        that have no room. Half-width renders fine and is untouched by our glyph
        work: it does not go through the 2-byte SJIS->slot table, so repainting
        kanji slots cannot break it (confirmed on hardware -- SELECT/L1/R2 render
        correctly in the roster+places build).
        """
        out = bytearray()
        for ch in text:
            if ch == ' ':
                out += b'\x20' if halfwidth_space else SPACE
                continue
            if halfwidth_ascii and 0x21 <= ord(ch) <= 0x7E:
                out += bytes([ord(ch)])
                continue
            # Half-width katakana (U+FF61-FF9F) is also a single byte, 0xA1-0xDF.
            # The game uses it -- e.g. 0xA5 '･' in UI, and the 決戦 battle blurbs
            # use it for particles. Round-trip it as-is rather than losing it.
            if 0xFF61 <= ord(ch) <= 0xFF9F:
                out += bytes([ord(ch) - 0xFF61 + 0xA1])
                continue
            code = self.code_for(ch)
            if code is None:
                raise KeyError('no mapping for %r (U+%04X)' % (ch, ord(ch)))
            out += struct.pack('>H', code)
        return bytes(out)

    def decode(self, b):
        out, j = '', 0
        while j < len(b):
            # Half-width ASCII is a single byte and can never be an SJIS lead
            # (leads are 0x81-0x9F / 0xE0-0xEF), so resolve it before trying a
            # 2-byte read -- otherwise "%3d" gets eaten as the pair (25 33).
            if 0x20 <= b[j] <= 0x7E:
                out += ' ' if b[j] == 0x20 else chr(b[j])
                j += 1
                continue
            if 0xA1 <= b[j] <= 0xDF:
                out += chr(b[j] - 0xA1 + 0xFF61)      # 반각 카타카나
                j += 1
                continue
            if j + 1 < len(b):
                code = struct.unpack('>H', b[j:j + 2])[0]
                if code == 0x8140:
                    out += ' '; j += 2; continue
                if code in self.dec:
                    out += self.dec[code]; j += 2; continue
                try:
                    ch = b[j:j + 2].decode('cp932')
                    out += REV_ALIAS.get(ch, ch); j += 2; continue
                except Exception:
                    pass
            out += '[%02x]' % b[j]; j += 1
        return out

    def fit(self, text, capacity, halfwidth_space=False):
        """encode and check it fits the slot, NUL terminator included"""
        b = self.encode(text, halfwidth_space)
        return b, len(b) + 1 <= capacity

    def glyph_slots(self):
        """[(slot, syllable)] -- where each Hangul glyph must be painted."""
        return [(self.slot_of[self.enc[ch]], ch) for ch in self.syllables]

    def encode_ui(self, text, **kw):
        """Like encode(), but with the UI control-code tokens spelled out.

        UI format strings embed two raw control bytes that are part of the string:
            {ESC} = 0x1b   colour select / restore:  \x1b[%dx ... \x1b[0x
            {N}   = 0x0a   line break
        extract_ui.parse() surfaces them as tokens (it used to throw the whole
        string away on hitting one, which lost 12 printf templates -- that is why
        "平原(平原) 設置：不可" still showed a Japanese 設置 on hardware).
        """
        out = bytearray()
        for part in re.split(r"(\{ESC\}|\{N\})", text):
            if part == "{ESC}":
                out += b"\x1b"
            elif part == "{N}":
                out += b"\x0a"
            elif part:
                out += self.encode(part, **kw)
        return bytes(out)


if __name__ == '__main__':
    import sys
    c = Codec(sys.argv[1])
    print('kanji carrier pool : %d' % len(c.kanji_pool))
    print('syllables to map   : %d' % len(c.syllables))
    print('spare kanji codes  : %d' % (len(c.kanji_pool) - len(c.syllables)))
    print('kept as-is         : %d' % len(c.keep))
    print()
    CAP = 16          # the main-menu string slots are a fixed 16 B stride
    print('  %-16s %3s %5s %s' % ('text', 'B', 'fits', 'roundtrip'))
    for s in ('이어서 하기', '새로 시작', '튜토리얼', '결전 제패 모드', '결전제패모드',
              '무장 등록·편집', '옵션', '환경 설정'):
        try:
            b, ok = c.fit(s, CAP)
        except KeyError as e:
            print('  %-16s  !! %s' % (s, e)); continue
        print('  %-16s %3d %5s %s' % (s, len(b), 'OK' if ok else 'OVER', c.decode(b) == s))
