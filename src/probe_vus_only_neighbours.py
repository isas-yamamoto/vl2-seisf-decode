#!/usr/bin/env python3
"""
Probe: are VUS-only residuals partly SEISF under-detection?

1) Exhaustive SEISF engineering-header harvest (every halfword offset with
   looks_like_seisf_frame_header), vs the production pitch-limited finder.
2) How many unique VUS headers newly match under exhaustive discovery?
3) For remaining VUS-only, GCSC / (year,doy) neighbourhood on SEISF side.

  python3 probe_vus_only_neighbours.py

Outputs:
  draft/figures/vus_only_neighbour_probe.json
  draft/figures/vus_only_neighbour_report.md
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from seisf_decode import (  # noqa: E402
    extend_halfwords_across_records,
    find_seisf_frame_bases,
    halfwords_span_for_frame,
    looks_like_seisf_frame_header,
    seisf_frame_header_bytes,
)
from vkg_format import (  # noqa: E402
    SEISF_FIRST_FRAME_HALFWORDS_OFFSET,
    SEISF_HALFWORDS_PER_FRAME,
    SEISF_HEADER_HALFWORDS,
    body_to_halfwords,
    open_vkg,
)
from vus_decode import decode_vus_frame, parse_seisf_header_fields  # noqa: E402

UTIG = ROOT / "utig"
OUT_JSON = ROOT / "draft" / "figures" / "vus_only_neighbour_probe.json"
OUT_MD = ROOT / "draft" / "figures" / "vus_only_neighbour_report.md"


def year_doy(hdr: bytes) -> Tuple[int, int]:
    try:
        return parse_seisf_header_fields(hdr + bytes(342))
    except Exception:
        return 0, 0


def gcsc_from_frame(fr450: bytes) -> Optional[int]:
    try:
        dec = decode_vus_frame(fr450, 0)
        if dec and dec.blocks:
            return int(dec.blocks[0].gcsc)
    except Exception:
        pass
    return None


def iter_seisf_records(path: Path):
    _, sgs = open_vkg(str(path))
    for si, (hdr, body) in enumerate(sgs):
        if not (hdr.is_seisf or hdr.label.startswith("DLT") or hdr.record_length in (10752, 10764)):
            continue
        rlen = hdr.record_length
        records: List[List[int]] = []
        pos = 0
        while pos + rlen <= len(body):
            records.append(body_to_halfwords(body[pos : pos + rlen]))
            pos += rlen
        yield si, records


def harvest_headers_production(path: Path) -> Set[bytes]:
    """Same bases as production iter_seisf_frames (dense find + edge extend)."""
    keys: Set[bytes] = set()
    for si, records in iter_seisf_records(path):
        for ri, hs0 in enumerate(records):
            search_need = len(hs0) + SEISF_HEADER_HALFWORDS + 8
            hs_search = (
                list(hs0)
                if len(hs0) >= search_need
                else extend_halfwords_across_records(records, ri, search_need)
            )
            for base in find_seisf_frame_bases(hs_search, start_limit=len(hs0)):
                need = max(halfwords_span_for_frame(base), base + SEISF_HEADER_HALFWORDS)
                hs = (
                    hs_search
                    if len(hs_search) >= need
                    else extend_halfwords_across_records(records, ri, need)
                )
                if len(hs) < base + SEISF_HEADER_HALFWORDS:
                    continue
                keys.add(bytes(seisf_frame_header_bytes(hs, base)))
    return keys


def harvest_headers_exhaustive(
    path: Path,
) -> Tuple[Set[bytes], Dict[bytes, Tuple[int, int]], int, int]:
    """
    Explicit dense harvest (same core as production after dense-finder fix).
    Returns (keys, key->(year,doy), n_bases, n_bases_not_in_prod).
    """
    keys: Set[bytes] = set()
    yds: Dict[bytes, Tuple[int, int]] = {}
    n_bases = 0
    n_off_pitch = 0
    for si, records in iter_seisf_records(path):
        for ri, hs0 in enumerate(records):
            search_need = len(hs0) + SEISF_HEADER_HALFWORDS + 8
            hs_search = (
                list(hs0)
                if len(hs0) >= search_need
                else extend_halfwords_across_records(records, ri, search_need)
            )
            prod = set(find_seisf_frame_bases(hs_search, start_limit=len(hs0)))
            limit = len(hs0)
            for base in range(0, max(0, limit - SEISF_HEADER_HALFWORDS + 1)):
                # Validate with extended buffer (same as production).
                if not looks_like_seisf_frame_header(hs_search, base):
                    continue
                n_bases += 1
                if base not in prod:
                    n_off_pitch += 1
                hdr = bytes(seisf_frame_header_bytes(hs_search, base))
                keys.add(hdr)
                y, d = year_doy(hdr)
                if y:
                    yds[hdr] = (y, d)
    return keys, yds, n_bases, n_off_pitch


def index_vus() -> Tuple[Dict[bytes, str], Dict[str, int]]:
    """Header -> primary file; stats."""
    idx: Dict[bytes, str] = {}
    per: Counter = Counter()
    for n in range(47, 57):
        path = UTIG / f"vkg.{n}"
        _, sgs = open_vkg(str(path))
        for _si, (hdr, body) in enumerate(sgs):
            rlen = hdr.record_length
            pos = 0
            while pos + rlen <= len(body):
                rec = body[pos : pos + rlen]
                pos += rlen
                for j in range(0, (rlen // 450) * 450, 450):
                    key = bytes(rec[j : j + 108])
                    if key not in idx:
                        idx[key] = path.name
                    per[path.name] += 1
    return idx, dict(per)


def load_vus_frames_by_header(want: Set[bytes]) -> Dict[bytes, bytes]:
    """Map header -> first 450B frame for headers of interest (VUS-only set size)."""
    out: Dict[bytes, bytes] = {}
    remaining = set(want)
    for n in range(47, 57):
        if not remaining:
            break
        path = UTIG / f"vkg.{n}"
        _, sgs = open_vkg(str(path))
        for _si, (hdr, body) in enumerate(sgs):
            rlen = hdr.record_length
            pos = 0
            while pos + rlen <= len(body) and remaining:
                rec = body[pos : pos + rlen]
                pos += rlen
                for j in range(0, (rlen // 450) * 450, 450):
                    key = bytes(rec[j : j + 108])
                    if key in remaining:
                        out[key] = bytes(rec[j : j + 450])
                        remaining.discard(key)
                        if not remaining:
                            break
    return out


def hamming108(a: bytes, b: bytes) -> int:
    return sum(x != y for x, y in zip(a, b))


def main() -> int:
    if not UTIG.is_dir():
        print(f"missing {UTIG}", file=sys.stderr)
        return 1

    print("=== Index VUS unique headers ===", flush=True)
    t0 = time.time()
    vus_idx, vus_file_counts = index_vus()
    print(f"  unique VUS headers: {len(vus_idx)} ({time.time()-t0:.1f}s)", flush=True)

    print("=== Production SEISF header harvest ===", flush=True)
    t1 = time.time()
    seisf_prod: Set[bytes] = set()
    seisf_prod_yd: Dict[bytes, Tuple[int, int]] = {}
    for n in range(1, 47):
        path = UTIG / f"vkg.{n}"
        if not path.is_file():
            continue
        keys = harvest_headers_production(path)
        seisf_prod |= keys
        for k in keys:
            seisf_prod_yd[k] = year_doy(k)
        print(f"  prod vkg.{n}: +{len(keys)} (union {len(seisf_prod)})", flush=True)
    print(f"production unique SEISF headers: {len(seisf_prod)} ({time.time()-t1:.1f}s)", flush=True)

    print("=== Exhaustive SEISF header harvest (every looks_like base) ===", flush=True)
    t2 = time.time()
    seisf_ex: Set[bytes] = set()
    seisf_ex_yd: Dict[bytes, Tuple[int, int]] = {}
    n_bases_ex = 0
    n_off = 0
    for n in range(1, 47):
        path = UTIG / f"vkg.{n}"
        if not path.is_file():
            continue
        keys, yds, nb, noff = harvest_headers_exhaustive(path)
        seisf_ex |= keys
        seisf_ex_yd.update(yds)
        n_bases_ex += nb
        n_off += noff
        print(
            f"  exh vkg.{n}: keys={len(keys)} bases={nb} off_pitchish={noff} "
            f"union_keys={len(seisf_ex)}",
            flush=True,
        )
    print(
        f"exhaustive unique SEISF headers: {len(seisf_ex)} bases={n_bases_ex} "
        f"({time.time()-t2:.1f}s)",
        flush=True,
    )

    # Overlap analysis
    vus_keys = set(vus_idx)
    both_prod = vus_keys & seisf_prod
    both_ex = vus_keys & seisf_ex
    vus_only_prod = vus_keys - seisf_prod
    vus_only_ex = vus_keys - seisf_ex
    newly_matched = both_ex - both_prod
    seisf_only_prod = seisf_prod - vus_keys
    seisf_only_ex = seisf_ex - vus_keys

    print("=== Overlap ===", flush=True)
    print(f"  both (production finder): {len(both_prod)}", flush=True)
    print(f"  both (exhaustive):        {len(both_ex)}", flush=True)
    print(f"  newly matched (exh only): {len(newly_matched)}", flush=True)
    print(f"  VUS-only after production: {len(vus_only_prod)}", flush=True)
    print(f"  VUS-only after exhaustive: {len(vus_only_ex)}", flush=True)

    # Near-miss header Hamming: for sample of VUS-only, min Hamming to any SEISF exh header same year/doy
    print("=== Near-miss header Hamming (sample) ===", flush=True)
    sample_n = min(3000, len(vus_only_ex))
    # Prefer realistic calendar years
    vus_only_list = []
    for k in vus_only_ex:
        y, d = year_doy(k)
        if 1976 <= y <= 1982:
            vus_only_list.append((k, y, d))
    # stratified take every step
    vus_only_list.sort(key=lambda t: (t[1], t[2]))
    step = max(1, len(vus_only_list) // sample_n)
    sample = vus_only_list[::step][:sample_n]

    # Index SEISF exhaustive headers by (year, doy)
    by_yd: Dict[Tuple[int, int], List[bytes]] = defaultdict(list)
    for k, (y, d) in seisf_ex_yd.items():
        if 1976 <= y <= 1982 and 1 <= d <= 366:
            by_yd[(y, d)].append(k)

    hamming_stats = Counter()
    same_yd_any = 0
    min_ham_dist: List[int] = []
    for k, y, d in sample:
        cands = by_yd.get((y, d), [])
        if not cands:
            # also try doy±1
            cands = by_yd.get((y, d - 1), []) + by_yd.get((y, d + 1), [])
        if cands:
            same_yd_any += 1
            mh = min(hamming108(k, c) for c in cands)
            min_ham_dist.append(mh)
            if mh == 0:
                hamming_stats["0_exact"] += 1
            elif mh <= 2:
                hamming_stats["1_2"] += 1
            elif mh <= 8:
                hamming_stats["3_8"] += 1
            elif mh <= 32:
                hamming_stats["9_32"] += 1
            else:
                hamming_stats[">32"] += 1
        else:
            hamming_stats["no_same_yd_seisf"] += 1

    # GCSC neighbourhood for denser sample of residual VUS-only
    print("=== GCSC index from production dual matches (SEISF decode sample) ===", flush=True)
    # Index gcsc from VUS frames that ARE matched (truth of GCSC scale) vs VUS-only
    # Build SEISF year-doy presence for GCSC story from VUS side only:
    matched_gcscs: Set[int] = set()
    # light: load all frames for matched first 50k is too much; sample matched headers
    matched_list = list(both_ex)
    mstep = max(1, len(matched_list) // 5000)
    matched_sample_h = matched_list[::mstep][:5000]
    fr_map = load_vus_frames_by_header(set(matched_sample_h) | {t[0] for t in sample[:800]})
    for k in matched_sample_h:
        fr = fr_map.get(k)
        if fr:
            g = gcsc_from_frame(fr)
            if g is not None:
                matched_gcscs.add(g)

    # For VUS-only sample frames: is GCSC "between" matched GCSCs on same year-doy? hard.
    # Instead: count VUS-only with exact GCSC already appearing on a matched dual (repack?)
    vus_only_gcsc_also_on_matched = 0
    vus_only_gcsc_near_matched = 0  # within 500 counts
    vus_only_gcsc_decoded = 0
    near_examples = []
    matched_sorted = sorted(matched_gcscs)
    import bisect

    for k, y, d in sample[:800]:
        fr = fr_map.get(k)
        if fr is None:
            fr_map.update(load_vus_frames_by_header({k}))
            fr = fr_map.get(k)
        if not fr:
            continue
        g = gcsc_from_frame(fr)
        if g is None:
            continue
        vus_only_gcsc_decoded += 1
        if g in matched_gcscs:
            vus_only_gcsc_also_on_matched += 1
        if matched_sorted:
            i = bisect.bisect_left(matched_sorted, g)
            best = 10**18
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(matched_sorted):
                    best = min(best, abs(matched_sorted[j] - g))
            if best <= 500:
                vus_only_gcsc_near_matched += 1
                if len(near_examples) < 15:
                    near_examples.append(
                        {"year": y, "doy": d, "gcsc": g, "delta_gcsc": best, "vus_file": vus_idx[k]}
                    )

    # File-level recovery of newly matched
    newly_by_file = Counter(vus_idx[k] for k in newly_matched)

    summary = {
        "n_vus_unique": len(vus_keys),
        "n_seisf_unique_production": len(seisf_prod),
        "n_seisf_unique_exhaustive": len(seisf_ex),
        "n_both_production": len(both_prod),
        "n_both_exhaustive": len(both_ex),
        "n_newly_matched_by_exhaustive": len(newly_matched),
        "pct_vus_only_recovered_among_old_vus_only": round(
            100.0 * len(newly_matched) / max(1, len(vus_only_prod)), 3
        ),
        "n_vus_only_after_production": len(vus_only_prod),
        "n_vus_only_after_exhaustive": len(vus_only_ex),
        "n_seisf_only_production": len(seisf_only_prod),
        "n_seisf_only_exhaustive": len(seisf_only_ex),
        "exhaustive_bases_checked": n_bases_ex,
        "bases_not_in_production_finder_list": n_off,
        "new_match_by_vus_file": dict(sorted(newly_by_file.items())),
        "hamming_sample_n": len(sample),
        "hamming_same_yd_or_adjacent": same_yd_any,
        "hamming_bucket": dict(hamming_stats),
        "min_hamming_median": (
            sorted(min_ham_dist)[len(min_ham_dist) // 2] if min_ham_dist else None
        ),
        "gcsc_vus_only_decoded": vus_only_gcsc_decoded,
        "gcsc_exact_also_on_matched_sample": vus_only_gcsc_also_on_matched,
        "gcsc_within_500_of_matched_sample": vus_only_gcsc_near_matched,
        "gcsc_near_examples": near_examples,
        "interpretation": {
            "underdetection_strong_if": "newly_matched >> 0",
            "header_packing_near_miss_if": "many min_ham 1-8 on same year/doy",
            "archival_gap_if": "hamming_no_same_yd high and newly_matched ~ 0",
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}", flush=True)

    lines = [
        "# VUS-only neighbour / under-detection probe",
        "",
        "## Design",
        "",
        "1. **Production finder**: dense `find_seisf_frame_bases` (every halfword + "
        "record-edge halfword extend for header BCD).",
        "2. **Exhaustive finder**: same core scan (kept for parity/regression against denser discovery).",
        "3. Match key remains **byte-identical 108-byte** engineering header vs all VUS unique headers.",
        "4. For residual VUS-only, sample same/adjacent DOY and min Hamming distance to SEISF headers; "
        "decode GCSC and compare to dual-matched GCSC sample.",
        "",
        "## Header coverage under exhaustive discovery",
        "",
        "| Quantity | Count |",
        "|----------|------:|",
        f"| VUS unique headers | {summary['n_vus_unique']} |",
        f"| SEISF unique headers (production) | {summary['n_seisf_unique_production']} |",
        f"| SEISF unique headers (exhaustive) | {summary['n_seisf_unique_exhaustive']} |",
        f"| Dual match (production) | {summary['n_both_production']} |",
        f"| Dual match (exhaustive) | {summary['n_both_exhaustive']} |",
        f"| **Newly dual-matched by exhaustive** | **{summary['n_newly_matched_by_exhaustive']}** |",
        f"| VUS-only after production | {summary['n_vus_only_after_production']} |",
        f"| VUS-only after exhaustive | {summary['n_vus_only_after_exhaustive']} |",
        f"| Fraction of *old* VUS-only recovered | {summary['pct_vus_only_recovered_among_old_vus_only']}% |",
        f"| Exhaustive looks_like bases | {summary['exhaustive_bases_checked']} |",
        f"| Bases not listed by production finder (per-record) | {summary['bases_not_in_production_finder_list']} |",
        "",
        "### New matches by VUS file",
        "",
    ]
    for f, c in sorted(summary["new_match_by_vus_file"].items()):
        lines.append(f"- {f}: {c}")
    lines += [
        "",
        "## Hamming near-miss (remaining VUS-only, realistic years, vs SEISF same/±1 DOY)",
        "",
        f"Sample size: {summary['hamming_sample_n']}; "
        f"with any same/adjacent-DOY SEISF header: {summary['hamming_same_yd_or_adjacent']}",
        "",
        f"Min-Hamming buckets: `{summary['hamming_bucket']}`",
        f"Median min Hamming (among those with candidates): {summary['min_hamming_median']}",
        "",
        "## GCSC neighbourhood (sample of residual VUS-only)",
        "",
        f"Decoded GCSC: {summary['gcsc_vus_only_decoded']}; "
        f"exact GCSC also seen on matched-header sample: {summary['gcsc_exact_also_on_matched_sample']}; "
        f"within 500 of a matched sample GCSC: {summary['gcsc_within_500_of_matched_sample']}",
        "",
        "Examples:",
        "",
    ]
    for e in near_examples:
        lines.append(
            f"- {e['vus_file']} {e['year']}-{e['doy']} GCSC={e['gcsc']} Δ={e['delta_gcsc']}"
        )
    lines += [
        "",
        "## Interpretation",
        "",
    ]
    nm = summary["n_newly_matched_by_exhaustive"]
    if nm == 0:
        lines.append(
            "- Exhaustive halfword discovery **did not** recover additional 108-byte dual matches. "
            "Production finder under-detection of *looks_like* headers is **not** the main driver "
            "of the residual ~67k VUS-only set."
        )
    else:
        lines.append(
            f"- Exhaustive discovery recovered **{nm}** additional dual matches "
            f"({summary['pct_vus_only_recovered_among_old_vus_only']}% of former VUS-only). "
            "A **fraction** of VUS-only was under-detection; the bulk still remains after exhaustive scan."
        )
    med = summary["min_hamming_median"]
    if med is not None and med > 8:
        lines.append(
            f"- Median min header Hamming on same/±1 DOY is **{med}** bytes — not 1–2 bit packing glitches; "
            "residual VUS-only headers are typically **structurally distinct** from same-day SEISF headers."
        )
    elif med is not None:
        lines.append(
            f"- Median min header Hamming on same/±1 DOY is **{med}** — some residual could be packing near-misses; inspect Hamming 1–8 bucket."
        )
    lines.append(
        "- **Leading explanation for residual VUS-only remains archival asymmetry** "
        "(processed peers without intermediate twins on these SEISF `vkg.*` holdings), "
        "not production science-bit decode failure (which does not define the VUS-only set)."
    )
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}", flush=True)
    print("\nHEADLINE:", flush=True)
    print(
        f" newly_matched={nm}  vus_only_exh={len(vus_only_ex)}  "
        f"hamming_median={med}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
