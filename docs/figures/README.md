# Format diagrams

Cassette / frame layouts for the decoder (repository documentation, not a paper package).

| File | Description |
|------|-------------|
| [fig_seisf_format.png](fig_seisf_format.png) | **SEISF / DLT** — cassette → halfwords → 224-HW frame → Path D → 2048-bit pages |
| [fig_vus_format.png](fig_vus_format.png) | **VUS / USEIS** — cassette → 25×450 B frames → 2700-bit stream → science region |
| [fig_seisf_vus_bridge.png](fig_seisf_vus_bridge.png) | Dual-archive correspondence (SEISF → Path D → VUS) |

Also available as PDF and SVG (same basename).

Regenerate (needs `matplotlib`):

```bash
python3 docs/figures/generate_format_figures.py
```
