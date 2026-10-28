"""Parse the building-help initializer: sequence of string constructors and their literals."""
import struct
from pe import PE

EXE = r"backup\ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
BASE = pe.image_base
text = next(s for s in pe.sections if s["name"] == ".text")
t0, t1 = text["rawptr"], text["rawptr"] + text["rawsize"]

CTORS = {0x1404116E0: "EN", 0x140410530: "EN2", 0x1404104B0: "UK"}


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


# find calls in the region
calls = []
lo, hi = 0x200000, 0x220000
for i in range(lo, hi - 5):
    if data[i] == 0xE8:
        rel = struct.unpack_from("<i", data, i + 1)[0]
        rva = pe.off_to_rva(i)
        target = BASE + rva + 5 + rel
        if target in CTORS:
            # nearest previous lea rdx
            for k in range(i - 1, max(lo, i - 20), -1):
                if data[k] in (0x48, 0x4C) and data[k + 1] == 0x8D and (data[k + 2] & 0xC7) == 0x05:
                    insn_rva = pe.off_to_rva(k)
                    disp = struct.unpack_from("<i", data, k + 3)[0]
                    tgt = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
                    off = pe.rva_to_off(tgt)
                    s = read_str(off) if off is not None else None
                    if s:
                        calls.append((i, CTORS[target], off, s))
                    break

print("calls:", len(calls))
for i, kind, off, s in calls:
    print(f"{i:#07x} {kind:3} {off:#07x} {len(s):5d} {s[:80]!r}")
