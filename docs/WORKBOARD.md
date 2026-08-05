# Workboard — paper + public release

**Updated:** 2026-08-05

## Locked decisions

1. Paper: **English**, AI-adjacent **journal** (method case: AI-assisted reverse eng. + dual archives)  
2. License: **MIT**  
3. Bundle **N51SUB.jpg** + related format **PDFs**; NOTICE documents UTIG disappearance story  
4. GitHub: **`isas-yamamoto/viking-vl2-seisf-decode`**

## Done

- [x] `LICENSE` (MIT)  
- [x] `NOTICE`  
- [x] `CITATION.cff`  
- [x] `draft/manuscript.md` (English, venue positioning)  
- [x] `docs/public-release.md` refresh  

## Next (you)

1. Create repo `viking-vl2-seisf-decode` under org/user `isas-yamamoto` (empty, no README if pushing existing tree).  
2. Locally:
   ```bash
   ./scripts/prepare_public_dist.sh
   cd public-dist
   # add LICENSE NOTICE CITATION from parent if script version lags — or push from repo root after layout settled
   git init   # only if not using existing Viking git
   git remote add origin git@github.com:isas-yamamoto/viking-vl2-seisf-decode.git
   git add ...
   git commit -m "Initial public release: Path D SEISF decoder (MIT)"
   git push -u origin main
   git tag v0.1.0 && git push origin v0.1.0
   ```
3. Flesh abstract + §4.5 AI narrative with screenshots only if needed; fill BibTeX first pages.  
4. Pick one venue and reformat (Patterns vs SoftwareX vs JOCCH).

## Next (assistant, on request)

- Rewrite root README for public GitHub  
- Wire `prepare_public_dist.sh` to copy LICENSE/NOTICE/CITATION  
- Pandoc/LaTeX skeleton for submission  
- `gh repo create isas-yamamoto/viking-vl2-seisf-decode` (needs auth)
