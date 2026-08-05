# Public release (decisions locked 2026-08-05)

Japanese: [public-release.ja.md](public-release.ja.md)

## Author decisions

| Item | Decision |
|------|----------|
| Paper language | **English** |
| Venue class | **AI-related journal** (method + case; see manuscript venue table) |
| Code license | **MIT** (`LICENSE`) |
| N51SUB photo | **Bundle** in `materials/` |
| Format PDFs | **Bundle** related docs |
| Rights stance | PDFs from former UTIG web (`http://www-udc.ig.utexas.edu/external/yosio/Viking/`); **N51SUB.jpg** = photo of paper copy from UTIG visit (not web-published). See `NOTICE`. |
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
- `vusinfo/` — original VUS C decoder by Yukio Yamamoto (first-party, MIT)
- `draft/` English outline for AI-venue paper
- `docs/` English docs; Japanese as `*.ja.md`

## What does not ship

- `utig/`, `nssdc/` full dumps
- bulk `materials3/` scrap worktrees

## Release checklist

- [x] MIT LICENSE
- [x] NOTICE (materials provenance story)
- [x] CITATION.cff (repo URL = recommended name; ORCID set)
- [x] English manuscript outline targeted at AI venues
- [x] Create repo under `isas-yamamoto` on GitHub (private)
- [x] `prepare_public_dist.sh` and push `public-dist`
- [x] Tag `v0.1.0`
- [ ] Optional Zenodo DOI from the GitHub release
