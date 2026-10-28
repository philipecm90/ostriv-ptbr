"""Extract localized string pairs (English UTF-8, Ukrainian UTF-16) with the exact
LEA instructions that load each literal, so shared string data can be patched per use.
"""
import struct
from pe import PE
import capstone

EXE = r"backup/ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
text = next(s for s in pe.sections if s["name"] == ".text")
tstart = text["rawptr"]
tend = tstart + text["rawsize"]

EN_CTOR = 0x1404116E0
UK_CTOR = 0x1404104B0
COMBINE = 0x1402A9770
BASE = pe.image_base

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = True
insns = list(md.disasm(data[tstart:tend], BASE + text["va"]))
print("instructions:", len(insns))


def rip_target(insn):
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
            return (insn.address + insn.size + op.mem.disp) & 0xFFFFFFFFFFFFFFFF
    return None


def call_target(insn):
    if insn.mnemonic == "call" and insn.operands and insn.operands[0].type == capstone.x86.X86_OP_IMM:
        return insn.operands[0].imm
    return None


def read_cstr(off, utf16=False):
    if utf16:
        j = off
        while data[j:j + 2] != b"\0\0":
            j += 2
        return data[off:j].decode("utf-16-le", "replace")
    j = data.find(b"\0", off)
    return data[off:j].decode("utf-8", "replace")


pairs = []
for idx, insn in enumerate(insns):
    if call_target(insn) != COMBINE:
        continue
    en_off = uk_off = None
    en_lea = uk_lea = None
    j = idx - 1
    while j >= 0 and idx - j < 40:
        ct = call_target(insns[j])
        if ct in (EN_CTOR, UK_CTOR):
            k = j - 1
            while k >= 0 and j - k < 6:
                if insns[k].mnemonic == "lea" and insns[k].op_str.startswith("rdx,"):
                    t = rip_target(insns[k])
                    if t is not None:
                        off = pe.va_to_off(t)
                        lea_off = pe.rva_to_off(insns[k].address - BASE)
                        if ct == EN_CTOR and en_off is None:
                            en_off, en_lea = off, lea_off
                        elif ct == UK_CTOR and uk_off is None:
                            uk_off, uk_lea = off, lea_off
                    break
                k -= 1
        if en_off is not None and uk_off is not None:
            break
        j -= 1
    if en_off is None or uk_off is None:
        continue
    pairs.append((insn.address, en_off, read_cstr(en_off), uk_off, read_cstr(uk_off, True),
                  en_lea, uk_lea))

print("pairs:", len(pairs))
with open("data/pairs.tsv", "w", encoding="utf-8", newline="") as f:
    f.write("call\tenoff\ten\tukoff\tuk\tenlea\tuklea\n")
    for p in pairs:
        f.write("\t".join(str(x).replace("\t", " ").replace("\n", "\\n") for x in p) + "\n")
print("wrote data/pairs.tsv")
