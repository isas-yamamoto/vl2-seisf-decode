# Viking Lander 2 SEISF cassette decoder (Path D)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Recover **bit-exact** 2048-bit science frames from scrambled **SEISF (DLT)** UTIG cassettes (`vkg.1`–`46`), validated against matched **VUS (USEIS)** frames (`vkg.47`–`56`).

**Organization:** [isas-yamamoto](https://github.com/isas-yamamoto) · **License:** MIT  
**Recommended remote:** `https://github.com/isas-yamamoto/viking-vl2-seisf-decode`

## Path D (summary)

1. Pack consecutive 18-bit halfwords as 36-bit pairs; **drop the top 4 bits** → 32 bits/pair
2. Stream offset **15**, length 2048
3. Unscramble with PD7400072 order using **Q = matv** (MAP probe)
4. Stitch halfwords across physical record boundaries when needed

Gold check (local `utig/vkg.1` + `vkg.47`): residual **0/2048**, frame equality, GCSC **125078**.

## Quick start

```bash
mkdir -p utig && cp /path/to/vkg.1 /path/to/vkg.47 utig/

cd src
python3 test_regression.py
python3 decode_vkg.py ../utig/vkg.1 --summary --max-frames 20
```

Python 3.9+, standard library only. Cassette images are **not** shipped.

## Layout

| Path | Contents |
|------|----------|
| `src/` | Decoder, CLI, regression tests |
| `vusinfo/` | Original VUS C decoder (Yukio Yamamoto), first-party |
| `materials/` | Curated PDFs + `N51SUB.jpg` |
| `draft/` | English manuscript outline (AI-venue framing) |
| `docs/` | Release notes and usage |

## Cite / materials

- `CITATION.cff`
- Provenance: `NOTICE` (UTIG web PDFs; N51SUB photo from paper at UTIG)
- License: `LICENSE` (MIT for software)

## Paper draft

`draft/manuscript.md` — English, AI-assisted reverse engineering + dual-archive ground truth.
