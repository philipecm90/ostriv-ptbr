"""Merge all English translatable strings (UTF-8 pairs, UTF-8 literals, UTF-16 literals)
into a single translation catalog with locations and reference counts."""
import csv
import json
import re
from collections import defaultdict

# reuse the prose filter from build_inventory
from build_inventory import prose

# ---------------------------------------------------------------- pair + utf8
pair_rows = list(csv.reader(open("data/pairs.tsv", encoding="utf-8"), delimiter="\t"))[1:]
utf8_rows = list(csv.reader(open("data/strings.tsv", encoding="utf-8"), delimiter="\t"))[1:]

utf16 = json.load(open("data/utf16_en.json", encoding="utf-8"))

catalog = {}


def add(text, off, enc, source, refs, uk=""):
    e = catalog.setdefault(text, dict(en=text, uk=uk, locs=[], encs=set(), sources=set(), refs=0))
    e["locs"].append([off, enc])
    e["encs"].add(enc)
    e["sources"].add(source)
    e["refs"] += refs
    if uk and not e["uk"]:
        e["uk"] = uk


# pairs (english side, UTF-8)
for row in pair_rows:
    call, enoff, en, ukoff, uk = int(row[0]), int(row[1]), row[2], int(row[3]), row[4]
    if en == "@locale@":
        continue
    add(en, enoff, "utf8", "ui-pair", 1, uk)

# utf8 literals (skip those already added by offset)
pair_offs = {int(r[1]) for r in pair_rows}
for row in utf8_rows:
    sid, en, uk, refs, noffs, sources = row
    offs = [o for o in json.load(open("data/strings.json", encoding="utf-8"))[int(sid)]["offs"]]
    for off in offs:
        if off in pair_offs:
            continue
        add(en.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\"),
            off, "utf8", "literal", 1)

# utf16 literals
skipped16 = 0
for r in utf16:
    s = r["en"]
    if not prose(s):
        skipped16 += 1
        continue
    add(s, r["offs"][0], "utf16", "literal16", r["refs"])

print("utf16 skipped by prose filter:", skipped16)
print("catalog size:", len(catalog))
print("chars:", sum(len(e["en"]) for e in catalog.values()))
print("bytes for utf16:", sum(2 * (len(e["en"]) + 1) for e in catalog.values() if "utf16" in e["encs"]))
from collections import Counter
print("sources:", Counter(s for e in catalog.values() for s in e["sources"]))
print("no refs:", sum(1 for e in catalog.values() if e["refs"] == 0))

# report strings translated in multiple encodings
multi = [e for e in catalog.values() if len(e["encs"]) > 1]
print("multi-encoding:", len(multi), "chars:", sum(len(e["en"]) for e in multi))

out = sorted(catalog.values(), key=lambda e: min(o for o, _ in e["locs"]))
with open("data/catalog.json", "w", encoding="utf-8") as f:
    json.dump([dict(id=i, en=e["en"], uk=e["uk"], locs=e["locs"], encs=sorted(e["encs"]),
                    sources=sorted(e["sources"]), refs=e["refs"]) for i, e in enumerate(out)],
              f, ensure_ascii=False, indent=1)
print("wrote data/catalog.json")

# quick top-30 longest
for e in sorted(out, key=lambda e: -len(e["en"]))[:5]:
    print("---", len(e["en"]), e["sources"], e["encs"])
    print(e["en"][:200].replace("\n", "\\n"))
