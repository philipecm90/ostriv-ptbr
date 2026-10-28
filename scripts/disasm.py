"""Disassemble around a file offset in .text."""
import sys
import capstone
from pe import PE

EXE = r"backup/ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)


def disasm(off, before=32, count=40):
    start = off - before
    code = data[start:start + 300]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    late = 0
    for insn in md.disasm(code, pe.image_base + pe.off_to_rva(start)):
        mark = ""
        for op in insn.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                target = insn.address + insn.size + op.mem.disp
                mark = f"   ; -> 0x{target:X} (file 0x{(pe.va_to_off(target) or 0):X})"
        print(f"0x{insn.address:X}: {insn.mnemonic:<8} {insn.op_str}{mark}")
        count -= 1
        if count <= 0:
            break


if __name__ == "__main__":
    off = int(sys.argv[1], 0)
    before = int(sys.argv[2], 0) if len(sys.argv) > 2 else 32
    count = int(sys.argv[3], 0) if len(sys.argv) > 3 else 40
    print(f"disasm around file 0x{off:X} rva 0x{pe.off_to_rva(off):X}")
    disasm(off, before, count)
