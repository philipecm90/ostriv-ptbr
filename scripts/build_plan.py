"""Build the final patch plan.

- Non-conflicting Ukrainian pair strings: address-based targets (covers every
  reference, including the help index).
- Conflicting shared Ukrainian strings: per-LEA relocations so each context keeps
  its own translation.
- Ukrainian help titles/bodies: address-based targets.
- Standalone literals: address-based targets (UTF-8 ones are ASCII-folded later).
"""
import csv
import json
from collections import defaultdict

cat = json.load(open("data/catalog.json", encoding="utf-8"))
pt = {int(k): v for k, v in json.load(open("data/pt_br.json", encoding="utf-8")).items()}
pt_by_en = {e["en"]: pt[e["id"]] for e in cat if e["id"] in pt}

pairs = list(csv.reader(open("data/pairs.tsv", encoding="utf-8"), delimiter="\t"))[1:]
pair_en_offsets = set()
pair_uk_offsets = set()

by_uk = defaultdict(lambda: dict(texts=set(), rows=[]))
for row in pairs:
    call, enoff, en, ukoff, uk, enlea, uklea = row
    enoff, ukoff, enlea, uklea = int(enoff), int(ukoff), int(enlea), int(uklea)
    pair_en_offsets.add(enoff)
    pair_uk_offsets.add(ukoff)
    text = "Português (Brasil)" if en == "@locale@" else (pt_by_en.get(en) or en)
    by_uk[ukoff]["texts"].add(text)
    by_uk[ukoff]["rows"].append((en, uklea, text))

uk_targets = []
relocs = []
for ukoff, info in by_uk.items():
    if len(info["texts"]) == 1:
        uk_targets.append(dict(off=ukoff, enc="utf16", text=next(iter(info["texts"])), en="<pair>"))
    else:
        for en, uklea, text in info["rows"]:
            relocs.append(dict(en=en, lea=uklea, text=text, enc="utf16"))

print("pair uk targets (address):", len(uk_targets))
print("pair conflicts (per-lea):", len(relocs))

# Ukrainian help articles
help_targets = []
for t in json.load(open("data/help_targets.json", encoding="utf-8")):
    help_targets.append(dict(off=t["uk"], enc="utf16", text=t["pt"], en="<help>"))
for t in json.load(open("data/help_buildings.json", encoding="utf-8")):
    help_targets.append(dict(off=t["uk"], enc="utf16", text=t["pt"], en="<help-building>"))
print("help targets:", len(help_targets))

# Standalone literals (exclude pair locations)
standalones = []
for e in json.load(open("data/catalog_uk.json", encoding="utf-8")):
    text = pt.get(e["id"])
    if not text:
        continue
    for off, enc in e["locs"]:
        if off in pair_en_offsets or off in pair_uk_offsets:
            continue
        standalones.append(dict(id=e["id"], en=e["en"], off=off, enc=enc, text=text))
print("standalone literals:", len(standalones))

# Merge address-based targets, deduping by offset
seen = set()
merged = []
for s in uk_targets + help_targets + standalones:
    key = (s["off"], s["enc"])
    if key in seen:
        continue
    seen.add(key)
    merged.append(s)

print("total address-based targets:", len(merged))
json.dump(dict(relocs=relocs, standalones=merged), open("data/patch_plan.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote data/patch_plan.json")
