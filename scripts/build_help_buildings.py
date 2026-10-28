"""Map Ukrainian building-help copies to their English counterparts and Portuguese translations."""
import json
import struct
from pe import PE

EXE = r"backup\ostriv_original.exe"
data = open(EXE, "rb").read()
pe = PE(data)
BASE = pe.image_base

CTORS = {0x1404116E0, 0x140410530, 0x1404104B0}


def read_str(off):
    j = off
    chars = []
    while j + 1 < len(data):
        u = data[j] | (data[j + 1] << 8)
        if u == 0:
            break
        if not (u >= 32 and (u < 0x500 or 0x2000 <= u <= 0x206F or u == 0x20AC)) and u not in (9,10,13):
            return None
        chars.append(chr(u))
        j += 2
    s = "".join(chars)
    if len(s) >= 2 and any(ch.isalpha() for ch in s):
        return s
    return None


def lang_of(s):
    cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
    lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
    return "UK" if cyr > lat else "EN"


seq = []
lo, hi = 0x200000, 0x220000
for i in range(lo, hi - 5):
    if data[i] == 0xE8:
        rel = struct.unpack_from("<i", data, i + 1)[0]
        rva = pe.off_to_rva(i)
        target = BASE + rva + 5 + rel
        if target in CTORS:
            for k in range(i - 1, max(lo, i - 20), -1):
                if data[k] in (0x48, 0x4C) and data[k + 1] == 0x8D and (data[k + 2] & 0xC7) == 0x05:
                    insn_rva = pe.off_to_rva(k)
                    disp = struct.unpack_from("<i", data, k + 3)[0]
                    tgt = (insn_rva + 7 + disp) & 0xFFFFFFFFFFFFFFFF
                    off = pe.rva_to_off(tgt)
                    s = read_str(off) if off is not None else None
                    if s:
                        seq.append((i, off, s, lang_of(s)))
                    break

print("sequence:", len(seq))
pairs = []
for a, b in zip(seq, seq[1:]):
    if a[3] == "EN" and b[3] == "UK":
        pairs.append((a[1], a[2], b[1], b[2]))

print("en->uk pairs:", len(pairs))

cat = json.load(open("data/catalog.json", encoding="utf-8"))
pt = {int(k): v for k, v in json.load(open("data/pt_br.json", encoding="utf-8")).items()}
pt_by_en = {e["en"]: pt[e["id"]] for e in cat if e["id"] in pt}

targets = []
missing = []
manual = {int(k): v for k, v in json.load(open("data/help_manual_buildings.json", encoding="utf-8")).items()}
for enoff, en, ukoff, uk in pairs:
    text = manual.get(enoff) or pt_by_en.get(en)
    if not text:
        missing.append((enoff, en[:70]))
        continue
    targets.append(dict(uk=ukoff, en=en, pt=text))

print("targets:", len(targets), "missing:", len(missing))
for m in missing[:20]:
    print("  missing:", m)

json.dump(targets, open("data/help_buildings.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote data/help_buildings.json")
