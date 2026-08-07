# N51SUB — the ground-software descramble routine

This is a technical appendix, not part of the paper: repo-level notes on
**N51SUB**, the PDP-15 ground-software subroutine that historically
descrambled the seismometer's DAPU buffer into VUS frames on the original
ground station. It documents what its three global entry points —
**MAP**, **SET**, **SEISDT** — each do, and how they map onto this
decoder's `Q = matv` implementation (`src/seisf_decode.py`).

This is exploratory transcription/analysis, not independently verified to
the rigor of the accompanying paper. Treat it as a working reference, and
see `NOTICE` for provenance of the source photograph.

## Source and transcription status

The listing below is transcribed from a photograph of the original N51SUB
assembly source (`materials/N51SUB.jpg`), cross-checked twice against
zoomed crops of the harder-to-read operands (`AXR`, `LAC T`, `BOUT`,
`UNSCR+BOUT`). One independent, partial transcription of the same source
spells the third global entry point **SETSDT**; the fuller transcription
below (four sheets, ends in `.END`, internally self-consistent — e.g.
`JMP* SEISDT`) spells it **SEISDT**, which we treat as authoritative.

```
.TITLE N51SUB
.GLOBL MAP,SET,SEISDT,,DA,NMAGTA
/ GENERATE MEMORY ADDRESS BIT PATTERN TABLE
MAP: LAC (BASE; DAC BADD#; LAW -777; DAC Q#; DZM TEMP#
BSLP LAC* BADD; LMQ; LAW -22; DAC NS#
SHLP LAC TEMP; LLS 1; AND (777; DAC TEMP
 TAD (MAT; DAC TADD#; LAC Q; TAD (1000; DAC* TADD; ISZ Q; SKP; JMP* MAP
 ISZ NS; JMP SHLP; ISZ BADD; JMP BSLP
BASE 410604; 712541; 572334; 424126; 477311; 133744; 651460
 061450; 645772; 130726; 263617; 564065; 556602; 657525
 005127; 456700; 716447; 535211; 031605; 733150; 357037
 740757; 427144; 045166; 436371; 542510; 706653; 423042; 0
MAT 0; .BLOCK 777
/ SETUP ROUTINE
SET; JMS* .DA; JMP .+4;ARRAY; JDR+400000;NR
 LAC I.; AND (70000; TCA; TAD ARRAY; DAC XR0#; AAC 340; DAC CXR#
 TAD (6522; DAC LR1#; LAW -17; DAC ACT#
 LAC ARRAY; AAC -1; DAC ARRAY; AAC 62; DAC* (10
 TAD (7004; DAC KOUT#; IAC; DAC DA; JMS RESET; JMP* SET
/ MAIN SUBROUTINE
SEISDT; LAC T1; DAC* 10; LAC T2; DAC* 10
 LAC T3; DAC* 10; LAC T4; DAC* 10; LAC CXR
IN PAX; LAC 0,X; SAD (1703; JMP DWD; PXA; AAC 44; PAL
 LAC 0,X; DAC* 12; AXS 1; JMP .-3; LAW -22; DAC ND#
 LAC 1,X; LMQ; LAC 0,X; LLS 1; AND (777; TAD (MAT; DAC TADD
 LAC* TADD; TCA; DAC Q; TAD (767; SMA;SZA; JMP QLT503; SMA; JMP QEQ503
 DAC NBA#; TAD (1000; DAC EA#; TCA; DAC NBB#; JMP CLP-3
QEQ503 LAW -4000; DAC NB#; CLA; JMS UNSCR; JMP NEXT
QLT503 DAC EA; TCA; DAC NBB; LAC Q; AAC -11; DAC NBA
 DZM EB#; LAW -4; DAC NC#
CLP LAC NBA; DAC NB; LAC EA; JMS UNSCR
 LAC NBB; DAC NB; LAC EB; JMS UNSCR
 LAC EA; TAD (1000; DAC EA; LAC EB; TAD (1000; DAC EB; ISZ NC; JMP CLP
NEXT LAC T; CLL; LRS 4; DAC* 12
 ISZ BCT; JMP .+3; JMS WRITET; JMS RESET
 LAC CXR; AAC 340; DAC CXR; ISZ ACT; JMP IN; PAX
 LAC LR1; PAL; LAC ARRAY; DAC* (10; LAC 0,X; DAC* 10; AXS 1; JMP .-3
 LAC 0,X; DAC T1#; LAC 1,X; DAC T2#; LAC 2,X; DAC T3#; LAC 3,X; DAC T4#
 LAC XR0; DAC CXR; LAW -20; DAC ACT; JMP* SEISDT
DWD LAW -226; DAC CCT#; LAC (111111; DAC* 12; ISZ CCT; JMP .-2
 ISZ BCT; JMP DWD; JMS WRITET; ISZ SEISDT; JMP* SEISDT
/ UNSCRAMBLE ROUTINE
UNSCR; TAD (1117; CLL; LRS 5; RAL; TAD CXR; PAX; CLA
 LLS 5; TCA; AAC 15; SPA; JMP BB; TAD (LRS 1; DAC ILRSA
 AND (17; TCA; DAC NS; LAC 0,X;ILRSA; JMP ALP
BB TAD (LRS 23; DAC ILRSB; AND (37; TCA; DAC NS; LAC 1,X;ILRSB; JMP BLP
ALP JMS BOUT; LAW -22; DAC NS; LAC 1,X; LMQ
BLP JMS BOUT; LAW -16; DAC NS; AXR 2; LAC 0,X; LRS 16; JMP ALP
/ SERIAL BIT PROCESSING
BOUT; LLS 1; RAR; LAC T#; RAR; DAC T; ISZ ND; JMP BRTN
 DAC* 12; LAW -22; DAC ND
BRTN ISZ NB; SKP; JMP* UNSCR; ISZ NS; JMP BOUT+1; JMP* BOUT
/ WRITE TAPE
WRITET; JMS* NMAGTA; JMP .+11; (7246;JDR; (1; (4; (2,0A; ER#; (1
 ISZ* NR; JMP* WRITET
RESET; LAC KOUT; DAC* (12; LAW -31; DAC BCT#; JMP* RESET
.END
```

