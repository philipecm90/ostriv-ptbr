"""List every LEA to a help string in the building-help initializer, in order."""
import struct
from pe import PE

EXE = r"backup\ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
BASE = pe.image_base


def read_any(off):
    # UTF-16
    j = off
    chars = []
    while j + 1 < len(data):
        u = data[j] | (data[j + 1] << 8)
        if u == 0:
            break
        if not ((u >= 32 and (u < 0x500 or 0x2000 <= u <= 0x206F or u == 0x20AC)) or u in (9,10,13)):
            chars = None
            break
        chars.append(chr(u))
        j += 2
    if chars:
        s = "".join(chars)
        if len(s) >= 8 and any(ch.isalpha() for ch in s):
            return "u16", s
    # UTF-8
    j = data.find(b"\x00", off)
    try:
        s = data[off:j].decode("utf-8")
        if len(s) >= 8 and all(ch.isprintable() or ch in "\n\r\t" for ch in s) and any(ch.isalpha() for ch in s):
            return "u8", s
    except UnicodeDecodeError:
        pass
    return None


rows = []
for i in range(0x200000, 0x220000 - 7):
    if data[i] in (0x48, 0x4C) and data[i + 1] == 0x8D and (data[i + 2] & 0xC7) == 0x05:
        insn_rva = pe.off_to_rva(i)
        disp = struct.unpack_from("<i", data, i + 3)[0]
        tgt = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
        off = pe.rva_to_off(tgt)
        r = read_any(off) if off is not None else None
        if r:
            enc, s = r
            cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
            lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
            lang = "UK" if cyr > lat else "EN"
            rows.append((i, off, enc, lang, s))

print("rows:", len(rows))
for i, off, enc, lang, s in rows:
    print(f"{i:#07x} -> {off:#07x} {enc} {lang} {len(s):5d} {s[:80]!r}")
