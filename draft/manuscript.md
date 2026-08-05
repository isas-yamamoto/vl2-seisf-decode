# Recovering scrambled lander telemetry with AI-assisted reverse engineering:
# Viking Lander 2 SEISF cassettes to bit-exact VUS frames

**Status:** English manuscript outline for an AI-adjacent journal  
**Venue focus:** AI-assisted scientific discovery / digital heritage / AI for Science  
(not a pure planetary-science methods paper; science data is the *case*, method is reverse engineering + validation)

| Item | Choice |
|------|--------|
| Language | English |
| Code license | MIT |
| Target org/repo | `isas-yamamoto` / see § Repository name |
| Ground truth | Matching VUS (USEIS) frames on UTIG reels |
| Code | `cursor/` Path D; `test_regression.py` |

---

## Suggested repository name

**Primary recommendation:** `viking-vl2-seisf-decode`

| Candidate | Rationale |
|-----------|-----------|
| **`viking-vl2-seisf-decode`** | Clear, searchable, mission + product (SEISF) + action |
| `viking-seisf-pathd` | Emphasizes the algorithm name |
| `utig-vl2-cassette-decode` | Emphasizes archive source; less algorithm-focused |

URL (primary): `https://github.com/isas-yamamoto/viking-vl2-seisf-decode`

---

## Target journals (AI-related, realistic fit)

Aim at **method + case** papers, not seismology-only venues.

| Tier | Venue examples | Fit |
|------|----------------|-----|
| Strong fit | *Patterns* (Cell Press), *Scientific Data* (Nature, if framed as soft+workflow), *ACM J. Comput. Cult. Herit. (JOCCH)*, *Digital Scholarship in the Humanities* | AI/tools + cultural/scientific heritage |
| AI-for-science | *Nature Machine Intelligence* (harder; need general AI method claim), workshops at NeurIPS/ICML “AI for Science” | Only if stressing assisted reverse-engineering pipeline |
| Engineering | *IEEE Access*, *SoftwareX* | Software artifact + decode method |
| Domain co-submit | Later: seismology note citing this paper for the data product | After method paper |

**Positioning one-liner for cover letter:**  
We present a bit-exact recovery of scrambled planetary lander telemetry achieved by combining archival hardware docs, photographed assembly listings, ground-truth dual archives, and iterative AI-assisted hypothesis search—releasing MIT-licensed software and curated materials.

---

## Abstract (draft)

The Viking Lander 2 seismic experiment left two coexisting cassette products: **SEISF (DLT)**, a scrambled science buffer as written from the spacecraft DRAM readout order, and **VUS (USEIS)**, the same science after ground processing on a PDP-15 (`N51SUB` / `N51VUS`). Open scientific reuse of SEISF requires inverting that scramble. We recover a **bit-exact** mapping from SEISF halfword streams to VUS 2048-bit data regions by (i) reinterpreting the PD7400072 page readout with pointer \(Q=\mathrm{matv}\), (ii) packing consecutive 18-bit halfwords as 36-bit pairs and retaining 32 bits (drop the top four), with a fixed stream offset of 15 bits, and (iii) stitching halfwords across physical record boundaries. Validation against header-matched VUS frames on UTIG reels (including a gold frame with GCSC \(=125078\)) achieves **2048/2048 bit identity** and full 450-byte frame equality. Along the path, several near-miss models (e.g., \(Q=\mathrm{matv}-2\) with offset 13) left only page-edge residuals—illustrating how dual archives and archive-grade listings constrain AI-assisted reverse-engineering search. We release the decoder under the **MIT License**, with curated primary materials (format PDFs and the N51SUB listing photograph) needed to reproduce the derivation.

**Keywords:** reverse engineering; scientific data recovery; digital preservation; planetary seismology; Viking; AI-assisted discovery; ground-truth dual archives

---

## 1. Introduction

### 1.1 Dual archives and lost pipelines

Historical spacecraft datasets often survive as both “raw-ish” streams and “mission-processed” products. When the processing stack (PDP-15 programs, operator runbooks) is incomplete, scrambled products become unusable even if bits are intact. Viking Lander 2 offers a clean laboratory: **SEISF** and **VUS** still coexist on UTIG 8 mm cassettes labeled DLT vs VUS.

### 1.2 Role of AI-assisted reverse engineering

Hypothesis generation at the bit-layout level is combinatorial. Human expertise selects archival sources; AI assistants accelerate enumeration of packing laws, pointer equations, and regression tests. We do not treat models as oracles; **every claim is locked by executable tests against VUS ground truth**.

