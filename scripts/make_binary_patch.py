"""Create a compact binary patch between the original and patched ostriv.exe.

The patch contains only the changed bytes plus the appended .ptbr section; it does
not contain the game's original code or text. Applying it to a legally owned
ostriv.exe produces ostriv_ptbr.exe.

Format (little-endian):
  magic       8s   b"OPTBR1\0\0"
  version     u32  1
  orig_size   u64
  patch_size  u64
  orig_sha1   20s
  patch_sha1  20s
  edit_count  u32
  edits       edit_count * (u64 offset, u32 length, bytes)
  tail_len    u32
  tail        tail_len bytes
"""
import hashlib
import struct
import sys

ORIG = r"backup\ostriv_original.exe"
PATCHED = r"ostriv_ptbr.exe"
OUT = r"dist\ostriv_0.5.9.58_ptbr.patch"


def sha1(b):
    return hashlib.sha1(b).digest()


def main():
    orig = open(ORIG, "rb").read()
    patched = open(PATCHED, "rb").read()
    if len(patched) < len(orig):
        raise SystemExit("patched smaller than original")

    # find differing runs in the common prefix, merging small gaps
    n = len(orig)
    diffs = [i for i in range(n) if orig[i] != patched[i]]
    print("differing bytes:", len(diffs))

    runs = []
    start = prev = diffs[0]
    for i in diffs[1:]:
        if i - prev <= 16:
            prev = i
        else:
            runs.append((start, prev + 1))
            start = prev = i
    runs.append((start, prev + 1))

    # extend each run by a small margin to keep alignment readable
    edits = []
    for a, b in runs:
        edits.append((a, b, patched[a:b]))
    print("edits:", len(edits), "bytes in edits:", sum(len(x[2]) for x in edits))

    tail = patched[n:]
    print("tail bytes:", len(tail))

    out = bytearray()
    out += b"OPTBR1\0\0"
    out += struct.pack("<I", 1)
    out += struct.pack("<Q", len(orig))
    out += struct.pack("<Q", len(patched))
    out += sha1(orig)
    out += sha1(patched)
    out += struct.pack("<I", len(edits))
    for a, b, data in edits:
        out += struct.pack("<QI", a, b - a)
        out += data
    out += struct.pack("<I", len(tail))
    out += tail

    open(OUT, "wb").write(out)
    print("wrote", OUT, len(out), "bytes")


if __name__ == "__main__":
    main()
