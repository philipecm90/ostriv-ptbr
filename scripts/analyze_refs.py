"""Per-string safety analysis for every patch target (English, Ukrainian and help strings)."""
import json
from collections import defaultdict
from pe import PE
import capstone

EXE = r"backup\ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
text = next(s for s in pe.sections if s["name"] == ".text")
rdata = next(s for s in pe.sections if s["name"] == ".rdata")
tstart, tend = text["rawptr"], text["rawptr"] + text["rawsize"]
rstart, rend = rdata["rawptr"], rdata["rawptr"] + rdata["rawsize"]
BASE = pe.image_base
MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
MD.detail = True


def read_str(off, enc):
    if enc == "utf8":
        j = data.find(b"\0", off)
        return data[off:j].decode("utf-8", "replace")
    j = off
    while data[j:j + 2] != b"\0\0":
        j += 2
    return data[off:j].decode("utf-16-le", "replace")


all_refs = defaultdict(list)
for insn in MD.disasm(data[tstart:tend], BASE + text["va"]):
    for op in insn.operands:
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
            tgt = ((insn.address + insn.size + op.mem.disp) & 0xFFFFFFFFFFFFFFFF) - BASE
            all_refs[tgt].append((pe.rva_to_off(insn.address - BASE), insn.mnemonic, insn.size))
print("ref targets:", len(all_refs))

locs = []
for name in ("data/catalog.json", "data/catalog_uk.json"):
    try:
        cat = json.load(open(name, encoding="utf-8"))
    except FileNotFoundError:
        continue
    for e in cat:
        for off, enc in e["locs"]:
            locs.append((e["id"], off, enc))
try:
    for t in json.load(open("data/help_targets.json", encoding="utf-8")):
        locs.append((-1, t["uk"], "utf16"))
except FileNotFoundError:
    pass
try:
    for t in json.load(open("data/help_buildings.json", encoding="utf-8")):
        locs.append((-1, t["uk"], "utf16"))
except FileNotFoundError:
    pass

seen = set()
locs = [x for x in locs if not ((x[1], x[2]) in seen or seen.add((x[1], x[2])))]
print("locations:", len(locs))

starts = set()
for i in range(rstart + 1, rend):
    if data[i - 1] == 0 and (32 <= data[i] < 127 or data[i] >= 0xC2):
        starts.add(i)
for i in range(rstart, rend - 1, 2):
    if i == rstart or (data[i - 2] == 0 and data[i - 1] == 0):
        if 32 <= data[i] < 127 and data[i + 1] == 0:
            starts.add(i)
for _, off, _ in locs:
    starts.add(off)

report = []
problems = 0
for eid, off, enc in locs:
    orig = read_str(off, enc)
    slen = len(orig.encode("utf-8")) if enc == "utf8" else len(orig.encode("utf-16-le"))
    rva = pe.off_to_rva(off)
    refs = all_refs.get(rva, [])
    lea = [r for r in refs if r[1] == "lea"]
    nonlea = [r for r in refs if r[1] != "lea"]

    mids = []
    for k in range(1, slen):
        if rva + k in all_refs:
            mids.append((k, all_refs[rva + k]))
    mid_lea = sum(1 for _, rs in mids for r in rs if r[1] == "lea")
    if mids:
        problems += 1

    nxt = None
    step = 1 if enc == "utf8" else 2
    for cand in range(off + step, rend):
        if cand in starts and (enc == "utf8" or (cand - off) % 2 == 0):
            nxt = cand
            break
    avail = (nxt - off - (1 if enc == "utf8" else 2)) if nxt else 0

    report.append(dict(id=eid, off=off, enc=enc, orig=orig,
                       bytes=slen, avail=avail, lea=len(lea), nonlea=len(nonlea),
                       mid=len(mids), mid_lea=mid_lea,
                       mnem=sorted(set(r[1] for r in refs))))

with open("data/analysis.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

print("locations:", len(report))
print("with mid refs:", problems)
print("no refs at all:", sum(1 for r in report if r["lea"] + r["nonlea"] == 0))
print("with non-lea refs:", sum(1 for r in report if r["nonlea"] > 0))
print("with only non-lea:", sum(1 for r in report if r["nonlea"] > 0 and r["lea"] == 0))
avails = sorted(r["avail"] - r["bytes"] for r in report)
import statistics
print("slack bytes: min", avails[0], "median", statistics.median(avails), "max", avails[-1])
