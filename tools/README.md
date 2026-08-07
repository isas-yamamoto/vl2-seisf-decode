# Optional inventory tools

Full-archive inventory and probes (not required for everyday decode).

Run from the **repository root** with `utig/` (and optionally `nssdc/`) present:

```bash
python3 tools/coverage_dual_archive.py --no-bits
python3 tools/coverage_nssdc.py --no-seisf
python3 tools/probe_vus_only_neighbours.py
```

Outputs are written under `out/` (gitignored).
