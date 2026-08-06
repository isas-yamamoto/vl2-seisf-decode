#!/usr/bin/env python3
"""
Sample decoder for Viking Lander 2 UTIG cassette files (utig/vkg.*).

  vkg.1  - vkg.46  ... SEISF / DLT  (scrambled science buffer; this tool)
  vkg.47 - vkg.56  ... VUS / USEIS (unscrambled; same layout as the
                       vusinfo C decoder, see legacy/vusinfo/)

README targets are vkg.1~vkg.46.

Examples
--------
  # Describe cassette subgroups
  python3 decode_vkg.py ../utig/vkg.1 --info

  # Decode SEISF frames (headers + science after MAP/UNSCR)
  python3 decode_vkg.py ../utig/vkg.1 --summary --max-frames 5

  # Frame summary only (year, DOY, GCSC, mode)
  python3 decode_vkg.py ../utig/vkg.1 --summary --max-frames 20

  # Dump samples CSV for first N frames
  python3 decode_vkg.py ../utig/vkg.1 --csv out.csv --max-frames 3

  # Compare VUS path (vkg.47+) against the C tool
  python3 decode_vkg.py ../utig/vkg.47 --summary --max-frames 10

  # SEISF without MAP (debug packing only)
  python3 decode_vkg.py ../utig/vkg.1 --raw --max-frames 2
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow running as a script directly (import siblings by path)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from seisf_decode import decode_seisf_file, describe_file, iter_seisf_frames
from vkg_format import open_vkg
from vus_decode import decode_vus_file


def _is_seisf_path(path: Path) -> bool:
    _, subgroups = open_vkg(str(path))
    if not subgroups:
        return True
    return subgroups[0][0].is_seisf or subgroups[0][0].label.startswith("DLT")


def _cmd_info(path: Path) -> int:
    print(describe_file(str(path)))
    if _is_seisf_path(path):
        n = 0
        years = set()
        doys = set()
        for loc, hs, header, _chained in iter_seisf_frames(str(path)):
            from vus_decode import parse_seisf_header_fields

            y, d = parse_seisf_header_fields(header + bytes(342))
            years.add(y)
            doys.add(d)
            n += 1
            if n >= 5000:
                break
        print(f"seisf_frames_scanned: {n}")
        if years:
            print(f"year_range: {min(years)}-{max(years)}")
            print(f"doy_values_sample: {sorted(doys)[:20]}")
    return 0


def _iter_decoded(path: Path, raw: bool, max_frames: int | None):
    if _is_seisf_path(path):
        return decode_seisf_file(str(path), unscramble=not raw, max_frames=max_frames)
    return _limit(decode_vus_file(str(path)), max_frames)


def _limit(it, max_frames: int | None):
    if max_frames is None:
        yield from it
        return
    for i, x in enumerate(it):
        if i >= max_frames:
            break
        yield x


def _cmd_summary(path: Path, raw: bool, max_frames: int | None) -> int:
    for fr in _iter_decoded(path, raw, max_frames):
        if not fr.blocks:
            print(
                f"frame={fr.frame_index:5d} year={fr.year} doy={fr.doy:3d} "
                f"(no science blocks) note={fr.note}"
            )
            continue
        for bi, block in enumerate(fr.blocks):
            print(
                f"frame={fr.frame_index:5d} year={fr.year} doy={fr.doy:3d} "
                f"gcsc={block.gcsc:8d} mode={block.cs.mode_name:6s} "
                f"n={block.ndata:3d} chg={block.change_code} "
                f"note={fr.note or ''}"
            )
    return 0


def _cmd_samples(path: Path, raw: bool, max_frames: int | None, limit_per_block: int) -> int:
    for fr in _iter_decoded(path, raw, max_frames):
        if not fr.blocks:
            print(
                f"# frame={fr.frame_index} year={fr.year} doy={fr.doy} "
                f"(no science) note={fr.note}"
            )
            continue
        for bi, block in enumerate(fr.blocks):
            print(
                f"# frame={fr.frame_index} block={bi} year={fr.year} doy={fr.doy} "
                f"gcsc={block.gcsc} mode={block.cs.mode_name} n={block.ndata}"
            )
            n = min(block.ndata, limit_per_block, len(block.amp[0]), len(block.amp[1]), len(block.amp[2]))
            for i in range(n):
                if block.cs.mode_name == "EVENT" and block.axis[0] and i < len(block.axis[0]):
                    print(
                        f"{i:4d}  {block.amp[0][i]:4d} {block.axis[0][i]:3d}  "
                        f"{block.amp[1][i]:4d} {block.axis[1][i]:3d}  "
                        f"{block.amp[2][i]:4d} {block.axis[2][i]:3d}"
                    )
                else:
                    print(
                        f"{i:4d}  {block.amp[0][i]:4d}  "
                        f"{block.amp[1][i]:4d}  {block.amp[2][i]:4d}"
                    )
    return 0


def _cmd_csv(path: Path, out: Path, raw: bool, max_frames: int | None) -> int:
    fields = [
        "frame",
        "block",
        "year",
        "doy",
        "gcsc",
        "mode",
        "sample",
        "amp_x",
        "amp_y",
        "amp_z",
        "axis_x",
        "axis_y",
        "axis_z",
        "note",
    ]
    n_rows = 0
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for fr in _iter_decoded(path, raw, max_frames):
            if not fr.blocks:
                continue
            for bi, block in enumerate(fr.blocks):
                event = block.cs.mode_name == "EVENT" and bool(block.axis[0])
                n = min(
                    block.ndata,
                    len(block.amp[0]),
                    len(block.amp[1]),
                    len(block.amp[2]),
                )
                for i in range(n):
                    w.writerow(
                        {
                            "frame": fr.frame_index,
                            "block": bi,
                            "year": fr.year,
                            "doy": fr.doy,
                            "gcsc": block.gcsc,
                            "mode": block.cs.mode_name,
                            "sample": i,
                            "amp_x": block.amp[0][i],
                            "amp_y": block.amp[1][i],
                            "amp_z": block.amp[2][i],
                            "axis_x": block.axis[0][i]
                            if event and i < len(block.axis[0])
                            else "",
                            "axis_y": block.axis[1][i]
                            if event and i < len(block.axis[1])
                            else "",
                            "axis_z": block.axis[2][i]
                            if event and i < len(block.axis[2])
                            else "",
                            "note": fr.note,
                        }
                    )
                    n_rows += 1
    print(f"wrote {n_rows} rows -> {out}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Decode Viking Lander 2 UTIG vkg.* (SEISF vkg.1-46 / VUS vkg.47-56)"
    )
    p.add_argument("vkg", type=Path, help="path to vkg.N file")
    p.add_argument("--info", action="store_true", help="show cassette subgroup layout")
    p.add_argument("--summary", action="store_true", help="print year/DOY/GCSC/mode lines")
    p.add_argument(
        "--samples",
        action="store_true",
        help="print amplitude samples (default if no other mode)",
    )
    p.add_argument("--csv", type=Path, help="write sample CSV to this path")
    p.add_argument(
        "--max-frames",
        type=int,
        default=None,
        metavar="N",
        help="process only the first N frames (default: no limit, all frames)",
    )
    p.add_argument(
        "--limit-per-block",
        type=int,
        default=20,
        help="with --samples: print at most this many samples per block (default 20)",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="SEISF only: skip MAP/UNSCR (debug)",
    )
    args = p.parse_args(argv)

    if not args.vkg.is_file():
        print(f"not found: {args.vkg}", file=sys.stderr)
        return 1

    if args.info:
        return _cmd_info(args.vkg)
    if args.csv:
        return _cmd_csv(args.vkg, args.csv, args.raw, args.max_frames)
    if args.summary:
        return _cmd_summary(args.vkg, args.raw, args.max_frames)
    # default: samples (no silent max-frames; use --max-frames explicitly to cap)
    return _cmd_samples(args.vkg, args.raw, args.max_frames, args.limit_per_block)


if __name__ == "__main__":
    raise SystemExit(main())