### 1.3 Contributions

1. Cassette/frame geometry for SEISF and a production Path-D unscramble.  
2. Bit-exact multi-frame validation protocol using shared 108-byte headers.  
3. Failure typology (near-miss \(Q\)/offset couplings, record spills) as reusable methodology.  
4. MIT-licensed software + curated archival materials for independent reproduction.

---

## 2. Related work (outline only)

- Digital recovery of space mission data; Apollo/planetary seismology data products.  
- Telemetry decommutation and interleaver inversion.  
- AI for Science / human–AI collaborative reverse engineering (position paper-level citations TBD).  
- Viking seismic dataset descriptions and VUS tooling (`vusinfo`).

Fill `@…` keys in `draft/references.bib` after reading first pages of each PDF.

---

## 3. Data products and notation

| Product | UTIG files (example) | Role |
|---------|----------------------|------|
| SEISF/DLT | `vkg.1`–`vkg.46` | Scrambled science |
| VUS/USEIS | `vkg.47`–`vkg.56` | Ground-processed GT |

- Logical SEISF frame: 224 halfwords (18-bit values in 3-byte cassette cells).  
- Shared engineering header: 108 bytes / 36 halfwords.  
- Science region: 2048 bits = four 512-bit pages.  
- Gold frame (vkg.1 base 170 ↔ vkg.47 f0): matv \(=423\), GCSC \(=125078\), year/DOY \(1976/249\).

---

## 4. Method

### 4.1 Structural parse

Subgroup header (1000 B), fixed SEISF records (10752/10764 B), halfword extraction, frame base search (pitch 224, first base 170 on gold reel).

### 4.2 Path D (deterministic)

1. **Pair-36 packing:** for each consecutive halfword pair, form 36 MSB-first bits; **drop indices 0–3**; emit 32 bits.  
2. Skip **bit_offset = 15**, take 2048 stream bits.  
3. Probe **matv** via N51SUB MAP table; set **\(Q=\mathrm{matv}\)** (matches N51SUB NBA \(=\mathrm{matv}+9\), NBB \(=503-\mathrm{matv}\)).  
4. Invert PD7400072 readout order into sequential buffer bits.  
5. **Record lookahead** when science extends past the physical record.

### 4.3 VUS parse

Port of `vusinfo` bit-stream layout (word-oriented 36-bit mirror into a 2700-bit frame stream; science at offset 648).

### 4.4 Validation protocol

Header-identical pairs; metrics: bit match /2048; full-frame equality; GCSC/mode/leading amplitudes. Locked by `test_regression.py`.

### 4.5 Near-miss typology (for the AI-methods narrative)

| Model | Result | Lesson |
|-------|--------|--------|
| \(Q=\mathrm{matv}-2\), off \(=13\) | ~2044/2048; residuals only at page-stream edges | Off-by-two family |
| Full 18-bit + residual \(Q\) | GCSC sometimes OK, amplitudes weak | Packing dominates |
| Truncated last record | ~1650/2048 “damage” | Spill, not media |
| Faithful BOUT microcode | Header+NBA/NBB OK; serial bit idiom open | Functional equivalence ≠ full ISA sim |

---

## 5. Results

- Gold: residual **0/2048**, frame_eq, NORMAL \(n=83\), leading amps match VUS.  
- Record-0 header-matched Path-D frames: bit- and frame-perfect under regression gates (≥12 frames; includes base 3530 boundary).  
- Long CLI runs (1000+ frames): bounded stream reads; no crash on short samples.

*(Expand with a small table after re-running tests for camera-ready numbers.)*

---

## 6. Discussion

- Dual products as **free ground truth** for reverse engineering.  
- AI assistants as search accelerators; **tests and archives** as verifiers.  
- Rights: MIT code; materials redistributed for scholarship from formerly public UTIG holdings (see `NOTICE`).  
- Limits: BOUT instruction-level gap; rare matv≥503 paths; media bit errors on other reels.

---

## 7. Conclusion

Path D yields bit-exact SEISF→VUS recovery for Viking Lander 2 cassettes and is released under MIT with the documents required to audit the derivation.

---

## Data and code availability

- Code: GitHub `isas-yamamoto/viking-vl2-seisf-decode` (planned), MIT.  
- Cassette images: not redistributed; place under `utig/` locally.  
- Tests: `python3 test_regression.py` with `vkg.1` and `vkg.47`.

## Author contributions / Acknowledgments / Conflicts

TBD.
