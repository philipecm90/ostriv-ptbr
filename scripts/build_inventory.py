"""Build the definitive list of translatable strings for the pt-BR patch.

Sources:
  * every (english, ukrainian) pair from the localization table initializer
  * standalone English literals that are referenced by code and look like prose
"""
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

NOISE_PATTERNS = [
    "#version", "layout(location", "uniform sampler", "void main",
    "out vec4", "in vec", "MultiByteToWideChar", "WideCharToMultiByte",
]


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


def null_strings(lo, hi):
    """Strings that start right after a NUL byte (or at section start), UTF-8 validated."""
    out = []
    i = lo
    while i < hi:
        if i != lo and data[i - 1] != 0:
            i += 1
            continue
        if 32 <= data[i] < 127 or data[i] >= 0xC2:
            j = i
            ok = True
            while j < hi and data[j] != 0:
                if data[j] < 0x80:
                    j += 1
                else:
                    n = 2 if data[j] < 0xE0 else 3 if data[j] < 0xF0 else 4
                    try:
                        data[j:j + n].decode("utf-8")
                    except UnicodeDecodeError:
                        ok = False
                        break
                    j += n
            if ok and j > i:
                try:
                    out.append((i, data[i:j].decode("utf-8")))
                except UnicodeDecodeError:
                    pass
                i = j + 1
                continue
        i += 1
    return out


def prose(s):
    if len(s) < 5 or len(s) > 2000:
        return False
    if any(p in s for p in NOISE_PATTERNS):
        return False
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in s):
        return False
    if s.endswith((".tst", ".tst2", ".anim", ".png", ".build", ".floor", ".snowblock",
                   ".ogg", ".wav", ".skeleton", ".dll", ".exe", ".dat", ".data", ".ini",
                   ".dat2", ".txt", ".json", ".xml")):
        return False
    if s.startswith(("WARNING", "ERROR", "assert", "Assertion")):
        return False
    if re.fullmatch(r"[A-Za-z0-9_./\\%\-]+", s):
        return False
    if "_" in s and "[" not in s:
        return False
    if re.search(r"[a-z][A-Z][a-z]", s) and " " not in s:
        return False
    # needs to look like a sentence/label: at least one space and one lowercase letter
    if " " not in s or not re.search(r"[a-z]", s):
        return False
    text_chars = sum(ch.isalnum() or ch in " .,!?';:()-/\"\n\t[]%+*=<>#&@_" for ch in s)
    return text_chars / len(s) > 0.95 and re.search(r"[A-Za-z]{2}", s)


def main():
    refs = rip_refs()
    pairs = list(csv.reader(open("data/pairs.tsv", encoding="utf-8"), delimiter="\t"))[1:]

    entries = {}   # en text -> dict
    pair_offsets = {}

    def add(s, off, source, uk=""):
        e = entries.setdefault(s, dict(en=s, offs=[], refs=0, sources=set(), uk=uk))
        if off not in e["offs"]:
            e["offs"].append(off)
            e["refs"] += len(refs.get(pe.off_to_rva(off), []))
        e["sources"].add(source)
        if uk and not e["uk"]:
            e["uk"] = uk

    for row in pairs:
        call, enoff, en, ukoff, uk = int(row[0]), int(row[1]), row[2], int(row[3]), row[4]
        pair_offsets[enoff] = True
        if en == "@locale@":
            continue
        add(en, enoff, "pair", uk)

    strings = null_strings(rstart, rend)
    print("strings:", len(strings))
    for off, s in strings:
        if off in pair_offsets:
            continue
        rva = pe.off_to_rva(off)
        n = len(refs.get(rva, []))
        if n == 0:
            continue
        if not prose(s):
            continue
        add(s, off, "literal")

    # second pass: any pair entry whose text was filtered out of null_strings (rare encodings)
    missing = [o for o in pair_offsets if not any(o in e["offs"] for e in entries.values())]
    print("pair offsets missing:", len(missing))

    out = sorted(entries.values(), key=lambda e: min(e["offs"]))
    with open("data/strings.tsv", "w", encoding="utf-8", newline="") as f:
        f.write("id\ten\tuk\trefs\tn_offs\tsources\n")
        for i, e in enumerate(out):
            en = e["en"].replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
            uk = (e["uk"] or "").replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
            f.write(f"{i}\t{en}\t{uk}\t{e['refs']}\t{len(e['offs'])}\t{','.join(sorted(e['sources']))}\n")
    with open("data/strings.json", "w", encoding="utf-8") as f:
        json.dump([dict(id=i, en=e["en"], uk=e["uk"], offs=e["offs"], refs=e["refs"],
                        sources=sorted(e["sources"])) for i, e in enumerate(out)],
                  f, ensure_ascii=False, indent=1)

    print("unique translatable:", len(out))
    print("chars:", sum(len(e["en"]) for e in out))
    print("sources:", Counter(s for e in out for s in e["sources"]))
    print("no refs:", sum(1 for e in out if e["refs"] == 0))
    print("with newline:", sum(1 for e in out if "\n" in e["en"]))
    print("with %s/%i:", sum(1 for e in out if re.search(r"%[sdifu]", e["en"])))
    print("with [img:", sum(1 for e in out if "[img" in e["en"]))
    print("with [b]:", sum(1 for e in out if "[b]" in e["en"]))


if __name__ == "__main__":
    main()
