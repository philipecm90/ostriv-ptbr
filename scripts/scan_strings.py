"""Extract candidate localization strings from ostriv.exe and dump a window for inspection."""
import sys
import struct
from pe import PE

EXE = r"backup/ostriv_original.exe"

data = open(EXE, "rb").read()
pe = PE(data)
rdata = next(s for s in pe.sections if s["name"] == ".rdata")
print("rdata", rdata)

start = rdata["rawptr"]
end = start + rdata["rawsize"]

def is_utf8_start(b, i):
    c = b[i]
    if c < 0x80:
        return 32 <= c <= 126
    if 0xC2 <= c <= 0xDF:
        return True
    if 0xE0 <= c <= 0xEF:
        return True
    if 0xF0 <= c <= 0xF4:
        return True
    return False

def utf8_len(b, i):
    c = b[i]
    if c < 0x80:
        return 1
    if 0xC2 <= c <= 0xDF:
        return 2
    if 0xE0 <= c <= 0xEF:
        return 3
    if 0xF0 <= c <= 0xF4:
        return 4
    return 0

strings = []
i = start
while i < end:
    if is_utf8_start(data, i):
        j = i
        ok = True
        while j < end and data[j] != 0:
            n = utf8_len(data, j)
            if n == 0:
                ok = False
                break
            try:
                data[j:j + n].decode("utf-8")
            except UnicodeDecodeError:
                ok = False
                break
            j += n
        if ok and j > i and 2 <= (j - i) <= 4000:
            s = data[i:j].decode("utf-8")
            # require mostly text-like chars
            if all(ch.isprintable() or ch in "\r\n\t" for ch in s):
                strings.append((i, j - i, s))
            i = j
    i += 1

print("utf8 strings in .rdata:", len(strings))
total = sum(s[1] for s in strings)
print("total bytes:", total)

lo, hi = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else None
out = [s for s in strings if s[0] >= lo and (hi is None or s[0] < hi)]
with open("data/window.txt", "w", encoding="utf-8") as f:
    for off, ln, s in out:
        f.write(f"{off}\t{ln}\t{s}\n")
print("window strings:", len(out), "-> data/window.txt")

# summary of string count per 64KB bucket
from collections import Counter
c = Counter((s[0] // 65536) * 65536 for s in strings)
for k in sorted(c):
    print(f"  {k:>9} : {c[k]}")
