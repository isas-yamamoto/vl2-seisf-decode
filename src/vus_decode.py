"""
VUS / USEIS science decoder.

Port of materials2/vl2_seisf/vusinfo (Yukio Yamamoto).
Validated against `./vusinfo -f utig/vkg.47` frame/GCSC/mode lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from vkg_format import (
    BYTES_PER_FRAME_VUS,
    MODE_EVENT,
    MODE_HIGH,
    MODE_NAMES,
    MODE_NORMAL,
    MODE_NORMAL2,
    WORDS_PER_FRAME,
)

BITS_PER_WORD = 36
BITS_PER_FRAME = BITS_PER_WORD * WORDS_PER_FRAME
SIZE_COMMAND_STATUS = 22
SIZE_CHANGE_CODE_BITS = 15
SIZE_SOURCE_CODE_BITS = 5
SIZE_AMPLITUDE = 8
SIZE_AXIS_CROSSING = 5

CHANGE_CODE = [0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1]


def get_vus_data(frame: bytes, word: int, start: int, end: int) -> int:
    """word is 1-based; bits 0..35 of that 36-bit word."""
    p = (word - 1) * 6
    ret = 0
    for i in range(start, end + 1):
        bo = i // 6
        bi = i % 6
        ret = (ret << 1) | ((frame[p + bo] >> (5 - bi)) & 1)
    return ret


def bcd2int(bcd: int) -> int:
    ret = 0
    times = 1
    while bcd > 0:
        ret += (bcd % 16) * times
        bcd //= 16
        times *= 10
    return ret


def make_bit_stream(frame: bytes) -> list[int]:
    bits = [0] * BITS_PER_FRAME
    for word in range(1, WORDS_PER_FRAME + 1):
        for i in range(BITS_PER_WORD):
            bit_offset = (word - 1) * BITS_PER_WORD + (
                (17 - i) if i < 18 else (35 - i + 18)
            )
            bits[bit_offset] = get_vus_data(frame, word, i, i)
    return bits


def get_int_from_bit_stream(
    bits: list[int], offset: int, length: int, signed: bool = False
) -> int:
    """Read `length` bits starting at `offset` (LSB of field at offset+length-1).

    Returns 0 if the field would extend past the end of `bits`.
    """
    if length <= 0 or offset < 0 or offset + length > len(bits):
        return 0
    ret = 0
    for i in range(length):
        ret = (ret << 1) | (bits[offset + length - 1 - i] & 1)
    if signed and bits[offset + length - 1]:
        ret -= 1 << length
    return ret


def search_change_code(bits: list[int]) -> list[int]:
    found: list[int] = []
    limit = BITS_PER_FRAME - SIZE_CHANGE_CODE_BITS - SIZE_SOURCE_CODE_BITS
    for i in range(19 * BITS_PER_WORD, limit):
        if all(bits[i + j] == CHANGE_CODE[j] for j in range(SIZE_CHANGE_CODE_BITS)):
            found.append(i)
    return found


@dataclass
class CommandStatus:
    mode: int
    hatten: int
    vatten: int
    tlevel: int
    fmode: int
    filt: int
    ztrig: int
    ytrig: int
    xtrig: int
    cal: int

    @property
    def mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, f"MODE{self.mode}")


def extract_command_status(cmd: int) -> CommandStatus:
    # Keep bit field masks identical to vus_utils.c
    return CommandStatus(
        mode=cmd & 0x03,
        hatten=(cmd >> 2) & 0x07,
        vatten=(cmd >> 5) & 0x07,
        tlevel=(cmd >> 8) & 0x07,
        fmode=(cmd >> 11) & 0x01,
        filt=(cmd >> 12) & 0x02,
        ztrig=(cmd >> 14) & 0x01,
        ytrig=(cmd >> 15) & 0x01,
        xtrig=(cmd >> 16) & 0x01,
        cal=(cmd >> 17) & 0x03,
    )


@dataclass
class ScienceBlock:
    gcsc: int
    cmd_status: int
    cs: CommandStatus
    change_code: int
    amp: List[List[int]] = field(default_factory=lambda: [[], [], []])
    axis: List[List[int]] = field(default_factory=lambda: [[], [], []])

    @property
    def ndata(self) -> int:
        return len(self.amp[0])


@dataclass
class DecodedFrame:
    frame_index: int
    year: int
    doy: int
    blocks: List[ScienceBlock]
    raw: bytes
    note: str = ""


def is_all_one_frame(frame: bytes) -> bool:
    return len(frame) >= BYTES_PER_FRAME_VUS and all(b == 0x09 for b in frame[:BYTES_PER_FRAME_VUS])


def parse_seisf_header_fields(frame: bytes) -> tuple[int, int]:
    """Year / DOY from SEISF/VUS frame header (BCD)."""
    doy = bcd2int(get_vus_data(frame, 3, 24, 35))
    year = 1900 + bcd2int(get_vus_data(frame, 5, 12, 19))
    return year, doy


def extract_data_from_bit_stream(bits: list[int]) -> list[ScienceBlock]:
    nbits = len(bits)
    starts = [18 * BITS_PER_WORD]
    limits: list[int] = []
    found = search_change_code(bits)
    for off in found:
        starts.append(off + SIZE_CHANGE_CODE_BITS + SIZE_SOURCE_CODE_BITS)
        limits.append(off - 3 * SIZE_AMPLITUDE)
    starts.append(WORDS_PER_FRAME * BITS_PER_WORD)
    limits.append(WORDS_PER_FRAME * BITS_PER_WORD - 3 * SIZE_AMPLITUDE)

    results: list[ScienceBlock] = []
    for gi in range(len(starts) - 1):
        offset = starts[gi]
        limit = min(limits[gi], nbits)
        if offset < 0 or offset >= nbits:
            continue
        # Prefix: GCSC + command (+ change code on first block)
        if gi == 0:
            if offset + 23 + SIZE_COMMAND_STATUS + 8 > nbits:
                continue
            gcsc = get_int_from_bit_stream(bits, offset, 23) << 1
            offset += 23
        else:
            if offset + 24 + SIZE_COMMAND_STATUS > nbits:
                continue
            gcsc = get_int_from_bit_stream(bits, offset, 24)
            offset += 24
        cmd = get_int_from_bit_stream(bits, offset, SIZE_COMMAND_STATUS)
        offset += SIZE_COMMAND_STATUS
        cs = extract_command_status(cmd)
        if gi == 0:
            chg = get_int_from_bit_stream(bits, offset, 8)
            offset += 8
        else:
            chg = 0
        sample_bits = 3 * (
            SIZE_AMPLITUDE
            + (SIZE_AXIS_CROSSING if cs.mode == MODE_EVENT else 0)
        )
        amps: list[list[int]] = [[], [], []]
        axes: list[list[int]] = [[], [], []]
        # Match vusinfo: continue while offset < limit (may use bits past limit
        # up to a full sample). Stop only on end-of-stream, not limit-24.
        while offset < limit:
            if offset + sample_bits > nbits:
                break
            for ch in range(3):
                amps[ch].append(
                    get_int_from_bit_stream(bits, offset, SIZE_AMPLITUDE, True)
                )
                offset += SIZE_AMPLITUDE
                if cs.mode == MODE_EVENT:
                    axes[ch].append(
                        get_int_from_bit_stream(bits, offset, SIZE_AXIS_CROSSING)
                    )
                    offset += SIZE_AXIS_CROSSING
        results.append(
            ScienceBlock(
                gcsc=gcsc,
                cmd_status=cmd,
                cs=cs,
                change_code=chg,
                amp=amps,
                axis=axes,
            )
        )
    return results


def decode_vus_frame(frame: bytes, frame_index: int = 0) -> Optional[DecodedFrame]:
    if len(frame) < BYTES_PER_FRAME_VUS:
        return None
    frame = frame[:BYTES_PER_FRAME_VUS]
    if is_all_one_frame(frame) or frame[:20] == b"\x00" * 20:
        return None
    year, doy = parse_seisf_header_fields(frame)
    bits = make_bit_stream(frame)
    try:
        blocks = extract_data_from_bit_stream(bits)
    except Exception:
        # Corrupted science (false change-code, short tail, etc.): header only
        blocks = []
    return DecodedFrame(frame_index, year, doy, blocks, frame)


def iter_vus_frames(record_body: bytes, record_length: int) -> Iterator[tuple[int, bytes]]:
    """record_body is one physical VUS data record, length 11250 typically."""
    nframes = record_length // BYTES_PER_FRAME_VUS
    for i in range(nframes):
        yield i, record_body[i * BYTES_PER_FRAME_VUS : (i + 1) * BYTES_PER_FRAME_VUS]


def decode_vus_file(path: str) -> Iterator[DecodedFrame]:
    from vkg_format import open_vkg, BYTES_PER_FRAME_VUS as BPF

    _, subgroups = open_vkg(path)
    fi = 0
    for hdr, body in subgroups:
        if not hdr.is_vus:
            raise ValueError(
                f"{path}: expected VUS tape (vkg.47-56), label={hdr.label!r}"
            )
        pos = 0
        rlen = hdr.record_length
        while pos + rlen <= len(body):
            rec = body[pos : pos + rlen]
            pos += rlen
            for _, fr in iter_vus_frames(rec, rlen):
                dec = decode_vus_frame(fr, fi)
                if dec is not None:
                    yield dec
                fi += 1
