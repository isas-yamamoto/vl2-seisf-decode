# vusinfo — VUS / USEIS cassette reader (C)

Historical C tools for **already-unscrambled** VUS cassette frames
(`vkg.47`–`vkg.56`). The Python package decodes VUS in
`src/vus_decode.py` with the same science-bit layout; this tree is kept
so operators can cross-check year / DOY / GCSC / amplitudes against
`vusinfo -f` / `-d`.

SEISF unscrambling is not implemented here — use `src/` for that.

```bash
make
./vusinfo -f /path/to/vkg.47
```
