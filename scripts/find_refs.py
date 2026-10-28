"""Find references to a given string offset (file offset) in ostriv.exe."""
import sys
import struct
from pe import PE

EXE = r"backup/ostriv_original.exe"


def find_refs(data, pe, off):
    rva = pe.off_to_rva(off)
    va = pe.image_base + rva
    print(f"file off 0x{off:X} rva 0x{rva:X} va 0x{va:X}")
    text = next(s for s in pe.sections if s["name"] == ".text")
    tstart, tend = text["rawptr"], text["rawptr"] + text["rawsize"]
    refs = []

    # RIP-relative LEA/MOV: REX.W + 8D/8B + modrm(mod=00, rm=101)
    for i in range(tstart, tend - 7):
        if data[i] in (0x48, 0x4C) and data[i + 1] in (0x8D, 0x8B):
            modrm = data[i + 2]
            if (modrm & 0xC7) == 0x05:
                disp = struct.unpack_from("<i", data, i + 3)[0]
                insn_rva = pe.off_to_rva(i)
                target = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
                if target == rva:
                    refs.append((i, "rip", i + 7))
                elif rva < target < rva + 0x400:
                    # reference into the middle (substring/offset)
                    pass

    # absolute 8-byte VA (anywhere)
    pat8 = struct.pack("<Q", va)
    start = 0
    while True:
        j = data.find(pat8, start)
        if j < 0:
            break
        refs.append((j, "abs64", j + 8))
        start = j + 1

    # absolute 4-byte RVA (anywhere)
    pat4 = struct.pack("<I", rva)
    start = 0
    cnt = 0
    while True:
        j = data.find(pat4, start)
        if j < 0:
            break
        cnt += 1
        start = j + 1
    print(f"refs: rip={sum(1 for r in refs if r[1]=='rip')} abs64={sum(1 for r in refs if r[1]=='abs64')} abs32rva_raw={cnt}")
    for r in refs[:20]:
        print("   ", hex(r[0]), r[1], "->", hex(pe.off_to_rva(r[0]) or 0))
    return refs


if __name__ == "__main__":
    data = open(EXE, "rb").read()
    pe = PE(data)
    for arg in sys.argv[1:]:
        find_refs(data, pe, int(arg, 0))
