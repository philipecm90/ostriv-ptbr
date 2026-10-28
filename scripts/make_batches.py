"""Split the catalog into translation batches (~6000 chars of English each).

Each batch is written as data/batches/bNN.txt with lines:
    id <TAB> english <TAB> ukrainian-context
Newlines inside strings are escaped as \\n so every entry stays on one line.
"""
import json
import os

BATCH_CHARS = 6000
os.makedirs("data/batches", exist_ok=True)

cat = json.load(open("data/catalog.json", encoding="utf-8"))
cat.sort(key=lambda e: e["id"])

batches = []
cur = []
size = 0
for e in cat:
    if cur and size + len(e["en"]) > BATCH_CHARS:
        batches.append(cur)
        cur = []
        size = 0
    cur.append(e)
    size += len(e["en"])
if cur:
    batches.append(cur)

for i, b in enumerate(batches, 1):
    path = f"data/batches/b{i:02d}.txt"
    with open(path, "w", encoding="utf-8") as f:
        for e in b:
            en = e["en"].replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
            uk = (e["uk"] or "").replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
            f.write(f"{e['id']}\t{en}\t{uk}\n")
    print(path, len(b), sum(len(e["en"]) for e in b))

print("batches:", len(batches), "entries:", len(cat), "chars:", sum(len(e["en"]) for e in cat))
