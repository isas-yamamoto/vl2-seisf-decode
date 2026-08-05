# Public release (decisions locked 2026-08-05)

## Author decisions

| Item | Decision |
|------|----------|
| Paper language | **English** |
| Venue class | **AI-related journal** (method + case; see manuscript venue table) |
| Code license | **MIT** (`LICENSE`) |
| N51SUB photo | **Bundle** in `materials/` |
| Format PDFs | **Bundle** related docs |
| Rights stance | Formerly public via UTIG; pages removed after retirement of contact investigator — redistributed for scholarship/reproducibility (`NOTICE`) |
| GitHub account | **`isas-yamamoto`** |
| Repository name | **`viking-vl2-seisf-decode`** (recommended) |

**Clone URL:**  
`https://github.com/isas-yamamoto/viking-vl2-seisf-decode.git`  

**Visibility:** repository is **private** until explicit public release.

### Alternate names (if primary is taken)

1. `viking-vl2-seisf-pathd`  
2. `viking-seisf-unscramble`  
3. `vl2-utig-seisf-decode`

## What ships

See `scripts/prepare_public_dist.sh` → `public-dist/`:

- MIT `LICENSE`, `NOTICE`, `CITATION.cff`
- `src/` decoder + tests
- `materials/` Tier-A PDFs + `N51SUB.jpg`
- `vusinfo/` — original VUS C decoder by Yukio Yamamoto (first-party, MIT)- `draft/` English outline for AI-venue paper

## What does not ship

- `utig/`, `nssdc/` full dumps  
- bulk `materials3/` scrap worktrees  

## Release checklist

- [x] MIT LICENSE  
- [x] NOTICE (materials provenance story)  
- [x] CITATION.cff (repo URL = recommended name)  
- [x] English manuscript outline targeted at AI venues  
- [ ] Create empty repo under `isas-yamamoto` on GitHub  
- [ ] `prepare_public_dist.sh` and push `public-dist` (or restructure root)  
- [ ] Tag `v0.1.0`  
- [ ] Optional Zenodo DOI from the GitHub release  
