# 公開リリース（決定事項 2026-08-05 確定）

English: [public-release.md](public-release.md)

## 著者決定

| 項目 | 決定 |
|------|------|
| 論文言語 | **英語** |
| 投稿先クラス | **AI 系ジャーナル**（手法・事例; 原稿の venue 表を参照） |
| コードライセンス | **MIT**（`LICENSE`） |
| N51SUB 写真 | **`materials/` に同梱** |
| フォーマット PDF | **関連文書を同梱** |
| 権利スタンス | PDF は旧 UTIG Web（`http://www-udc.ig.utexas.edu/external/yosio/Viking/`）由来; **N51SUB.jpg** は UTIG 訪問時の紙資料を撮影（Web 未公開）。`NOTICE` 参照 |
| GitHub アカウント | **`isas-yamamoto`** |
| リポジトリ名 | **`viking-vl2-seisf-decode`**（推奨） |

**Clone URL:**  
`https://github.com/isas-yamamoto/viking-vl2-seisf-decode.git`

**公開状態:** 明示的な public 化まで **private**。

### 代替名（上記が取れない場合）

1. `viking-vl2-seisf-pathd`
2. `viking-seisf-unscramble`
3. `vl2-utig-seisf-decode`

## 同梱するもの

`scripts/prepare_public_dist.sh` → `public-dist/`:

- MIT `LICENSE`, `NOTICE`, `CITATION.cff`
- `src/` デコーダ + テスト
- `materials/` Tier-A PDF + `N51SUB.jpg`
- `vusinfo/` — Yukio Yamamoto による VUS 用 C デコーダ（first-party, MIT）
- `draft/` AI 系向け英語原稿アウトライン
- `docs/` 英語が正; 日本語は `*.ja.md`

## 同梱しないもの

- `utig/`, `nssdc/` の一式
- 作業用の大量 `materials3/` など

## リリースチェックリスト

- [x] MIT LICENSE
- [x] NOTICE（出所の説明）
- [x] CITATION.cff（URL・ORCID）
- [x] AI 会場向け英語原稿アウトライン
- [x] `isas-yamamoto` 下にリポジトリ作成（private）
- [x] `prepare_public_dist.sh` と push
- [x] タグ `v0.1.0`
- [ ] 任意: GitHub release から Zenodo DOI
