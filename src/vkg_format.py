"""
Viking Lander 2 UTIG cassette (vkg.*) common layout.

Reference (UTIG Tech Report No.118, VUSFormat.pdf, materials2/vl2_seisf):

  - Each original 7-track tape is one vkg.N file.
  - Multiple subgroups; each subgroup = 1000-byte header + fixed-length data records.
  - Tape id word  = 5
  - Bytes 3-8     = tape label (ASCII): "DLT..." = SEISF (vkg.1-46), "VUS..." = USEIS (vkg.47-56)
  - Bytes 9-10    = file number on original tape
  - Bytes 11-12   = length of each following data record
  - Data bytes hold original 6-bit units in the 6 LSBs (MSB 2 bits zero / pad).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Iterator, Optional

SIZE_RECORD_HEADER = 1000

# Science frame sizes (6-bit units already one-per-byte)
WORDS_PER_FRAME = 75  # 36-bit words
BYTES_PER_WORD = 6  # six 6-bit units
BYTES_PER_FRAME_VUS = WORDS_PER_FRAME * BYTES_PER_WORD  # 450

# SEISF physical frames after cassette restore (halfwords = 18-bit)
SEISF_HALFWORDS_PER_FRAME = 224  # 112 36-bit words; N51SUB CXR stride AAC 340(oct)=224
SEISF_BYTES_PER_FRAME = SEISF_HALFWORDS_PER_FRAME * 3  # 3 bytes per 18-bit halfword = 672
SEISF_HEADER_HALFWORDS = 36  # 18 36-bit words = 108 bytes of SEISF header (also VUS frame header)
SEISF_FIRST_FRAME_HALFWORDS_OFFSET = 170  # observed on DLT tapes restored to 8mm cassette

# Record lengths seen in UTIG archive
RECORD_LEN_SEISF_A = 10752
RECORD_LEN_SEISF_B = 10764
RECORD_LEN_VUS = 11250  # 25 * 450

MODE_NORMAL = 0
MODE_HIGH = 1
MODE_EVENT = 2
MODE_NORMAL2 = 3

MODE_NAMES = {
    MODE_NORMAL: "NORMAL",
    MODE_HIGH: "HIGH",
    MODE_EVENT: "EVENT",
    MODE_NORMAL2: "NORMAL",
}


@dataclass
class CassetteHeader:
    tape_id: int
    label: str
    file_no: int
    record_length: int
    file_offset: int = 0

    @property
    def is_seisf(self) -> bool:
        return self.label.startswith("DLT")

    @property
    def is_vus(self) -> bool:
        return self.label.startswith("VUS")


def parse_cassette_header(blob: bytes, file_offset: int = 0) -> Optional[CassetteHeader]:
    if len(blob) < 12:
        return None
    tape_id = (blob[0] << 8) | blob[1]
    if tape_id != 5:
        return None
    label = blob[2:8].decode("ascii", errors="replace")
    file_no = (blob[8] << 8) | blob[9]
    record_length = (blob[10] << 8) | blob[11]
    if record_length not in (
        RECORD_LEN_SEISF_A,
        RECORD_LEN_SEISF_B,
        RECORD_LEN_VUS,
    ):
        # still accept if label looks right
        if not (label.startswith("DLT") or label.startswith("VUS")):
            return None
    return CassetteHeader(tape_id, label, file_no, record_length, file_offset)


def is_subgroup_header(data: bytes, pos: int) -> bool:
    if pos + 8 > len(data):
        return False
    if data[pos] != 0x00 or data[pos + 1] != 0x05:
        return False
    tag = data[pos + 2 : pos + 5]
    return tag in (b"DLT", b"VUS")


def iter_subgroups(data: bytes) -> Iterator[tuple[CassetteHeader, bytes]]:
    """Yield (header, concatenated data body of that subgroup)."""
    pos = 0
    n = len(data)
    while pos + SIZE_RECORD_HEADER <= n:
        if not is_subgroup_header(data, pos):
            pos += 1
            continue
        hdr = parse_cassette_header(data[pos : pos + SIZE_RECORD_HEADER], pos)
        if hdr is None:
            pos += 1
            continue
        pos += SIZE_RECORD_HEADER
        chunks: list[bytes] = []
        while pos + hdr.record_length <= n:
            if is_subgroup_header(data, pos):
                break
            chunks.append(data[pos : pos + hdr.record_length])
            pos += hdr.record_length
        yield hdr, b"".join(chunks)


def frame_to_halfwords(frame_6bit_bytes: bytes) -> list[int]:
    """Pack every 6 bytes (6-bit units) into two 18-bit halfwords."""
    hs: list[int] = []
    for i in range(0, len(frame_6bit_bytes) - 5, 6):
        w = 0
        for j in range(6):
            w = (w << 6) | (frame_6bit_bytes[i + j] & 0x3F)
        hs.append((w >> 18) & 0o777777)
        hs.append(w & 0o777777)
    return hs


def halfwords_to_frame_bytes(halfwords: list[int]) -> bytes:
    """Inverse of frame_to_halfwords (must be even length)."""
    out = bytearray()
    for i in range(0, len(halfwords) - 1, 2):
        w = ((halfwords[i] & 0o777777) << 18) | (halfwords[i + 1] & 0o777777)
        for s in range(5, -1, -1):
            out.append((w >> (s * 6)) & 0x3F)
    return bytes(out)


def body_to_halfwords(body: bytes) -> list[int]:
    """SEISF record body as sequential 18-bit halfwords (3 bytes each)."""
    hs: list[int] = []
    for i in range(0, len(body) - 2, 3):
        hs.append(
            ((body[i] & 0x3F) << 12)
            | ((body[i + 1] & 0x3F) << 6)
            | (body[i + 2] & 0x3F)
        )
    return hs


def halfwords_to_body(halfwords: list[int]) -> bytes:
    out = bytearray()
    for h in halfwords:
        h &= 0o777777
        out.append((h >> 12) & 0x3F)
        out.append((h >> 6) & 0x3F)
        out.append(h & 0x3F)
    return bytes(out)


def open_vkg(path: str) -> tuple[bytes, list[tuple[CassetteHeader, bytes]]]:
    with open(path, "rb") as f:
        data = f.read()
    return data, list(iter_subgroups(data))


def read_exact(f: BinaryIO, n: int) -> bytes:
    b = f.read(n)
    if len(b) != n:
        raise EOFError(f"expected {n} bytes, got {len(b)}")
    return b
