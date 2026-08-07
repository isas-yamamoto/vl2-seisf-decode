#!/usr/bin/env python3
"""
Coverage: NSSDC PSPG-00070 ASCII reformat vs UTIG cassette VUS / SEISF.

Match keys (explicitly NOT the 108-byte dual-archive header):
  primary   : IGCSC / first science-block GCSC
  secondary : (IYEAR, IDAY±δ) with GCSC  — DOY may be off by 1 between products

  python3 tools/coverage_nssdc.py
  python3 tools/coverage_nssdc.py --no-seisf   # skip SEISF GCSC pass

Outputs under out/:
  coverage_nssdc.json
  coverage_nssdc_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from seisf_decode import (  # noqa: E402
    find_seisf_frame_bases,
    iter_seisf_frames,
    seisf_frame_to_vus_bytes,
)
from vkg_format import open_vkg  # noqa: E402
from vus_decode import (  # noqa: E402
    BITS_PER_WORD,
    SIZE_COMMAND_STATUS,
    extract_command_status,
    get_int_from_bit_stream,
    make_bit_stream,
    parse_seisf_header_fields,
)

UTIG = ROOT / "utig"
NSSDC_REFORMAT = ROOT / "nssdc" / "PSPG-00070" / "reformat"
OUT_DIR = ROOT / "out"
OUT_JSON = OUT_DIR / "coverage_nssdc.json"
OUT_MD = OUT_DIR / "coverage_nssdc_report.md"

# Science stream starts after 18 VUS words (engineering header region).
_SCI0 = 18 * BITS_PER_WORD


def first_block_gcsc_mode(frame450: bytes) -> Optional[Tuple[int, str]]:
    """Cheap first-block GCSC + mode name (no amplitude unpacking)."""
    if len(frame450) < 450:
        return None
    if frame450[:20] == b"\x00" * 20 or all(b == 0x09 for b in frame450[:450]):
        return None
    try:
        bits = make_bit_stream(frame450[:450])
        if _SCI0 + 23 + SIZE_COMMAND_STATUS > len(bits):
            return None
        gcsc = get_int_from_bit_stream(bits, _SCI0, 23) << 1
        cmd = get_int_from_bit_stream(bits, _SCI0 + 23, SIZE_COMMAND_STATUS)
        return int(gcsc), extract_command_status(cmd).mode_name
    except Exception:
        return None


def seisf_paths() -> List[Path]:
    return [UTIG / f"vkg.{n}" for n in range(1, 47) if (UTIG / f"vkg.{n}").is_file()]


def vus_paths() -> List[Path]:
    return [UTIG / f"vkg.{n}" for n in range(47, 57) if (UTIG / f"vkg.{n}").is_file()]


def parse_nssdc_reformat_meta(path: Path) -> Optional[Dict[str, object]]:
    meta: Dict[str, str] = {}
    try:
        with path.open("r", errors="replace") as f:
            for line in f:
                if not line.startswith("#"):
                    break
                if ":" not in line:
                    continue
                k, v = line[1:].split(":", 1)
                meta[k.strip()] = v.strip()
    except OSError:
        return None
    try:
        year = int(meta["IYEAR"])
        doy = int(meta["IDAY"])
        gcsc = int(meta["IGCSC"])
    except (KeyError, ValueError):
        return None
    try:
        rel = str(path.resolve().relative_to(ROOT))
    except ValueError:
        rel = str(path)
    return {
        "year": year,
        "doy": doy,
        "gcsc": gcsc,
        "mode": meta.get("MODE", ""),
        "lndr": meta.get("LNDR", ""),
        "isdr": meta.get("ISDR", ""),
        "file": rel,
    }


def index_nssdc(reformat_root: Path) -> Dict[str, object]:
    """Index all ASCII reformat event files under PSPG-00070/reformat."""
    t0 = time.time()
    n_files = 0
    n_bad = 0
    by_gcsc: Dict[int, List[Tuple[int, int]]] = defaultdict(list)  # gcsc -> [(y,d), ...]
    triples: Set[Tuple[int, int, int]] = set()
    modes = Counter()
    years = Counter()
    landers = Counter()
    volumes = Counter()

    for path in sorted(reformat_root.rglob("*.txt")):
        rec = parse_nssdc_reformat_meta(path)
        if rec is None:
            n_bad += 1
            continue
        n_files += 1
        y, d, g = int(rec["year"]), int(rec["doy"]), int(rec["gcsc"])
        triples.add((y, d, g))
        by_gcsc[g].append((y, d))
        modes[str(rec["mode"])] += 1
        years[y] += 1
        landers[str(rec["lndr"])] += 1
        # volume dir e.g. DD029661_F1
        volumes[path.parent.name] += 1
        if n_files % 50000 == 0:
            print(f"  NSSDC scanned {n_files}...", flush=True)

    # GCSC uniqueness: how often one GCSC maps to multiple (y,d)
    multi_yd = sum(1 for ys in by_gcsc.values() if len(set(ys)) > 1)
    multi_file = sum(1 for ys in by_gcsc.values() if len(ys) > 1)

    return {
        "source": str(reformat_root.relative_to(ROOT)),
        "n_files": n_files,
        "n_parse_fail": n_bad,
        "n_unique_gcsc": len(by_gcsc),
        "n_unique_year_doy_gcsc": len(triples),
        "gcsc_with_multiple_year_doy": multi_yd,
        "gcsc_with_multiple_files": multi_file,
        "modes": dict(modes.most_common()),
        "years": dict(sorted(years.items())),
        "landers": dict(landers),
        "n_volumes": len(volumes),
        "elapsed_s": round(time.time() - t0, 2),
        "_by_gcsc": by_gcsc,
        "_triples": triples,
        "_gcsc_set": set(by_gcsc.keys()),
    }


def index_vus_gcsc() -> Dict[str, object]:
    """Enumerate all VUS frames; light first-block GCSC."""
    t0 = time.time()
    n_frames = 0
    n_gcsc_ok = 0
    by_gcsc: Dict[int, List[Tuple[int, int, str]]] = defaultdict(list)
    triples: Set[Tuple[int, int, int]] = set()
    years = Counter()
    modes = Counter()
    headers: Set[bytes] = set()

    for path in vus_paths():
        name = path.name
        _, sgs = open_vkg(str(path))
        n_here = 0
        for _si, (hdr, body) in enumerate(sgs):
            rlen = hdr.record_length
            pos = 0
            while pos + rlen <= len(body):
                rec = body[pos : pos + rlen]
                pos += rlen
                for j in range(0, (rlen // 450) * 450, 450):
                    fr = bytes(rec[j : j + 450])
                    n_frames += 1
                    n_here += 1
                    headers.add(fr[:108])
                    try:
                        year, doy = parse_seisf_header_fields(fr)
                    except Exception:
                        year, doy = 0, 0
                    info = first_block_gcsc_mode(fr)
                    if info is None:
                        continue
                    gcsc, mode = info
                    n_gcsc_ok += 1
                    triples.add((year, doy, gcsc))
                    by_gcsc[gcsc].append((year, doy, name))
                    years[year] += 1
                    modes[mode] += 1
        print(f"  VUS {name}: {n_here} frames", flush=True)

    return {
        "n_frames": n_frames,
        "n_unique_headers": len(headers),
        "n_gcsc_ok": n_gcsc_ok,
        "n_unique_gcsc": len(by_gcsc),
        "n_unique_year_doy_gcsc": len(triples),
        "years": dict(sorted(years.items())),
        "modes": dict(modes.most_common()),
        "elapsed_s": round(time.time() - t0, 2),
        "_by_gcsc": by_gcsc,
        "_triples": triples,
        "_gcsc_set": set(by_gcsc.keys()),
    }


def index_seisf_gcsc(limit_bases: Optional[int] = None) -> Dict[str, object]:
    """
    Production SEISF decode → first-block GCSC.
    This is slower than VUS light path; keep optional.
    """
    t0 = time.time()
    n_bases = 0
    n_ok = 0
    by_gcsc: Dict[int, List[Tuple[int, int, str]]] = defaultdict(list)
    triples: Set[Tuple[int, int, int]] = set()
    headers: Set[bytes] = set()
    years = Counter()

    for path in seisf_paths():
        name = path.name
        n_here = 0
        for loc, hs, header, _chained in iter_seisf_frames(str(path), require_chained=True):
            n_bases += 1
            n_here += 1
            try:
                year, doy = parse_seisf_header_fields(header + bytes(342))
                headers.add(bytes(header[:108]) if len(header) >= 108 else bytes(header))
                vus_b = seisf_frame_to_vus_bytes(hs, loc.halfword_offset)
                info = first_block_gcsc_mode(vus_b)
            except Exception:
                info = None
                year, doy = 0, 0
            if info is not None:
                gcsc, _mode = info
                n_ok += 1
                triples.add((year, doy, gcsc))
                by_gcsc[gcsc].append((year, doy, name))
                years[year] += 1
            if limit_bases and n_bases >= limit_bases:
                break
        print(f"  SEISF {name}: {n_here} bases (cum {n_bases}, ok {n_ok})", flush=True)
        if limit_bases and n_bases >= limit_bases:
            break

    return {
        "n_bases": n_bases,
        "n_gcsc_ok": n_ok,
        "n_unique_headers": len(headers),
        "n_unique_gcsc": len(by_gcsc),
        "n_unique_year_doy_gcsc": len(triples),
        "years": dict(sorted(years.items())),
        "elapsed_s": round(time.time() - t0, 2),
        "truncated": bool(limit_bases),
        "_by_gcsc": by_gcsc,
        "_triples": triples,
        "_gcsc_set": set(by_gcsc.keys()),
    }


def set_compare(
    a: Set[int], b: Set[int], name_a: str, name_b: str
) -> Dict[str, object]:
    both = a & b
    only_a = a - b
    only_b = b - a
    return {
        f"n_{name_a}": len(a),
        f"n_{name_b}": len(b),
        "n_both": len(both),
        f"n_only_{name_a}": len(only_a),
        f"n_only_{name_b}": len(only_b),
        f"frac_{name_a}_in_{name_b}": (len(both) / len(a)) if a else None,
        f"frac_{name_b}_in_{name_a}": (len(both) / len(b)) if b else None,
    }


def triple_compare(
    a: Set[Tuple[int, int, int]],
    b: Set[Tuple[int, int, int]],
    name_a: str,
    name_b: str,
    doy_slack: int = 0,
) -> Dict[str, object]:
    """Exact (y,d,g) and optionally match with |Δdoy|≤slack same y,g."""
    both = a & b
    only_a = a - b
    only_b = b - a
    out: Dict[str, object] = {
        f"n_{name_a}": len(a),
        f"n_{name_b}": len(b),
        "n_both_exact": len(both),
        f"n_only_{name_a}_exact": len(only_a),
        f"n_only_{name_b}_exact": len(only_b),
        f"frac_{name_a}_in_{name_b}_exact": (len(both) / len(a)) if a else None,
        f"frac_{name_b}_in_{name_a}_exact": (len(both) / len(b)) if b else None,
    }
    if doy_slack <= 0:
        return out

    # Index b by (year, gcsc) -> set of doys
    b_yd: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
    for y, d, g in b:
        b_yd[(y, g)].add(d)

    soft_a = 0
    for y, d, g in a:
        doys = b_yd.get((y, g))
        if not doys:
            continue
        if any(abs(d - bd) <= doy_slack for bd in doys):
            soft_a += 1
    a_yd: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
    for y, d, g in a:
        a_yd[(y, g)].add(d)
    soft_b = 0
    for y, d, g in b:
        doys = a_yd.get((y, g))
        if not doys:
            continue
        if any(abs(d - ad) <= doy_slack for ad in doys):
            soft_b += 1

    out["doy_slack"] = doy_slack
    out[f"n_{name_a}_matched_doy_pm{doy_slack}"] = soft_a
    out[f"n_{name_b}_matched_doy_pm{doy_slack}"] = soft_b
    out[f"frac_{name_a}_in_{name_b}_doy_pm{doy_slack}"] = (
        (soft_a / len(a)) if a else None
    )
    out[f"frac_{name_b}_in_{name_a}_doy_pm{doy_slack}"] = (
        (soft_b / len(b)) if b else None
    )
    return out


def year_gcsc_hist(
    nssdc_by: Dict[int, List[Tuple[int, int]]],
    other_gcsc: Set[int],
) -> Dict[str, Dict[str, int]]:
    """Per calendar year (from NSSDC side): how many unique GCSC land in other."""
    by_year_gcsc: Dict[int, Set[int]] = defaultdict(set)
    for g, yds in nssdc_by.items():
        for y, _d in yds:
            by_year_gcsc[y].add(g)
    out: Dict[str, Dict[str, int]] = {}
    for y in sorted(by_year_gcsc):
        gs = by_year_gcsc[y]
        both = gs & other_gcsc
        out[str(y)] = {
            "nssdc_unique_gcsc": len(gs),
            "also_in_other": len(both),
            "nssdc_only": len(gs - other_gcsc),
        }
    return out


def pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    return f"{100.0 * x:.3f}%"


def write_report(summary: Dict[str, object]) -> str:
    nv = summary["vs_vus_gcsc"]
    nt = summary["vs_vus_year_doy_gcsc"]
    lines = [
        "# NSSDC ASCII × cassette coverage",
        "",
        "NSSDC source: **PSPG-00070 reformat** (`#IYEAR` / `#IDAY` / `#IGCSC` headers).",
        "",
        "Match key is **not** the 108-byte SEISF/VUS engineering header.",
        "Primary key: **GCSC** (first science block / `#IGCSC`).",
        "Secondary: **(year, DOY, GCSC)** with optional DOY ±1 (archive calendar packing).",
        "",
        "## NSSDC inventory",
        "",
        f"- Files (parse OK): **{summary['nssdc']['n_files']}**",
        f"- Unique GCSC: **{summary['nssdc']['n_unique_gcsc']}**",
        f"- Unique (year, DOY, GCSC): **{summary['nssdc']['n_unique_year_doy_gcsc']}**",
        f"- Volumes: {summary['nssdc']['n_volumes']}",
        f"- Landers: `{summary['nssdc']['landers']}`",
        f"- Modes: `{summary['nssdc']['modes']}`",
        f"- Years: `{summary['nssdc']['years']}`",
        f"- GCSC with multiple (year,DOY): {summary['nssdc']['gcsc_with_multiple_year_doy']}",
        f"- Scan time: {summary['nssdc']['elapsed_s']} s",
        "",
        "## Cassette VUS inventory (for compare)",
        "",
        f"- Frames: **{summary['vus']['n_frames']}**",
        f"- GCSC decode OK: **{summary['vus']['n_gcsc_ok']}**",
        f"- Unique GCSC: **{summary['vus']['n_unique_gcsc']}**",
        f"- Unique (year, DOY, GCSC): **{summary['vus']['n_unique_year_doy_gcsc']}**",
        f"- Scan time: {summary['vus']['elapsed_s']} s",
        "",
        "## NSSDC ∩ VUS (GCSC)",
        "",
        "| Quantity | Count | Fraction |",
        "|----------|------:|---------:|",
        f"| NSSDC GCSC also in VUS | {nv['n_both']} | {pct(nv['frac_nssdc_in_vus'])} of NSSDC |",
        f"| VUS GCSC also in NSSDC | {nv['n_both']} | {pct(nv['frac_vus_in_nssdc'])} of VUS |",
        f"| NSSDC-only GCSC | {nv['n_only_nssdc']} | |",
        f"| VUS-only GCSC | {nv['n_only_vus']} | |",
        "",
        "## NSSDC ∩ VUS (year, DOY, GCSC)",
        "",
        f"- Exact: NSSDC→VUS **{pct(nt['frac_nssdc_in_vus_exact'])}** "
        f"({nt['n_both_exact']} / {nt['n_nssdc']})",
        f"- Exact: VUS→NSSDC **{pct(nt['frac_vus_in_nssdc_exact'])}** "
        f"({nt['n_both_exact']} / {nt['n_vus']})",
    ]
    if "frac_nssdc_in_vus_doy_pm1" in nt:
        lines += [
            f"- DOY±1: NSSDC→VUS **{pct(nt['frac_nssdc_in_vus_doy_pm1'])}** "
            f"({nt['n_nssdc_matched_doy_pm1']} / {nt['n_nssdc']})",
            f"- DOY±1: VUS→NSSDC **{pct(nt['frac_vus_in_nssdc_doy_pm1'])}** "
            f"({nt['n_vus_matched_doy_pm1']} / {nt['n_vus']})",
        ]
    lines += [
        "",
        "### Per-year (NSSDC GCSC, present in VUS)",
        "",
        "| Year | NSSDC GCSC | also VUS | NSSDC-only |",
        "|-----:|-----------:|---------:|-----------:|",
    ]
    for y, row in summary["nssdc_year_vs_vus"].items():
        lines.append(
            f"| {y} | {row['nssdc_unique_gcsc']} | {row['also_in_other']} | {row['nssdc_only']} |"
        )

    if summary.get("seisf"):
        ns = summary["vs_seisf_gcsc"]
        nst = summary["vs_seisf_year_doy_gcsc"]
        lines += [
            "",
            "## SEISF inventory (production decode → GCSC)",
            "",
            f"- Bases scanned: **{summary['seisf']['n_bases']}**"
            + (" (truncated)" if summary["seisf"].get("truncated") else ""),
            f"- GCSC OK: **{summary['seisf']['n_gcsc_ok']}**",
            f"- Unique GCSC: **{summary['seisf']['n_unique_gcsc']}**",
            f"- Scan time: {summary['seisf']['elapsed_s']} s",
            "",
            "## NSSDC ∩ SEISF (GCSC)",
            "",
            f"- NSSDC→SEISF: **{pct(ns['frac_nssdc_in_seisf'])}** "
            f"({ns['n_both']} / {ns['n_nssdc']})",
            f"- SEISF→NSSDC: **{pct(ns['frac_seisf_in_nssdc'])}** "
            f"({ns['n_both']} / {ns['n_seisf']})",
            f"- NSSDC-only: {ns['n_only_nssdc']}; SEISF-only: {ns['n_only_seisf']}",
            "",
            "## NSSDC ∩ SEISF (year, DOY, GCSC)",
            "",
            f"- Exact NSSDC→SEISF: **{pct(nst['frac_nssdc_in_seisf_exact'])}**",
        ]
        if "frac_nssdc_in_seisf_doy_pm1" in nst:
            lines.append(
                f"- DOY±1 NSSDC→SEISF: **{pct(nst['frac_nssdc_in_seisf_doy_pm1'])}**"
            )
        lines += [
            "",
            "### Per-year (NSSDC GCSC, present in SEISF)",
            "",
            "| Year | NSSDC GCSC | also SEISF | NSSDC-only |",
            "|-----:|-----------:|-----------:|-----------:|",
        ]
        for y, row in summary["nssdc_year_vs_seisf"].items():
            lines.append(
                f"| {y} | {row['nssdc_unique_gcsc']} | {row['also_in_other']} | {row['nssdc_only']} |"
            )

    lines += [
        "",
        "## Triple product (GCSC)",
        "",
        f"- NSSDC ∩ VUS ∩ SEISF: **{summary.get('n_gcsc_all_three', 'n/a')}**"
        if summary.get("seisf")
        else "- SEISF scan skipped (`--no-seisf`).",
        "",
        "## Notes",
        "",
        "- `separate/` and `preformat/` trees are alternate presentations of the same "
        "PSPG-00070 hold; this report uses **reformat** only (one file ≈ one event).",
        "- GCSC identity is archival / operational time-tag identity, not bit-identical "
        "frame content between NSSDC and cassette.",
        "- Gold-pair style check: cassette DOY can differ by 1 from `#IDAY` for the same GCSC.",
        "",
        f"JSON: [{OUT_JSON.name}]({OUT_JSON.name})",
        "",
    ]
    return "\n".join(lines)


def public_index(idx: Dict[str, object]) -> Dict[str, object]:
    """Drop private sets for JSON serialization."""
    return {k: v for k, v in idx.items() if not k.startswith("_")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-seisf",
        action="store_true",
        help="skip production SEISF→GCSC pass (faster)",
    )
    ap.add_argument(
        "--seisf-limit",
        type=int,
        default=0,
        help="decode only first N SEISF bases (debug)",
    )
    ap.add_argument(
        "--nssdc-root",
        type=Path,
        default=NSSDC_REFORMAT,
        help="path to reformat tree",
    )
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== NSSDC reformat ===", flush=True)
    nssdc = index_nssdc(args.nssdc_root)
    print(
        f"  files={nssdc['n_files']} unique_gcsc={nssdc['n_unique_gcsc']} "
        f"triples={nssdc['n_unique_year_doy_gcsc']} ({nssdc['elapsed_s']}s)",
        flush=True,
    )

    print("=== VUS GCSC ===", flush=True)
    vus = index_vus_gcsc()
    print(
        f"  frames={vus['n_frames']} unique_gcsc={vus['n_unique_gcsc']} "
        f"({vus['elapsed_s']}s)",
        flush=True,
    )

    vs_vus_g = set_compare(
        nssdc["_gcsc_set"], vus["_gcsc_set"], "nssdc", "vus"  # type: ignore[arg-type]
    )
    # rename keys to clearer names
    vs_vus_gcsc = {
        "n_nssdc": vs_vus_g["n_nssdc"],
        "n_vus": vs_vus_g["n_vus"],
        "n_both": vs_vus_g["n_both"],
        "n_only_nssdc": vs_vus_g["n_only_nssdc"],
        "n_only_vus": vs_vus_g["n_only_vus"],
        "frac_nssdc_in_vus": vs_vus_g["frac_nssdc_in_vus"],
        "frac_vus_in_nssdc": vs_vus_g["frac_vus_in_nssdc"],
    }
    vs_vus_t = triple_compare(
        nssdc["_triples"],  # type: ignore[arg-type]
        vus["_triples"],  # type: ignore[arg-type]
        "nssdc",
        "vus",
        doy_slack=1,
    )

    summary: Dict[str, object] = {
        "match_semantics": {
            "primary": "GCSC (#IGCSC / first science block)",
            "secondary": "(year, DOY, GCSC) with optional DOY±1",
            "not": "108-byte engineering header bit identity",
        },
        "nssdc": public_index(nssdc),
        "vus": public_index(vus),
        "vs_vus_gcsc": vs_vus_gcsc,
        "vs_vus_year_doy_gcsc": vs_vus_t,
        "nssdc_year_vs_vus": year_gcsc_hist(
            nssdc["_by_gcsc"], vus["_gcsc_set"]  # type: ignore[arg-type]
        ),
    }

    seisf: Optional[Dict[str, object]] = None
    if not args.no_seisf:
        print("=== SEISF production GCSC ===", flush=True)
        lim = args.seisf_limit or None
        seisf = index_seisf_gcsc(limit_bases=lim)
        print(
            f"  bases={seisf['n_bases']} unique_gcsc={seisf['n_unique_gcsc']} "
            f"({seisf['elapsed_s']}s)",
            flush=True,
        )
        vs_s_g = set_compare(
            nssdc["_gcsc_set"], seisf["_gcsc_set"], "nssdc", "seisf"  # type: ignore[arg-type]
        )
        vs_seisf_gcsc = {
            "n_nssdc": vs_s_g["n_nssdc"],
            "n_seisf": vs_s_g["n_seisf"],
            "n_both": vs_s_g["n_both"],
            "n_only_nssdc": vs_s_g["n_only_nssdc"],
            "n_only_seisf": vs_s_g["n_only_seisf"],
            "frac_nssdc_in_seisf": vs_s_g["frac_nssdc_in_seisf"],
            "frac_seisf_in_nssdc": vs_s_g["frac_seisf_in_nssdc"],
        }
        vs_seisf_t = triple_compare(
            nssdc["_triples"],  # type: ignore[arg-type]
            seisf["_triples"],  # type: ignore[arg-type]
            "nssdc",
            "seisf",
            doy_slack=1,
        )
        all3 = nssdc["_gcsc_set"] & vus["_gcsc_set"] & seisf["_gcsc_set"]  # type: ignore[operator]
        summary["seisf"] = public_index(seisf)
        summary["vs_seisf_gcsc"] = vs_seisf_gcsc
        summary["vs_seisf_year_doy_gcsc"] = vs_seisf_t
        summary["nssdc_year_vs_seisf"] = year_gcsc_hist(
            nssdc["_by_gcsc"], seisf["_gcsc_set"]  # type: ignore[arg-type]
        )
        summary["n_gcsc_all_three"] = len(all3)
        summary["frac_nssdc_in_all_three"] = (
            len(all3) / len(nssdc["_gcsc_set"]) if nssdc["_gcsc_set"] else None
        )

    # Spot-check gold pair GCSC
    gold = 125078
    summary["gold_gcsc_125078"] = {
        "in_nssdc": gold in nssdc["_gcsc_set"],  # type: ignore[operator]
        "in_vus": gold in vus["_gcsc_set"],  # type: ignore[operator]
        "nssdc_year_doy": list(set(nssdc["_by_gcsc"].get(gold, []))),  # type: ignore[index]
        "vus_year_doy_sample": list(
            {(y, d) for y, d, _f in vus["_by_gcsc"].get(gold, [])}  # type: ignore[index]
        )[:5],
    }

    text = write_report(summary)
    OUT_MD.write_text(text, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(text)
    print(f"\nWrote {OUT_JSON} and {OUT_MD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
