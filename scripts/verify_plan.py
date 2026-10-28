"""Verify the final patch plan against a patched exe."""
import json
import re
import sys
from collections import defaultdict
import pefile
import capstone
from pe import PE
from ascii_fold import ascii_fold

PREFIX = re.compile(r"^[a-z_]+@")


def display_text(text):
    return PREFIX.sub("", text, count=1)

orig = PE(open(r"backup\ostriv_original.exe", "rb").read())
raw = open(sys.argv[1], "rb").read()
patched = PE(raw)
plan = json.load(open("data/patch_plan.json", encoding="utf-8"))
analysis = {r["off"]: r for r in json.load(open("data/analysis.json", encoding="utf-8"))}
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
MD.detail = True

print("--- pefile check")
pe = pefile.PE(sys.argv[1], fast_load=False)
for s in pe.sections:
    name = s.Name.rstrip(b"\0").decode("ascii", "replace")
    print(f"  {name:8} VA={s.VirtualAddress:#x} vsize={s.Misc_VirtualSize} rawsize={s.SizeOfRawData} chars={s.Characteristics:#x}")
sec = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".ptbr")
print("SizeOfImage:", hex(pe.OPTIONAL_HEADER.SizeOfImage), "ptbr VA:", hex(sec.VirtualAddress), "vsize:", sec.Misc_VirtualSize)


def lea_target(lea_off):
    insn_rva = patched.off_to_rva(lea_off)
    insn = next(MD.disasm(raw[lea_off:lea_off + 7], patched.image_base + insn_rva), None)
    if insn is None or insn.mnemonic != "lea":
        return None
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
            return patched.va_to_off(insn.address + insn.size + op.mem.disp)
    return None


ok = bad = 0
for r in plan["relocs"]:
    expected = display_text(r["text"]).encode("utf-16-le")
    t = lea_target(r["lea"])
    if t is not None and raw[t:t + len(expected)] == expected:
        ok += 1
    else:
        bad += 1
        if bad <= 8:
            print("  RELOC FAILED:", r["en"][:50], "lea", hex(r["lea"]), "target", hex(t) if t else None)

print(f"pair relocations: {ok} ok, {bad} failed")

# standalone
refs = defaultdict(list)
text = next(s for s in orig.sections if s["name"] == ".text")
for i in range(text["rawptr"], text["rawptr"] + text["rawsize"] - 7):
    if orig.data[i] in (0x48, 0x4C) and orig.data[i + 1] == 0x8D and (orig.data[i + 2] & 0xC7) == 0x05:
        insn_rva = orig.off_to_rva(i)
        disp = int.from_bytes(orig.data[i + 3:i + 7], "little", signed=True)
        refs[(insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF].append(i)

ok = bad = 0
for s in plan["standalones"]:
    text_pt = display_text(s["text"] if s["enc"] == "utf16" else ascii_fold(s["text"]))
    expected = text_pt.encode("utf-8") if s["enc"] == "utf8" else text_pt.encode("utf-16-le")
    if raw[s["off"]:s["off"] + len(expected)] == expected:
        ok += 1
        continue
    targets = [lea_target(i) for i in refs.get(orig.off_to_rva(s["off"]), [])]
    if any(t is not None and raw[t:t + len(expected)] == expected for t in targets):
        ok += 1
    else:
        bad += 1
        if bad <= 8:
            print("  STANDALONE FAILED:", s["en"][:50], s["enc"])

print(f"standalone: {ok} ok, {bad} failed")
