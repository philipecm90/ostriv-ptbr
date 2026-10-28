"""Minimal PE parsing helpers for ostriv.exe analysis/patching."""
import struct


class PE:
    def __init__(self, data: bytes):
        self.data = bytearray(data)
        self.pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        assert data[self.pe_off:self.pe_off + 4] == b"PE\0\0"
        self.num_sections = struct.unpack_from("<H", data, self.pe_off + 6)[0]
        self.opt_size = struct.unpack_from("<H", data, self.pe_off + 20)[0]
        self.opt_off = self.pe_off + 24
        magic = struct.unpack_from("<H", data, self.opt_off)[0]
        assert magic == 0x20B, hex(magic)
        self.image_base = struct.unpack_from("<Q", data, self.opt_off + 24)[0]
        self.section_alignment = struct.unpack_from("<I", data, self.opt_off + 32)[0]
        self.file_alignment = struct.unpack_from("<I", data, self.opt_off + 36)[0]
        self.size_of_image = struct.unpack_from("<I", data, self.opt_off + 56)[0]
        self.size_of_headers = struct.unpack_from("<I", data, self.opt_off + 60)[0]
        self.num_dirs = struct.unpack_from("<I", data, self.opt_off + 108)[0]
        self.dirs = []
        for i in range(self.num_dirs):
            rva, size = struct.unpack_from("<II", data, self.opt_off + 112 + i * 8)
            self.dirs.append((rva, size))
        self.sections = []
        sec_off = self.opt_off + self.opt_size
        for i in range(self.num_sections):
            o = sec_off + i * 40
            name = data[o:o + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
            chars = struct.unpack_from("<I", data, o + 36)[0]
            self.sections.append(dict(name=name, vsize=vsize, va=va, rawsize=rawsize,
                                      rawptr=rawptr, chars=chars, hdr_off=o))

    def off_to_rva(self, off: int):
        for s in self.sections:
            if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
                return s["va"] + (off - s["rawptr"])
        return None

    def rva_to_off(self, rva: int):
        for s in self.sections:
            if s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"]):
                if rva - s["va"] < s["rawsize"]:
                    return s["rawptr"] + (rva - s["va"])
        return None

    def va_to_off(self, va: int):
        return self.rva_to_off(va - self.image_base)

    def section_of_rva(self, rva: int):
        for s in self.sections:
            if s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"]):
                return s
        return None
