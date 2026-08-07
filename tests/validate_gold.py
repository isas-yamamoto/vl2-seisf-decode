#!/usr/bin/env python3
"""
Gold-frame diagnostics + hard assertions.

Run from repository root:
  python3 tests/validate_gold.py

Prints a comparison table. Exit code 1 on assertion failure.
Use tests/test_regression.py for the full fixed suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from seisf_decode import (  # noqa: E402
    _PAIR36_BIT_OFFSET,
    _halfwords_data_msb_stream,
    _halfwords_pair36_stream,
    estimate_q_from_matv,
    estimate_q18_from_matv,
    find_seisf_frame_bases,
    map_unscramble_data_bits,
    n51_unscramble_2048,
    pd7400072_unscramble,
    seisf_frame_to_vus_bytes,
)
from vkg_format import body_to_halfwords, open_vkg  # noqa: E402
from vus_decode import (  # noqa: E402
    decode_vus_frame,
    get_int_from_bit_stream,
    make_bit_stream,
)

GOLD_GCSC = 125078


def amp_bytes(bits, start: int = 53, n: int = 12) -> list[int]:
    return [get_int_from_bit_stream(bits, start + 8 * i, 8) for i in range(n)]


def main() -> int:
    seisf = ROOT / "utig" / "vkg.1"
    vus = ROOT / "utig" / "vkg.47"
    if not seisf.is_file() or not vus.is_file():
        print(f"missing data: {seisf} or {vus}", file=sys.stderr)
        return 1

    _, sgs = open_vkg(str(seisf))
    h, body = sgs[0]
    hs = body_to_halfwords(body[: h.record_length])
    fb = find_seisf_frame_bases(hs)[0]

    v_frame = open_vkg(str(vus))[1][0][1][:450]
    v_bits = make_bit_stream(v_frame)[648 : 648 + 2048]
    v_dec = decode_vus_frame(v_frame, 0)
    assert v_dec and v_dec.blocks
    v_gold = v_dec.blocks[0]
    v_ser = []
    for i in range(4):
        for ch in range(3):
            a = v_gold.amp[ch][i]
            v_ser.append(a & 0xFF if a >= 0 else (a + 256) & 0xFF)

    print(f"SEISF frame_base={fb}  VUS GCSC={v_gold.gcsc} mode={v_gold.cs.mode_name}")
    print(f"V serial amps[:12]={v_ser}")

    q0, matv = estimate_q_from_matv(hs, fb)
    q18, _ = estimate_q18_from_matv(hs, fb)
    print(f"matv={matv} Q={q0} (production uses Q=matv, off={_PAIR36_BIT_OFFSET})  q18={q18}")

    paths: dict[str, list[int]] = {}
    paths["map_unscramble (auto)"] = map_unscramble_data_bits(hs, fb)

    s18 = _halfwords_data_msb_stream(hs, fb)
    b = pd7400072_unscramble(s18, q18)
    b[0] ^= 1
    paths[f"18bit Q{q18} flip0"] = b

    s32 = _halfwords_pair36_stream(hs, fb, bit_offset=_PAIR36_BIT_OFFSET)
    paths[f"pair36 drop4 off{_PAIR36_BIT_OFFSET} Q{q0}"] = pd7400072_unscramble(
        s32, q0
    )

    s_old = _halfwords_pair36_stream(hs, fb, bit_offset=13)
    paths[f"pair36 drop4 off13 Q{matv - 2} (legacy)"] = pd7400072_unscramble(
        s_old, matv - 2
    )

    try:
        bout = n51_unscramble_2048(hs, fb)
        bout2 = list(bout)
        bout2[0] ^= 1
        paths["n51 BOUT"] = bout
        paths["n51 BOUT flip0"] = bout2
    except Exception as e:
        print(f"BOUT failed: {e}")

    print()
    print(f"{'path':40s} {'GCSC':>8s} {'bit@':>6s} {'amp#':>5s}  amps[:6]")
    for name, bits in paths.items():
        g = get_int_from_bit_stream(bits, 0, 23) << 1
        m = sum(a == c for a, c in zip(bits, v_bits))
        aa = amp_bytes(bits)
        ex = sum(a == c for a, c in zip(aa, v_ser))
        print(f"{name:40s} {g:8d} {m:4d}/2048 {ex:2d}/12  {aa[:6]}")

    auto = paths["map_unscramble (auto)"]
    auto_gcsc = get_int_from_bit_stream(auto, 0, 23) << 1
    auto_mism = sum(1 for i in range(2048) if auto[i] != v_bits[i])

    frame = seisf_frame_to_vus_bytes(hs, fb)
    dec = decode_vus_frame(frame, 0)
    print()
    if not (dec and dec.blocks):
        print("e2e decode failed")
        return 1

    bl = dec.blocks[0]
    print(
        f"e2e seisf_frame_to_vus: GCSC={bl.gcsc} mode={bl.cs.mode_name} "
        f"n={bl.ndata} frame_eq={frame == v_frame}"
    )
    print(
        f"  X[:6]={[a for a in bl.amp[0][:6]]} "
        f"Y[:6]={[a for a in bl.amp[1][:6]]} "
        f"Z[:6]={[a for a in bl.amp[2][:6]]}"
    )
    print(
        f"  VUS  X[:6]={v_gold.amp[0][:6]} "
        f"Y[:6]={v_gold.amp[1][:6]} "
        f"Z[:6]={v_gold.amp[2][:6]}"
    )
    print(f"  residual bits vs VUS science region: {auto_mism}/2048")

    # Hard gates (same as test_regression gold checks)
    errors: list[str] = []
    if _PAIR36_BIT_OFFSET != 15:
        errors.append(f"bit_offset={_PAIR36_BIT_OFFSET} want 15")
    if matv != 423 or q0 != 423:
        errors.append(f"matv/Q={matv}/{q0} want 423/423")
    if auto_gcsc != GOLD_GCSC:
        errors.append(f"auto GCSC={auto_gcsc} want {GOLD_GCSC}")
    if auto_mism != 0:
        errors.append(f"science residual {auto_mism}/2048")
    if frame != v_frame:
        errors.append("frame bytes != VUS gold frame")
    if bl.gcsc != GOLD_GCSC or bl.cs.mode_name != "NORMAL" or bl.ndata != 83:
        errors.append(f"e2e decode GCSC/mode/n wrong: {bl.gcsc} {bl.cs.mode_name} {bl.ndata}")
    if list(bl.amp[0][:6]) != [0, 119, 38, 14, 6, 3]:
        errors.append(f"X[:6]={list(bl.amp[0][:6])}")

    if errors:
        print("\nASSERT FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nGOLD ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
