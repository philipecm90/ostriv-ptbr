"""Extract every LEA in the Ukrainian help DB initializer (byte-pattern scan, no desync)."""
import struct
from pe import PE

EXE = r"backup\ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
BASE = pe.image_base


def read_str(off):
    j = off
    chars = []
    while j + 1 < len(data):
        u = data[j] | (data[j + 1] << 8)
        if u == 0:
            break
        if not (u >= 32 and u < 0x500):
            return None
        chars.append(chr(u))
        j += 2
    s = "".join(chars)
    if len(s) >= 2 and any(ch.isalpha() for ch in s):
        return s
    return None


rows = []
for i in range(0x4E000, 0x50F2F - 7):
    if data[i] in (0x48, 0x4C) and data[i + 1] == 0x8D and (data[i + 2] & 0xC7) == 0x05:
        insn_rva = pe.off_to_rva(i)
        disp = struct.unpack_from("<i", data, i + 3)[0]
        tgt = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
        off = pe.rva_to_off(tgt)
        s = read_str(off) if off is not None else None
        if s:
            rows.append((i, off, s))

print("refs:", len(rows))
for insn_off, off, s in rows:
    print(f"{insn_off:#07x} -> {off:#07x} {len(s):5d} {s[:80]!r}")
