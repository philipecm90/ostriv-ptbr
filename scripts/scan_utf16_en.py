"""Extract UTF-16 English strings (help texts) with reference counts from ostriv.exe."""
import csv
import json
import re
from collections import defaultdict, Counter
from pe import PE
import capstone

EXE = r"backup/ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
text = next(s for s in pe.sections if s["name"] == ".text")
rdata = next(s for s in pe.sections if s["name"] == ".rdata")
tstart, tend = text["rawptr"], text["rawptr"] + text["rawsize"]
rstart, rend = rdata["rawptr"], rdata["rawptr"] + rdata["rawsize"]
BASE = pe.image_base


def rip_refs():
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    refs = defaultdict(list)
    for insn in md.disasm(data[tstart:tend], BASE + text["va"]):
        for op in insn.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                rva = ((insn.address + insn.size + op.mem.disp) & 0xFFFFFFFFFFFFFFFF) - BASE
                refs[rva].append(pe.rva_to_off(insn.address - BASE))
    return refs


def plausible(u):
    if u < 0x20:
        return u in (9, 10, 13)
    if 0x20 <= u <= 0x24F:
        return True
    if 0x400 <= u <= 0x4FF:
        return True
    if 0x2010 <= u <= 0x203A or u in (0x2116, 0x20AC):
        return True
    return False


def main():
    refs = rip_refs()
    print("refs map:", len(refs))
    blocks = []
    i = rstart
    while i < rend - 2:
        if (i - rstart) % 2 == 0 and (i == rstart or (data[i - 2] == 0 and data[i - 1] == 0)):
            u = data[i] | (data[i + 1] << 8)
            if u >= 0x20 and plausible(u):
                j = i
                chars = []
                good = True
                while j + 1 < rend:
                    u = data[j] | (data[j + 1] << 8)
                    if u == 0:
                        break
                    if not plausible(u):
                        good = False
                        break
                    chars.append(chr(u))
                    j += 2
                s = "".join(chars)
                if good and len(s) >= 8:
                    blocks.append((i, s))
                    i = j + 2
                    continue
        i += 2

    print("utf16 blocks:", len(blocks))

    en, uk = [], []
    for off, s in blocks:
        cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
        lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
        if cyr > lat:
            uk.append((off, s))
        elif lat > 0:
            en.append((off, s))

    print("en:", len(en), "uk:", len(uk))
    print("en chars:", sum(len(s) for _, s in en))

    # references
    records = []
    for off, s in en:
        rva = pe.off_to_rva(off)
        nref = len(refs.get(rva, []))
        records.append(dict(off=off, en=s, refs=nref))

    withref = [r for r in records if r["refs"] > 0]
    print("en with refs:", len(withref), "chars:", sum(len(r["en"]) for r in withref))
    print("en without refs:", len(records) - len(withref))

    # dedupe
    by_text = {}
    for r in withref:
        e = by_text.setdefault(r["en"], dict(en=r["en"], offs=[], refs=0))
        e["offs"].append(r["off"])
        e["refs"] += r["refs"]

    # compare with already-known strings
    known = {}
    for row in list(csv.reader(open("data/strings.tsv", encoding="utf-8"), delimiter="\t"))[1:]:
        known[row[1].replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")] = row[0]
    dup = [t for t in by_text if t in known]
    print("duplicates of utf8 inventory:", len(dup))
    print("new unique utf16 en:", len(by_text) - len(dup), "chars:",
          sum(len(t) for t in by_text if t not in known))

    with open("data/utf16_en.json", "w", encoding="utf-8") as f:
        json.dump([dict(en=t, offs=v["offs"], refs=v["refs"], dup=t in known)
                   for t, v in by_text.items()], f, ensure_ascii=False, indent=1)

    with open("data/utf16_en.tsv", "w", encoding="utf-8", newline="") as f:
        f.write("off\trefs\tdup\ten\n")
        for t, v in sorted(by_text.items(), key=lambda kv: min(kv[1]["offs"])):
            f.write(f"{min(v['offs'])}\t{v['refs']}\t{1 if t in known else 0}\t"
                    f"{t.replace(chr(9),' ').replace(chr(10),'\\n')}\n")

    print("--- sample new strings")
    for t in [t for t in by_text if t not in known][:10]:
        print("  ", t[:130].replace("\n", "\\n"))


if __name__ == "__main__":
    main()
