"""Find long Ukrainian strings that are not covered by the patch plan."""
import json

data = open(r"backup\ostriv_original.exe", "rb").read()
plan = json.load(open("data/patch_plan.json", encoding="utf-8"))
covered = {s["off"] for s in plan["standalones"]} | {r["lea"] for r in plan["relocs"]}

# all long UTF-16 Ukrainian strings in .rdata
strings = []
i = 0x4B9000
while i < 0x6A0000:
    if i % 2 == 0 and (i == 0x4B9000 or (data[i - 2] == 0 and data[i - 1] == 0)):
        j = i
        chars = []
        ok = True
        while j + 1 < len(data):
            u = data[j] | (data[j + 1] << 8)
            if u == 0:
                break
            if not (u >= 32 and (u < 0x500 or 0x2000 <= u <= 0x206F)) and u not in (9, 10, 13):
                ok = False
                break
            chars.append(chr(u))
            j += 2
        if ok and len(chars) >= 80:
            s = "".join(chars)
            cyr = sum(1 for ch in s if "\u0400" <= ch <= "\u04FF")
            lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
            if cyr > lat:
                strings.append((i, s))
            i = j + 2
            continue
    i += 2

print("long uk strings:", len(strings))
missing = [(off, s) for off, s in strings if off not in covered]
print("not covered:", len(missing))
for off, s in missing[:30]:
    print(f"{off:#07x} {len(s):5d} {s[:90]!r}")
