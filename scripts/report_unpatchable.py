import json

cat = {e["id"]: e for e in json.load(open("data/catalog.json", encoding="utf-8"))}
pt = {int(k): v for k, v in json.load(open("data/pt_br.json", encoding="utf-8")).items()}
a = {r["off"]: r for r in json.load(open("data/analysis.json", encoding="utf-8"))}

rows = []
for i, e in cat.items():
    if i not in pt:
        continue
    p = pt[i]
    for off, enc in e["locs"]:
        r = a[off]
        n = len(p.encode("utf-8")) if enc == "utf8" else len(p.encode("utf-16-le"))
        if n > r["avail"] and r["mid_lea"] == 0 and not r["lea"]:
            rows.append((i, r["avail"], n, e["en"], p))

print("unpatchable:", len(rows))
for i, avail, need, en, p in rows:
    print()
    print(f"id {i}  avail={avail} need={need}")
    print("  EN:", en)
    print("  PT:", p)
