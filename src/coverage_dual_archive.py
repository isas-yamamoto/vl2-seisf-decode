#!/usr/bin/env python3
"""
Full dual-archive coverage: SEISF (vkg.1–46) vs VUS (vkg.47–56).

Match key = first 108 bytes of the VUS-shaped engineering header.

  python3 coverage_dual_archive.py              # headers + bit sample
  python3 coverage_dual_archive.py --no-bits
  python3 coverage_dual_archive.py --bits-all   # all production-eligible

Outputs under draft/figures/:
  coverage_dual_archive.json
  coverage_dual_archive_report.md
  coverage_seisf_only.jsonl   (one line per SEISF base with no VUS twin)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from seisf_decode import (  # noqa: E402
    estimate_q_from_matv,
    iter_seisf_frames,
    map_unscramble_best_vs_ref,
)
from vkg_format import open_vkg  # noqa: E402
from vus_decode import make_bit_stream, parse_seisf_header_fields  # noqa: E402

UTIG = ROOT / "utig"
OUT_DIR = ROOT / "draft" / "figures"
OUT_JSON = OUT_DIR / "coverage_dual_archive.json"
OUT_MD = OUT_DIR / "coverage_dual_archive_report.md"
OUT_SEISF_ONLY = OUT_DIR / "coverage_seisf_only.jsonl"
OUT_VUS_ONLY = OUT_DIR / "coverage_vus_only_sample.jsonl"


def seisf_paths() -> List[Path]:
    return [UTIG / f"vkg.{n}" for n in range(1, 47) if (UTIG / f"vkg.{n}").is_file()]


def vus_paths() -> List[Path]:
    return [UTIG / f"vkg.{n}" for n in range(47, 57) if (UTIG / f"vkg.{n}").is_file()]


def hdr_year_doy(hdr108: bytes) -> Tuple[int, int]:
    try:
        return parse_seisf_header_fields(hdr108 + bytes(342))
    except Exception:
        return 0, 0


def index_vus() -> Tuple[Dict[bytes, Tuple[str, int]], Dict[str, int]]:
    """
    Map 108B header -> (primary_file, n_occurrences).
    Store only one primary location file to save memory.
    """
    index: Dict[bytes, Tuple[str, int]] = {}
    per_file: Counter = Counter()
    total = 0
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
                    key = bytes(rec[j : j + 108])
                    if key in index:
                        f0, c = index[key]
                        index[key] = (f0, c + 1)
                    else:
                        index[key] = (name, 1)
                    total += 1
                    n_here += 1
        per_file[name] = n_here
        print(f"  VUS {name}: {n_here} frames", flush=True)
    stats = {
        "total_frames": total,
        "unique_headers": len(index),
        "per_file": dict(sorted(per_file.items())),
    }
    return index, stats


def load_vus_frame_by_header(path: Path, want: bytes) -> Optional[bytes]:
    """Linear search for first frame with header (used sparingly for bit checks)."""
    _, sgs = open_vkg(str(path))
    for _si, (hdr, body) in enumerate(sgs):
        rlen = hdr.record_length
        pos = 0
        while pos + rlen <= len(body):
            rec = body[pos : pos + rlen]
            pos += rlen
            for j in range(0, (rlen // 450) * 450, 450):
                if bytes(rec[j : j + 108]) == want:
                    return bytes(rec[j : j + 450])
    return None


def load_all_distinct_vus_frames_by_header(want: bytes) -> List[bytes]:
    """
    Every *distinct* 450B frame content sharing this 108B header, across the
    full VUS archive. Only 15 of 387,011 unique VUS headers archive-wide
    have more than one distinct content (AUTHOR_NOTES.md item 23); this full
    multi-file scan is only ever called as a rare fallback when the single
    primary-file candidate already failed bit-exact verification, not on the
    common path.
    """
    seen: Dict[bytes, None] = {}
    for path in vus_paths():
        _, sgs = open_vkg(str(path))
        for _si, (hdr, body) in enumerate(sgs):
            rlen = hdr.record_length
            pos = 0
            while pos + rlen <= len(body):
                rec = body[pos : pos + rlen]
                pos += rlen
                for j in range(0, (rlen // 450) * 450, 450):
                    if bytes(rec[j : j + 108]) == want:
                        seen.setdefault(bytes(rec[j : j + 450]), None)
    return list(seen.keys())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bits", action="store_true")
    ap.add_argument(
        "--bits-all",
        action="store_true",
        help="science-bit score every production-eligible match (slow)",
    )
    ap.add_argument(
        "--bits-limit",
        type=int,
        default=2000,
        help="max matches to science-score if not --bits-all (default 2000)",
    )
    args = ap.parse_args()
    if not UTIG.is_dir():
        print(f"missing {UTIG}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Index VUS vkg.47–56 ===", flush=True)
    t0 = time.time()
    vus_index, vus_stats = index_vus()
    print(
        f"VUS: {vus_stats['total_frames']} frames, "
        f"{vus_stats['unique_headers']} unique, {time.time() - t0:.1f}s",
        flush=True,
    )

    print("=== Scan SEISF vkg.1–46 ===", flush=True)
    per_file_bases: Counter = Counter()
    per_file_matched: Counter = Counter()
    matched_by_vus_file: Counter = Counter()
    seisf_keys: Set[bytes] = set()
    seisf_dup_headers = 0
    n_matched = 0
    n_multi_vus = 0
    matv_oor = 0
    production_matched = 0

    bits_checked = bit_ok = bit_fail = 0
    pad_force_n1_rescues = 0
    bit_fail_sample: List[Dict[str, Any]] = []
    seisf_only_sample: List[Dict[str, Any]] = []
    n_seisf_only = 0

    do_bits = not args.no_bits
    bits_limit = None if args.bits_all else args.bits_limit
    # Cache VUS frames for bit checks: file -> list not needed; small cache by key
    frame_cache: Dict[bytes, Optional[bytes]] = {}

    t1 = time.time()
    with OUT_SEISF_ONLY.open("w", encoding="utf-8") as only_f:
        for path in seisf_paths():
            name = path.name
            n_base = n_match = 0
            for loc, hs, header, chained in iter_seisf_frames(str(path), require_chained=False):
                key = bytes(header)
                year, doy = hdr_year_doy(key)
                hit = vus_index.get(key)

                if not chained:
                    if hit is None:
                        # No VUS counterpart to verify against; fall back to
                        # the structural heuristic (exclude, as an isolated
                        # base is *usually* a coincidental match -- see
                        # AUTHOR_NOTES item 12 for the known false-negative
                        # rate this accepts).
                        continue
                    # Isolated but header-matched: don't guess: verify
                    # bit-exactness directly, since roughly 40% of these
                    # turn out to be genuine frames (AUTHOR_NOTES item 12).
                    vfile_v, nloc_v = hit
                    if key not in frame_cache:
                        frame_cache[key] = load_vus_frame_by_header(UTIG / vfile_v, key)
                    fr_v = frame_cache[key]
                    verified = False
                    bits_v = None
                    if fr_v is not None:
                        try:
                            vb_v = make_bit_stream(fr_v)[648 : 648 + 2048]
                            bits_v, mism_v, _mode = map_unscramble_best_vs_ref(
                                hs,
                                loc.halfword_offset,
                                vb_v,
                                record_halfwords=loc.record_halfwords,
                                trailing_all_ones=loc.trailing_all_ones,
                            )
                            verified = mism_v == 0
                        except Exception:
                            verified = False
                    if not verified and nloc_v > 1 and bits_v is not None:
                        # Rare: this header has multiple occurrences and the
                        # one primary-file candidate wasn't bit-exact -- see
                        # if a distinct-content duplicate elsewhere is
                        # (AUTHOR_NOTES item 23).
                        for fr_alt in load_all_distinct_vus_frames_by_header(key):
                            vb_alt = make_bit_stream(fr_alt)[648 : 648 + 2048]
                            _b, m_alt, _ = map_unscramble_best_vs_ref(
                                hs,
                                loc.halfword_offset,
                                vb_alt,
                                record_halfwords=loc.record_halfwords,
                                trailing_all_ones=loc.trailing_all_ones,
                            )
                            if m_alt == 0:
                                verified = True
                                break
                    if not verified:
                        continue  # confirmed spurious; exclude

                n_base += 1
                if key in seisf_keys:
                    seisf_dup_headers += 1
                else:
                    seisf_keys.add(key)

                if hit is None:
                    n_seisf_only += 1
                    rec = {
                        "file": name,
                        "sg": loc.subgroup,
                        "rec": loc.record_index,
                        "base": loc.halfword_offset,
                        "year": year,
                        "doy": doy,
                    }
                    only_f.write(json.dumps(rec) + "\n")
                    if len(seisf_only_sample) < 100:
                        seisf_only_sample.append(rec)
                    elif n_seisf_only % max(1, n_seisf_only // 50) == 0 and len(seisf_only_sample) < 150:
                        seisf_only_sample.append(rec)
                    continue

                n_match += 1
                n_matched += 1
                vfile, nloc = hit
                matched_by_vus_file[vfile] += 1
                if nloc > 1:
                    n_multi_vus += 1

                matv = -1
                eligible = False
                if do_bits:
                    try:
                        _q, matv = estimate_q_from_matv(hs, loc.halfword_offset)
                    except Exception:
                        matv = -1
                    eligible = 0 < matv < 503
                    if eligible:
                        production_matched += 1
                    else:
                        matv_oor += 1

                if do_bits and eligible and (bits_limit is None or bits_checked < bits_limit):
                    if key not in frame_cache:
                        frame_cache[key] = load_vus_frame_by_header(UTIG / vfile, key)
                    fr = frame_cache[key]
                    mism = -1
                    bits = None
                    pad_mode = "safe"
                    if fr is not None:
                        try:
                            vb = make_bit_stream(fr)[648 : 648 + 2048]
                            bits, mism, pad_mode = map_unscramble_best_vs_ref(
                                hs,
                                loc.halfword_offset,
                                vb,
                                record_halfwords=loc.record_halfwords,
                                trailing_all_ones=loc.trailing_all_ones,
                            )
                        except Exception:
                            mism = -2
                    if mism != 0 and nloc > 1 and bits is not None:
                        # Rare: multiple VUS occurrences of this header --
                        # check whether a distinct-content duplicate
                        # elsewhere is the true bit-exact match instead of
                        # the arbitrary primary-file one (item 23).
                        for fr_alt in load_all_distinct_vus_frames_by_header(key):
                            vb_alt = make_bit_stream(fr_alt)[648 : 648 + 2048]
                            _b, m_alt, mode_alt = map_unscramble_best_vs_ref(
                                hs,
                                loc.halfword_offset,
                                vb_alt,
                                record_halfwords=loc.record_halfwords,
                                trailing_all_ones=loc.trailing_all_ones,
                            )
                            if m_alt == 0:
                                mism = 0
                                pad_mode = mode_alt
                                break
                    bits_checked += 1
                    if mism == 0:
                        bit_ok += 1
                        if pad_mode == "force_n1":
                            pad_force_n1_rescues += 1
                    else:
                        bit_fail += 1
                        if len(bit_fail_sample) < 80:
                            bit_fail_sample.append(
                                {
                                    "file": name,
                                    "vus_file": vfile,
                                    "base": loc.halfword_offset,
                                    "year": year,
                                    "doy": doy,
                                    "matv": matv,
                                    "mism": mism,
                                    "pad_mode": pad_mode,
                                }
                            )

            per_file_bases[name] = n_base
            per_file_matched[name] = n_match
            print(
                f"  SEISF {name}: bases={n_base} matched={n_match} "
                f"only={n_base - n_match} "
                f"bits={bit_ok}/{bits_checked} "
                f"elapsed={time.time() - t1:.1f}s",
                flush=True,
            )

    print("=== VUS-only (unique headers not seen on SEISF) ===", flush=True)
    vus_only_by_file: Counter = Counter()
    vus_only_instances = 0
    n_vus_only_unique = 0
    vus_only_sample: List[Dict[str, Any]] = []
    with OUT_VUS_ONLY.open("w", encoding="utf-8") as vf:
        for key, (vfile, nloc) in vus_index.items():
            if key in seisf_keys:
                continue
            n_vus_only_unique += 1
            vus_only_by_file[vfile] += 1
            vus_only_instances += nloc
            if n_vus_only_unique <= 200 or n_vus_only_unique % 2000 == 0:
                y, d = hdr_year_doy(key)
                rec = {"file": vfile, "year": y, "doy": d, "n_locs": nloc}
                vf.write(json.dumps(rec) + "\n")
                if len(vus_only_sample) < 120:
                    vus_only_sample.append(rec)

    n_bases = sum(per_file_bases.values())
    n_unique_seisf = len(seisf_keys)
    n_vus_unique = vus_stats["unique_headers"]
    n_vus_covered_unique = n_vus_unique - n_vus_only_unique
    # unique SEISF headers that matched
    # approximate: unique SEISF that are in both sets
    n_both_unique = sum(1 for k in seisf_keys if k in vus_index)

    summary = {
        "match_definition": "identical 108-byte engineering header",
        "n_seisf_bases": n_bases,
        "n_seisf_unique_headers": n_unique_seisf,
        "n_seisf_extra_bases_same_header": seisf_dup_headers,
        "n_seisf_bases_matched": n_matched,
        "n_seisf_bases_only": n_seisf_only,
        "n_unique_headers_in_both": n_both_unique,
        "n_vus_frames": vus_stats["total_frames"],
        "n_vus_unique_headers": n_vus_unique,
        "n_vus_unique_only": n_vus_only_unique,
        "n_vus_frame_instances_only": vus_only_instances,
        "n_vus_unique_covered": n_vus_covered_unique,
        "pct_seisf_bases_matched": round(100.0 * n_matched / max(1, n_bases), 3),
        "pct_vus_unique_covered": round(100.0 * n_vus_covered_unique / max(1, n_vus_unique), 3),
        "production_eligible_matched_approx": production_matched,
        "matv_oor_matched": matv_oor,
        "n_matched_bases_with_duplicate_vus_header": n_multi_vus,
        "bits_checked": bits_checked,
        "bits_zero": bit_ok,
        "bits_nonzero": bit_fail,
        "pad_force_n1_rescues": pad_force_n1_rescues,
        "per_file_bases": dict(sorted(per_file_bases.items())),
        "per_file_matched": dict(sorted(per_file_matched.items())),
        "seisf_only_by_file": {
            f: per_file_bases[f] - per_file_matched[f] for f in sorted(per_file_bases)
            if per_file_bases[f] - per_file_matched[f] > 0
        },
        "vus_only_by_file": dict(sorted(vus_only_by_file.items())),
        "matched_by_vus_file": dict(sorted(matched_by_vus_file.items())),
        "seisf_only_sample": seisf_only_sample[:80],
        "vus_only_sample": vus_only_sample[:80],
        "bit_fail_sample": bit_fail_sample,
        "artifacts": {
            "seisf_only_jsonl": str(OUT_SEISF_ONLY.relative_to(ROOT)),
            "vus_only_sample_jsonl": str(OUT_VUS_ONLY.relative_to(ROOT)),
        },
    }

    payload = {"vus_stats": vus_stats, "summary": summary}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}", flush=True)

    # Markdown report
    lines = [
        "# Dual-archive coverage report (SEISF × VUS)",
        "",
        "Match key: **byte-identical 108-byte engineering header**.",
        "",
        "## Headline counts",
        "",
        "| Quantity | Count |",
        "|----------|------:|",
        f"| SEISF frame bases | {n_bases} |",
        f"| SEISF unique headers | {n_unique_seisf} |",
        f"| SEISF bases with VUS twin | {n_matched} (**{summary['pct_seisf_bases_matched']}%**) |",
        f"| SEISF bases without VUS | {n_seisf_only} |",
        f"| Unique headers in both | {n_both_unique} |",
        f"| VUS frame slots | {vus_stats['total_frames']} |",
        f"| VUS unique headers | {n_vus_unique} |",
        f"| VUS unique with SEISF twin | {n_vus_covered_unique} (**{summary['pct_vus_unique_covered']}%**) |",
        f"| VUS unique without SEISF | {n_vus_only_unique} |",
        f"| VUS frame instances without SEISF | {vus_only_instances} |",
        f"| Matched but matv∉(0,503) | {matv_oor} |",
        "",
    ]
    if bits_checked:
        lines += [
            "## Science-bit checks (production-eligible subset)",
            "",
            f"- Checked: **{bits_checked}**",
            f"- R=0: **{bit_ok}**",
            f"- R≠0 or error: **{bit_fail}**",
            f"- R=0 only via n=1 trailing-0o777777 VUS-oracle strip: "
            f"**{pad_force_n1_rescues}**",
            "",
        ]
        if bit_fail_sample:
            lines.append("### Fail samples")
            lines.append("")
            for e in bit_fail_sample[:40]:
                lines.append(
                    f"- {e['file']}→{e['vus_file']} {e['year']}-{e['doy']} "
                    f"base={e['base']} R={e['mism']} matv={e['matv']}"
                )
            lines.append("")

    lines += ["## SEISF-only bases by file", "", "| file | only | bases | matched |", "|------|-----:|------:|--------:|"]
    for f in sorted(per_file_bases):
        o = per_file_bases[f] - per_file_matched[f]
        if o or per_file_bases[f]:
            lines.append(f"| {f} | {o} | {per_file_bases[f]} | {per_file_matched[f]} |")
    lines += [
        "",
        "## VUS-only unique headers by file",
        "",
        "| file | unique headers w/o SEISF |",
        "|------|-------------------------:|",
    ]
    for f, c in sorted(vus_only_by_file.items()):
        lines.append(f"| {f} | {c} |")
    lines += [
        "",
        "## Note on late SEISF reels (vkg.27+)",
        "",
        "Some late DLT files yield few/zero frame bases under `find_seisf_frame_bases` "
        "(year/DOY heuristic); those may still contain non-standard content or damaged geometry—"
        "bases=0 does not alone prove empty media.",
        "",
        f"Full SEISF-only list: `{OUT_SEISF_ONLY.name}`",
        f"VUS-only samples: `{OUT_VUS_ONLY.name}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}", flush=True)

    print("\n=== HEADLINE ===", flush=True)
    print(
        f"SEISF bases matched: {n_matched}/{n_bases} ({summary['pct_seisf_bases_matched']}%)",
        flush=True,
    )
    print(
        f"VUS unique covered: {n_vus_covered_unique}/{n_vus_unique} "
        f"({summary['pct_vus_unique_covered']}%)",
        flush=True,
    )
    print(
        f"SEISF-only bases: {n_seisf_only}; VUS-only unique: {n_vus_only_unique}",
        flush=True,
    )
    if bits_checked:
        print(f"Bits R=0: {bit_ok}/{bits_checked}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
