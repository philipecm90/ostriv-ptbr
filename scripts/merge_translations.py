"""Merge translation batches, validate placeholders/markup, and report coverage."""
import glob
import json
import re
import sys

cat = json.load(open("data/catalog.json", encoding="utf-8"))
by_id = {e["id"]: e for e in cat}

SKIP = set()
SKIP |= {0, 103, 104, 105, 122, 123, 125, 127, 128, 140, 141, 236, 362, 1225, 2251, 2254}
SKIP |= set(range(1085, 1090))
SKIP |= set(range(1159, 1178))
SKIP |= set(range(2061, 2109))          # town names stay as-is
SKIP |= set(range(2260, 2284))          # build info / debug log
SKIP |= set(range(2284, 2365))          # FMOD library error strings
SKIP |= set(range(2365, 2383))          # keyboard key names
SKIP |= set(range(2383, 2387))          # debug
SKIP |= {2409, 2410, 2411}

pt = {}
for path in sorted(glob.glob("data/translations/b*.json")):
    data = json.load(open(path, encoding="utf-8"))
    for k, v in data.items():
        i = int(k)
        if i in pt:
            print(f"duplicate id {i} in {path}")
        pt[i] = v
    print(f"{path}: {len(data)}")

missing = [i for i in by_id if i not in pt and i not in SKIP]
extra = [i for i in pt if i not in by_id]
print(f"\ntranslated: {len(pt)}  catalog: {len(by_id)}  missing: {len(missing)}  extra: {len(extra)}")

overrides = {int(k): v for k, v in json.load(open("data/overrides.json", encoding="utf-8")).items()}
for i, v in overrides.items():
    if i in pt:
        pt[i] = v
print(f"overrides applied: {len(overrides)}")
if missing:
    for i in missing[:20]:
        print("  MISSING", i, repr(by_id[i]["en"][:90]))
if extra:
    print("  EXTRA", extra[:20])

FMT = re.compile(r"%(?:%|[-+ #0]*[\d.]*(?:hh|h|ll|l|z|j|t|L)?[diouxXeEfFgGaAcspn])")
BRACKET = re.compile(r"\[[^\]\n]*\]")


def check(i):
    en, p = by_id[i]["en"], pt[i]
    errs = []
    if sorted(FMT.findall(en)) != sorted(FMT.findall(p)):
        errs.append(("fmt", FMT.findall(en), FMT.findall(p)))
    eb = [t for t in BRACKET.findall(en)]
    pb = [t for t in BRACKET.findall(p)]
    if sorted(eb) != sorted(pb):
        errs.append(("brackets", eb, pb))
    m = re.match(r"^([a-z_]+@)", en)
    if m and not p.startswith(m.group(1)):
        errs.append(("prefix", m.group(1), p[:20]))
    if en[:1] == " " and p[:1] != " ":
        errs.append(("leadspace", en[:10], p[:10]))
    if en[-1:] == " " and p[-1:] != " ":
        errs.append(("trailspace", en[-10:], p[-10:]))
    if en.count("\n") != p.count("\n"):
        errs.append(("newlines", en.count("\n"), p.count("\n")))
    return errs


problems = []
for i in pt:
    if i in by_id:
        errs = check(i)
        if errs:
            problems.append((i, by_id[i]["en"], pt[i], errs))

print(f"\nvalidation problems: {len(problems)}")
for i, en, p, errs in problems:
    print(f"\n--- id {i}: {errs}")
    print("EN:", repr(en[:160]))
    print("PT:", repr(p[:160]))

json.dump({str(k): v for k, v in pt.items()}, open("data/pt_br.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote data/pt_br.json")

# encoding/fit estimate
analysis = {r["off"]: r for r in json.load(open("data/analysis.json", encoding="utf-8"))}
fit = nofit = 0
for i, p in pt.items():
    e = by_id.get(i)
    if not e:
        continue
    for off, enc in e["locs"]:
        a = analysis[off]
        n = len(p.encode("utf-8")) if enc == "utf8" else len(p.encode("utf-16-le"))
        if n <= a["avail"] and a["mid_lea"] == 0:
            fit += 1
        else:
            nofit += 1
print(f"locations that can be in-place: {fit}, need relocation: {nofit}")