## MAP — building the address/pointer table

`MAP` builds a 512-slot lookup table, `MAT[]`, from 29 octal constants
(`BASE`). For each constant it loads it into `MQ` and, 18 times, left-shifts
a running 9-bit `TEMP` register by one bit (feeding in `MQ`'s vacated bit),
then stores the *sequence index* `Q` (running from `-511` up to `0`
inclusive — 512 values) into `MAT[TEMP]`. The net effect: `MAT[]` is a
fixed permutation table that maps a 9-bit probe value (derived from the
first two words of the scrambled buffer) to a value in `[1, 512]` — the
page pointer this decoder calls `matv`.

`build_map_table()` in `src/seisf_decode.py` reimplements this loop
(same `_MAP_BASE` octal constants, same shift-and-store logic) and produces
the identical `MAT[]` table used by the production decoder's `_mat_probe()`.
An earlier version of this reimplementation stopped the loop one iteration
too early (as soon as `Q` reached `0`, before storing that final entry),
leaving exactly one 9-bit index unassigned at its zero-initialized default;
`estimate_q_from_matv()`'s `matv <= 0` fallback then silently mapped that
one missing index to `matv = 503` (the identity/no-reordering case) instead
of its correct value, `matv = 512`. Since `matv = 512` and `matv = 503`
require different unscrambling (segment lengths 503/9 per page vs. a flat
identity pass), every frame probing to that one index decoded incorrectly.
This was the entire mechanism behind `matv = 503`'s roughly 48%
archive-wide bit-exact failure rate reported in earlier versions of the
accompanying paper.

## SET — one-time PDP-15 bookkeeping

`SET` runs once per invocation. It resolves the buffer's index-register base
(`XR0`) from an index-register field packed into the caller's argument word,
sets the record-to-record halfword stride `CXR = 0o340` (224 decimal — the
same 224-halfword frame stride used throughout this decoder, see
`SEISF_HEADER_HALFWORDS` and `vkg_format.py`), and initializes the tape
output-record counter (`ACT`), the output array pointer, and the tape-write
flag (`KOUT`).

None of this affects the descramble arithmetic — it is PDP-15-specific
address setup for driving a physical output tape drive. This decoder reads
directly from an in-memory halfword array and writes decoded frames as
Python objects, so `SET` has no counterpart in `src/seisf_decode.py`; it is
reproduced here only for completeness of the source.

## SEISDT — the main per-frame loop

`SEISDT` is the entry point called once per cassette record. For each
672-halfword logical frame it:

1. Copies the 4-word engineering-header carry-over (`T1`–`T4`) to the output
   stream via the auto-incrementing output pointer at address `012`.
2. Walks the record's halfwords (`IN` loop) at stride `CXR`, watching for the
   dummy-word sentinel `0o1703` (`DWD` branch fills padding when hit).
3. Reads the first scrambled data pair, looks up `Q` via the `MAP` table
   (`LAC 1,X; LMQ; LAC 0,X; LLS 1; AND 777; TAD (MAT; DAC TADD; LAC* TADD;
   TCA; DAC Q`) — this is exactly `_mat_probe()` / `matv` in the Python
   decoder.
4. Branches on `Q` vs. 503:
   - **`QLT503`** (`Q < 503`): sets up `NBA = Q + 9`, `NBB = 503 - Q`,
     `EA = 503 - Q`, `EB = 0`, then loops `CLP` four times (once per
     512-bit page), calling `UNSCR` twice per page — once for the `NBA`-bit
     segment at `EA`, once for the `NBB`-bit segment at `EB` — advancing
     `EA`/`EB` by 512 (`0o1000`) each pass.
   - **`QEQ503`** (`Q >= 503`): a single 2048-bit `UNSCR` call from `EA = 0`
     (the identity-order case).
5. At the end of the record, rotates the frame's trailer word (`LAC T; LRS 4`)
   into the output stream, advances `CXR` by another 224 halfwords for the
   next frame, and loops (`IN`) until the record's action counter (`ACT`)
   is exhausted, then calls `WRITET`/`RESET` before continuing.

This branch structure is exactly `n51_unscramble_2048()` and
`pd7400072_readout_order()` in `src/seisf_decode.py`: `Q = matv`, the same
`NBA`/`NBB`/`EA`/`EB` formulas, and the same `Q < 503` / `Q >= 503` split
(with the `Q = 503` boundary case handled as identity order, per
PD7400072 §3.1.1.5.4.4.2).

## UNSCR / BOUT — serial bit extraction

`UNSCR` computes a start address from `CXR` and a small rotate/complement of
the segment length, then branches into one of two alignment cases (`ALP` for
the `Q < 503` "A" segment, `BB`/`BLP` for the "B" segment and the `Q >= 503`
case), each of which repeatedly calls `BOUT` to extract one bit at a time
via `LLS 1` (shift the combined `AC`/`MQ` register left by one, so `MQ`'s
top bit enters the link) followed by `RAR` (rotate that bit into the output
word `T`). Every 18 bits, the assembled halfword is written out through the
auto-incrementing pointer at address `012` and the bit-fill counter `ND` is
reloaded; `BRTN` then decides whether to keep extracting (more bits needed
in this segment), refill from the next halfword (`NS` exhausted), or return
to `SEISDT`/`CLP` (segment done, via `ISZ NB`).

`src/seisf_decode.py` has a structural reconstruction of this bit walk
(`_n51_unscr_segment`), reusing the same `MAT[]` table and matching the
address-setup and refill-group sizes above; it is kept as a secondary,
exploratory path and is **not** what the production decoder uses to produce
its validated, bit-exact output (`n51_unscramble_2048` / production pair36 constants in
`README.md`, i.e. 36-bit halfword pairing with the top 4 bits dropped). A
fully cycle-accurate revival of `UNSCR`/`BOUT` — one that reproduces the
production bit-exact result via genuine PDP-15 bit-serial emulation rather
than the pair-and-drop reconstruction — remains open.

## Summary: how this maps onto the decoder

| N51SUB | This decoder |
|--------|--------------|
| `MAP` | `build_map_table()` — identical `MAT[]` construction |
| `SET` | No counterpart (PDP-15 tape/output bookkeeping only) |
| `SEISDT`'s `Q` lookup | `_mat_probe()` → `matv` |
| `SEISDT`'s `QLT503`/`QEQ503` split | `pd7400072_readout_order()` / `n51_unscramble_2048()` |
| `UNSCR`/`BOUT` bit walk | `_n51_unscr_segment()` (exploratory; production path uses pair-and-drop instead) |

Primary sources: `materials/N51SUB.jpg` (photograph); `NOTICE` (provenance).
