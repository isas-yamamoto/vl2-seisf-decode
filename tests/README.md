# Required regression gates

| Script | Role |
|--------|------|
| `test_regression.py` | Fixed unittest suite (gold frame, multi-frame, boundary, VUS) |
| `validate_gold.py` | Gold-frame diagnostics table + hard asserts |

From the **repository root**, with `utig/vkg.1` and `utig/vkg.47` present:

```bash
python3 tests/test_regression.py
python3 tests/validate_gold.py
python3 -m unittest discover -s tests -v
```

Exit **0 = PASS**, **1 = FAIL** (including missing data).
