"""Build a patch catalog that targets the UTF-16 slots plus ASCII-safe UTF-8 literals.

- pair entries: patch the Ukrainian (UTF-16) literal, leaving the English slot intact
- literal16 entries: patch the UTF-16 literal directly
- standalone utf8 literals: patch with folded (ASCII) Portuguese
"""
import csv
import json
import unicodedata
from collections import defaultdict

cat = json.load(open("data/catalog.json", encoding="utf-8"))
pairs = list(csv.reader(open("data/pairs.tsv", encoding="utf-8"), delimiter="\t"))[1:]

uk_by_text = defaultdict(list)
pair_en_offsets = set()
for row in pairs:
    enoff, en, ukoff = int(row[1]), row[2], int(row[3])
    pair_en_offsets.add(enoff)
    if ukoff not in uk_by_text[en]:
        uk_by_text[en].append(ukoff)

print("pair texts:", len(uk_by_text), "pair en offsets:", len(pair_en_offsets))

out = []
for e in cat:
    locs = []
    for ukoff in uk_by_text.get(e["en"], []):
        locs.append([ukoff, "utf16"])
    for off, enc in e["locs"]:
        if enc == "utf16":
            if off not in [x[0] for x in locs]:
                locs.append([off, "utf16"])
        else:
            if off not in pair_en_offsets:
                locs.append([off, "utf8"])
    if locs:
        out.append(dict(id=e["id"], en=e["en"], locs=locs))

# the language name is not part of the catalog
out.append(dict(id=9999, en="@locale@", locs=[[5633456, "utf16"]]))

json.dump(out, open("data/catalog_uk.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("catalog_uk entries:", len(out), "locations:", sum(len(e["locs"]) for e in out))
from collections import Counter
c = Counter(enc for e in out for _, enc in e["locs"])
print(c)

# report entries that only have a utf8 location (these get ASCII-folded)
only8 = [e for e in out if all(enc == "utf8" for _, enc in e["locs"])]
print("utf8-only entries:", len(only8), "chars:", sum(len(e["en"]) for e in only8))
