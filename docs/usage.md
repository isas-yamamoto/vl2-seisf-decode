# Usage — Viking Lander 2 (`utig/vkg.*`) decode

Paths below assume the published layout (`src/` next to `docs/`). For the local Viking workspace decoder, use `cursor/` instead of `src/`.

```bash
cd src   # or: cd cursor
```

Python 3.9+, standard library only.

---

## Data types

| Files | Label | Meaning |
|-------|--------|---------|
| `../utig/vkg.1`–`vkg.46` | `DLT…` | **SEISF** (scrambled). Main target of this package |
| `../utig/vkg.47`–`vkg.56` | `VUS…` | **VUS / USEIS** (unscrambled). Same layout as `vusinfo` |

Both tape families share one CLI. Type is detected from the leading subgroup header, not the file extension.

Japanese version: [usage.ja.md](usage.ja.md)

## Cassette / frame formats

| Diagram | File |
|---------|------|
| SEISF / DLT | [figures/fig_seisf_format.png](figures/fig_seisf_format.png) |
| VUS / USEIS | [figures/fig_vus_format.png](figures/fig_vus_format.png) |
| SEISF → Path D → VUS | [figures/fig_seisf_vus_bridge.png](figures/fig_seisf_vus_bridge.png) |

![SEISF layout](figures/fig_seisf_format.png)

![VUS layout](figures/fig_vus_format.png)

![Path D dual-archive](figures/fig_seisf_vus_bridge.png)

Index: [figures/README.md](figures/README.md). PDF/SVG siblings for each basename.

---

## Source files

| File | Role |
|------|------|
| `decode_vkg.py` | CLI entry point |
| `vkg_format.py` | Cassette / record layout |
| `vus_decode.py` | VUS science bitstream decode |
| `seisf_decode.py` | SEISF + Path D (pair36 / Q=matv / off=15) |
| `validate_gold.py` | Gold-frame diagnostics + hard asserts |
| `test_regression.py` | Fixed regression suite (unittest) |

---

## Regression checks (fixed)

With `../utig/vkg.1` and `../utig/vkg.47` present:

```bash
# Full suite (gold frame, multi-frame, boundary, VUS)
python3 test_regression.py

# Gold frame only: diagnostics + asserts
python3 validate_gold.py

# Verbose unittest
python3 -m unittest test_regression -v
```

Exit **0 = PASS**, **1 = FAIL** (missing data also exits 1).

| Check | Expectation |
|-------|-------------|
| Path D constants | `bit_offset=15`, drop `(0,1,2,3)`, `Q=matv` |
| Gold f0 (`base=170`) | GCSC=125078, science **0 residual**, 450 B **frame_eq** |
| Amplitudes | First 6 X/Y/Z samples match VUS |
| Header-matched frames on record 0 | All Path D targets **2048/2048** |
| `base=3530` | Record boundary + lookahead → **2048/2048** |
| VUS `vkg.47` f0 | NORMAL / n=83 / GCSC=125078 |

---

## Commands

### 1. File structure

Subgroup count, labels, record length, SEISF year/DOY range:

```bash
python3 decode_vkg.py ../utig/vkg.1 --info
python3 decode_vkg.py ../utig/vkg.47 --info
```

### 2. Frame summary (year, DOY, GCSC, mode)

```bash
# SEISF (first 20 frames)
python3 decode_vkg.py ../utig/vkg.1 --summary --max-frames 20

# VUS (similar to vusinfo -f)
python3 decode_vkg.py ../utig/vkg.47 --summary --max-frames 20
```

Example (VUS):

```
frame=    0 year=1976 doy=249 gcsc=  125078 mode=NORMAL n= 83 chg=255 note=
```

- `note=seisf+unscr` — SEISF read via MAP/UNSCR  
- `note=seisf-raw` — with `--raw` (no unscramble)

### 3. Amplitude samples

Default mode when no other output flags are set. Use `--max-frames` to bound work.

```bash
python3 decode_vkg.py ../utig/vkg.1 --samples --max-frames 3 --limit-per-block 20
python3 decode_vkg.py ../utig/vkg.47 --samples --max-frames 1 --limit-per-block 30
```

- NORMAL / HIGH: `sample  amp_x  amp_y  amp_z`
- EVENT: axis-crossing counts follow each axis block

### 4. CSV export

```bash
python3 decode_vkg.py ../utig/vkg.1 --csv out_vkg1.csv --max-frames 5
python3 decode_vkg.py ../utig/vkg.47 --csv out_vkg47.csv --max-frames 10
```

Columns: `frame, block, year, doy, gcsc, mode, sample, amp_x, amp_y, amp_z, axis_x, axis_y, axis_z, note`

### 5. Skip SEISF MAP (debug)

Header structure only, or pack bits into VUS-shaped fields without unscramble:

```bash
python3 decode_vkg.py ../utig/vkg.1 --raw --summary --max-frames 5
```

---

## Options

| Option | Description |
|--------|-------------|
| `vkg` (positional) | Path to `vkg.N` |
| `--info` | Cassette subgroup structure only |
| `--summary` | One-line year / DOY / GCSC / mode |
| `--samples` | Print amplitudes (default if no other mode) |
| `--csv PATH` | Write samples to CSV |
| `--max-frames N` | Process only the first N frames. **If omitted, all frames** |
| `--limit-per-block N` | With `--samples`, samples shown per block (default 20) |
| `--raw` | SEISF only: skip MAP/UNSCR |

---

## C decoder (VUS)

Unscrambled VUS can also be checked with the bundled `vusinfo` C tools:

```bash
cd ../vusinfo
make
./vusinfo -f ../utig/vkg.47 | head
./vusinfo -d ../utig/vkg.47 | head   # amplitudes
```

Python `--summary` year / DOY / GCSC / mode should match `vusinfo -f`.

---

## SEISF notes (Path D)

- **Headers (year, DOY) and cassette structure** are readable on `vkg.1`–`46`.
- **Science buffer (Path D, production):**
  - halfword pairs → 36-bit → **drop top 4 bits** → 32 bits (BLP-style 32/36)
  - **`Q = matv`** (matches N51SUB NBA=matv+9 / NBB=503−matv)
  - **`bit_offset = 15`**
  - vkg.1↔vkg.47: **2048/2048**, full frame equality where headers match
  - Earlier near-miss: Q=matv−2 / off=13 → ≤8 residual bits at page edges (same family, off-by-two)
  - **Record boundaries:** halfword lookahead into the next physical record (`iter_seisf_frames`)
  - Check: `python3 validate_gold.py`
- N51SUB `BOUT` micro-simulation matches headers / NBA·NBB; bit-insert path incomplete (Path E).
- See also: `materials/N51SUB.jpg`, other files under `materials/`, and `NOTICE`.

---

## Typical workflow

1. `--info` to confirm SEISF vs VUS and record layout.  
2. For VUS: `--summary` / `--csv` for production decode.  
3. For SEISF: check year/DOY with `--summary`, then validate science against VUS (or other archives).  
4. When experimenting with unscramble, compare `--raw` vs normal output.
