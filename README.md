# Viking Lander 2 SEISF cassette decoder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Recover **bit-exact** 2048-bit science frames from scrambled **SEISF (DLT)** UTIG cassettes (`vkg.1`–`29`; `vkg.30`–`46` in the same holding are a separate meteorology instrument product, out of scope), validated against matched **VUS (USEIS)** frames (`vkg.47`–`56`).

**Organization:** [isas-yamamoto](https://github.com/isas-yamamoto) · **License:** MIT  
**Repository:** `https://github.com/isas-yamamoto/vl2-seisf-decode`

## Decode pipeline (summary)

1. Pack consecutive 18-bit halfwords as 36-bit pairs; **drop the top 4 bits** → 32 bits/pair
2. Stream offset **15**, length 2048
3. Unscramble with PD7400072 order using **Q = matv** (MAP probe), covering all three page-readout cases (Q < 503, Q = 503, Q > 503)
4. Stitch halfwords across physical record boundaries when needed, dropping the fixed-length leader a record carries when its length is not an exact multiple of the 224-halfword frame stride

`matv` is read from a 512-entry lookup table (an N51SUB "MAP" routine) indexed by a 9-bit field taken from the first two science halfwords; it is used directly as the page pointer Q above (docs/usage.md has the per-case segment-length formulas).

Gold check (local `utig/vkg.1` + `vkg.47`): residual **0/2048**, frame equality, GCSC **125078**.

Archive-wide bit-exact failure rates: **0.08%** for matv < 503, **0.13%** for matv = 503, and **0.11%** for matv > 503 — all three page-readout cases essentially equally reliable (see docs/usage.md for the small residual that remains). VUS-unique-header coverage is **99.0%**; the SEISF-side matched fraction is **79.0%**, reflecting SEISF's 29-file span (`vkg.1`–`vkg.29`) vs. VUS's 10 (`vkg.47`–`vkg.56`).

## Quick start

```bash
mkdir -p utig && cp /path/to/vkg.1 /path/to/vkg.47 utig/

# Required regression gate (needs utig/vkg.1 and vkg.47)
python3 tests/test_regression.py

# Decode
python3 src/decode_vkg.py utig/vkg.1 --summary --max-frames 20
```

Python 3.9+, standard library only. Cassette images are **not** shipped.

## Layout

| Path | Contents |
|------|----------|
| `src/` | Production decoder + CLI (`decode_vkg.py`) |
| `tests/` | Required regression gates (`test_regression.py`, `validate_gold.py`) |
| `tools/` | Optional full-archive inventory / probes (writes under `out/`) |
| `legacy/vusinfo/` | Historical C reader for **VUS** frames (`vusinfo`); kept for cross-check with `src/vus_decode.py` |
| `materials/` | Curated PDFs + `N51SUB.jpg` |
| `docs/` | Operator docs + **format diagrams** (`docs/figures/`) |

## Data

`vkg.1`–`vkg.56` are archived at DARTS (ISAS/JAXA): https://data.darts.isas.jaxa.jp/pub/viking/utig/

## Format diagrams

| | |
|--|--|
| SEISF / DLT | ![SEISF layout](docs/figures/fig_seisf_format.png) |
| VUS / USEIS | ![VUS layout](docs/figures/fig_vus_format.png) |
| Dual-archive map | ![SEISF–VUS bridge](docs/figures/fig_seisf_vus_bridge.png) |

Details: [docs/figures/README.md](docs/figures/README.md)

## Documentation

- English: [docs/usage.md](docs/usage.md)
- N51SUB technical notes (MAP/SET/SEISDT, not in the paper): [docs/n51sub.md](docs/n51sub.md)

## Cite / materials

- `CITATION.cff`
- Provenance: `NOTICE` (UTIG web PDFs; N51SUB photo from paper at UTIG)
- License: `LICENSE` (MIT for software)

A scholarly paper draft, if any, is maintained in a **separate repository**, not here.
