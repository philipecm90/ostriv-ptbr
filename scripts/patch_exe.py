"""Patch ostriv.exe with pt-BR.

- Localized pairs: each pair's Ukrainian (UTF-16) LEA is retargeted to a new
  string in a `.ptbr` section. This is per-instruction, so shared literals and
  duplicate strings are handled correctly.
- Standalone literals: overwritten in place when they fit, otherwise relocated
  and their references retargeted. UTF-8 literals are ASCII-folded because the
  game's UTF-8 text path only renders ASCII.

Usage:
  python scripts/patch_exe.py <out.exe> [--identity]
"""
import json
import re
import struct
import sys
from collections import defaultdict
from pe import PE
from ascii_fold import ascii_fold
import capstone

EXE = r"backup\ostriv_original.exe"
BASE = None
data = None
pe = None
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
MD.detail = True


def align(v, a):
    return (v + a - 1) // a * a


PREFIX = re.compile(r"^[a-z_]+@")


def display_text(text):
    """Remove the localization context prefix (e.g. col_title@, lowercase@)."""
    return PREFIX.sub("", text, count=1)


def collect_lea_refs():
    """rva -> [instruction file offsets] for RIP-relative `lea` only (verified)."""
    refs = defaultdict(list)
    text = next(s for s in pe.sections if s["name"] == ".text")
    tstart, tend = text["rawptr"], text["rawptr"] + text["rawsize"]
    for i in range(tstart, tend - 7):
        if data[i] in (0x48, 0x4C) and data[i + 1] == 0x8D and (data[i + 2] & 0xC7) == 0x05:
            insn_rva = pe.off_to_rva(i)
            disp = struct.unpack_from("<i", data, i + 3)[0]
            target = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
            insn = next(MD.disasm(bytes(data[i:i + 7]), BASE + insn_rva), None)
            if insn is None or insn.mnemonic != "lea" or insn.size != 7:
                continue
            for op in insn.operands:
                if (op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP
                        and (insn.address + insn.size + op.mem.disp) & 0xFFFFFFFFFFFFFFFF == BASE + target):
                    refs[target].append(i)
    return refs


def add_section(blob):
    num = pe.num_sections
    sec_tab_end = pe.opt_off + pe.opt_size + num * 40
    if sec_tab_end + 40 > pe.size_of_headers:
        raise SystemExit("no room for another section header")

    sa, fa = pe.section_alignment, pe.file_alignment
    va = align(pe.size_of_image, sa)
    raw_size = align(len(blob), fa)
    raw_ptr = align(len(pe.data), fa)

    header = bytearray(40)
    header[0:8] = b".ptbr\0\0\0"
    struct.pack_into("<I", header, 8, len(blob))
    struct.pack_into("<I", header, 12, va)
    struct.pack_into("<I", header, 16, raw_size)
    struct.pack_into("<I", header, 20, raw_ptr)
    struct.pack_into("<I", header, 36, 0x40000040)
    pe.data[sec_tab_end:sec_tab_end + 40] = header

    struct.pack_into("<H", pe.data, pe.pe_off + 6, num + 1)
    struct.pack_into("<I", pe.data, pe.opt_off + 56, va + align(len(blob), sa))

    pe.data.extend(b"\0" * (raw_ptr - len(pe.data)))
    pe.data.extend(blob)
    pe.data.extend(b"\0" * (raw_size - len(blob)))
    return va


def main():
    global BASE, data, pe
    out_path = sys.argv[1]
    identity = "--identity" in sys.argv

    data = bytearray(open(EXE, "rb").read())
    pe = PE(data)
    BASE = pe.image_base
    lea_refs = collect_lea_refs()
    print("lea targets:", len(lea_refs))

    plan = json.load(open("data/patch_plan.json", encoding="utf-8"))
    analysis = {r["off"]: r for r in json.load(open("data/analysis.json", encoding="utf-8"))}

    # ---- standalone decisions
    inplace = []
    relocate = []
    skipped = []
    for s in plan["standalones"]:
        a = analysis[s["off"]]
        text = s["en"] if identity else (s["text"] if s["enc"] == "utf16" else ascii_fold(s["text"]))
        text = display_text(text)
        enc_text = text.encode("utf-8") if s["enc"] == "utf8" else text.encode("utf-16-le")
        term = 1 if s["enc"] == "utf8" else 2
        if a["mid_lea"] == 0 and len(enc_text) <= a["avail"]:
            inplace.append((s["off"], enc_text + b"\0" * term))
        elif lea_refs.get(pe.off_to_rva(s["off"])):
            relocate.append((s["off"], s["enc"], enc_text + b"\0" * term))
        else:
            skipped.append((s["off"], s["enc"], s["en"][:60]))

    print(f"standalone: in-place {len(inplace)} relocate {len(relocate)} skipped {len(skipped)}")
    for x in skipped[:10]:
        print("   skipped:", x)

    for off, blob in inplace:
        pe.data[off:off + len(blob)] = blob

    # language-specific menu backgrounds: use the English logo art in Portuguese mode
    for off, text in ((0x3E6AE0, "ui_menu_bg_1080_eng.png"),
                      (0x3E6B30, "ui_menu_bg_4k_eng.png"),
                      (0x5B4950, "ui_menu_bg_1080_eng.png"),
                      (0x5B49A0, "ui_menu_bg_4k_eng.png")):
        b = text.encode("ascii") + b"\0"
        if len(b) > 0x30:
            raise SystemExit("asset string too long")
        pe.data[off:off + len(b)] = b

    # ---- build .ptbr blob: pair relocations first, then standalone relocations
    blob = bytearray()
    positions = {}

    def put(enc_text, enc):
        while len(blob) % 2:
            blob.append(0)
        key = (enc_text, enc)
        if key not in positions:
            positions[key] = len(blob)
            blob.extend(enc_text)
        return key

    reloc_pairs = []
    for r in plan["relocs"]:
        text = r["en"] if identity else r["text"]
        text = display_text(text)
        enc_text = text.encode("utf-16-le") + b"\0\0"
        key = put(enc_text, "utf16")
        reloc_pairs.append((r["lea"], key))

    reloc_standalone = []
    for off, enc, enc_text in relocate:
        key = put(enc_text, enc)
        reloc_standalone.append((off, enc, key))

    sec_va = add_section(bytes(blob)) if blob else None
    print(f".ptbr at RVA 0x{sec_va:X}, {len(blob)} bytes" if blob else "no section needed")

    def retarget_lea(lea_off, new_rva):
        insn_rva = pe.off_to_rva(lea_off)
        insn = next(MD.disasm(bytes(pe.data[lea_off:lea_off + 7]), BASE + insn_rva), None)
        if insn is None or insn.mnemonic != "lea" or insn.size != 7:
            raise SystemExit(f"not a lea at {lea_off:#x}")
        struct.pack_into("<i", pe.data, lea_off + 3, new_rva - (insn_rva + 7))

    n = 0
    for lea_off, key in reloc_pairs:
        retarget_lea(lea_off, sec_va + positions[key])
        n += 1
    for off, enc, key in reloc_standalone:
        new = sec_va + positions[key]
        for lea_off in lea_refs[pe.off_to_rva(off)]:
            retarget_lea(lea_off, new)
            n += 1

    print(f"retargeted {n} lea instructions")
    open(out_path, "wb").write(pe.data)
    print("wrote", out_path, len(pe.data), "bytes")


if __name__ == "__main__":
    main()
