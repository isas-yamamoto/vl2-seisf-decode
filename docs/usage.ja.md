# 使い方 — Viking Lander 2 (`utig/vkg.*`) デコード

以下は公開レイアウト（`src/` が `docs/` の隣）を想定しています。

```bash
cd src
```

依存は標準ライブラリのみ（Python 3.9+ 想定）。

英語版: [usage.md](usage.md)

## カセット／フレーム形式図

| 図 | ファイル |
|----|----------|
| SEISF / DLT | [figures/fig_seisf_format.png](figures/fig_seisf_format.png) |
| VUS / USEIS | [figures/fig_vus_format.png](figures/fig_vus_format.png) |
| SEISF → デコード → VUS | [figures/fig_seisf_vus_bridge.png](figures/fig_seisf_vus_bridge.png) |

![SEISF レイアウト](figures/fig_seisf_format.png)

![VUS レイアウト](figures/fig_vus_format.png)

![デコード対応](figures/fig_seisf_vus_bridge.png)

索引: [figures/README.md](figures/README.md)。各図に PDF / SVG あり。

---

## データの種類

| ファイル | ラベル | 意味 |
|----------|--------|------|
| `../utig/vkg.1`〜`vkg.29` | `DLT…` | **SEISF**（スクランブル付き）。本パッケージの主対象 |
| `../utig/vkg.30`〜`vkg.46` | `DLT…` | **MET**（気象計器。SEISFとは別製品）。同一保存物だが対象外 |
| `../utig/vkg.47`〜`vkg.56` | `VUS…` | **VUS / USEIS**（アンスクランブル済み）。`vusinfo` と同等レイアウト |

両方を同じ CLI から扱います。拡張子ではなく先頭サブグループヘッダで判別します。

入手元: `vkg.1`〜`vkg.56` は DARTS（宇宙科学研究所/JAXA）で公開: https://data.darts.isas.jaxa.jp/pub/viking/utig/

---

## ファイル構成

| ファイル | 内容 |
|----------|------|
| `decode_vkg.py` | CLI エントリポイント |
| `vkg_format.py` | カセット／レコード共通レイアウト |
| `vus_decode.py` | VUS 科学データのビット列デコード |
| `seisf_decode.py` | SEISF デコード（pair36 / Q=matv / off=15） |
| `validate_gold.py` | 金フレーム診断表 + ハードアサート（終了コード） |
| `test_regression.py` | **固定リグレッション**（unittest） |

---

## 動作確認（固定）

データ `../utig/vkg.1` と `../utig/vkg.47` がある状態で:

```bash
# 推奨: 一式（金フレーム + 複数フレーム + 境界 + VUS）
python3 test_regression.py

# 金フレームのみ診断表 + アサート
python3 validate_gold.py

# unittest 詳細
python3 -m unittest test_regression -v
```

終了コード **0 = PASS**、**1 = FAIL**（データ欠落時も 1）。

| 検査 | 期待 |
|------|------|
| デコード定数 | `bit_offset=15`, drop `(0,1,2,3)`, `Q=matv` |
| 金 f0 (base=170) | GCSC=125078、science **0 residual**、450B **frame_eq** |
| 振幅 | X/Y/Z 先頭6が VUS と一致 |
| レコード0 ヘッダ一致フレーム | デコード対象はすべて 2048/2048 |
| base=3530 | レコード境界・先読みで 2048/2048 |
| VUS vkg.47 f0 | NORMAL / n=83 / GCSC=125078 |

---

## 基本コマンド

### 1. ファイル構造の表示

サブグループ数・ラベル・レコード長・SEISF フレームの年/DOY 範囲。

```bash
python3 decode_vkg.py ../utig/vkg.1 --info
python3 decode_vkg.py ../utig/vkg.47 --info
```

### 2. フレーム要約（年・DOY・GCSC・mode）

```bash
# SEISF（先頭 20 フレーム）
python3 decode_vkg.py ../utig/vkg.1 --summary --max-frames 20

# VUS（vusinfo の -f に相当）
python3 decode_vkg.py ../utig/vkg.47 --summary --max-frames 20
```

出力例（VUS）:

```
frame=    0 year=1976 doy=249 gcsc=  125078 mode=NORMAL n= 83 chg=255 note=
```

- `note=seisf+unscr` … SEISF を MAP/UNSCR 経由で読んだもの
- `note=seisf-raw` … `--raw` 時（スクランブル解除なし）

### 3. 振幅サンプル表示

他モード未指定時の既定動作。作業量は `--max-frames` で制限します。

```bash
python3 decode_vkg.py ../utig/vkg.1 --samples --max-frames 3 --limit-per-block 20
python3 decode_vkg.py ../utig/vkg.47 --samples --max-frames 1 --limit-per-block 30
```

- NORMAL / HIGH: `sample  amp_x  amp_y  amp_z`
- EVENT: 各軸の後に axis crossings が続く

### 4. CSV 出力

```bash
python3 decode_vkg.py ../utig/vkg.1 --csv out_vkg1.csv --max-frames 5
python3 decode_vkg.py ../utig/vkg.47 --csv out_vkg47.csv --max-frames 10
```

列: `frame, block, year, doy, gcsc, mode, sample, amp_x, amp_y, amp_z, axis_x, axis_y, axis_z, note`

### 5. SEISF の MAP をスキップ（デバッグ）

ヘッダ構造だけ見る／アンスクランブルを切ってパックをそのまま VUS 形に載せる場合。

```bash
python3 decode_vkg.py ../utig/vkg.1 --raw --summary --max-frames 5
```

---

## オプション一覧

| オプション | 説明 |
|------------|------|
| `vkg`（位置引数） | `vkg.N` へのパス |
| `--info` | カセットサブグループ構成のみ表示 |
| `--summary` | 年 / DOY / GCSC / mode の 1 行要約 |
| `--samples` | 振幅を標準出力（他モード未指定時の既定動作） |
| `--csv PATH` | サンプルを CSV 保存 |
| `--max-frames N` | 先頭 N フレームだけ処理。**省略時は全フレーム**（上限なし） |
| `--limit-per-block N` | `--samples` 時、1 ブロックあたり表示サンプル数（既定 20） |
| `--raw` | SEISF のみ: MAP/UNSCR を行わない |

---

## C 実装（VUS のみ）との比較

アンスクランブル済み VUS は、同梱の `vusinfo`（レガシー、本パッケージに後継。`legacy/vusinfo/README.md` 参照）でも検証できます。

```bash
cd ../legacy/vusinfo
make
./vusinfo -f ../../utig/vkg.47 | head
./vusinfo -d ../../utig/vkg.47 | head   # 振幅
```

Python の `--summary` の year / DOY / GCSC / mode は `vusinfo -f` と一致する想定です。

---

## 現状の注意（SEISF）

- **ヘッダ（年・DOY）とカセット構造**は `vkg.1`〜`29`（SEISF）と `vkg.30`〜`46`（MET、対象外）で読める。
- **科学バッファ（確定）**:
  - 半語ペア 36bit → **先頭 4bit 破棄** → 32bit 詰め（BLP 系 32/36）
  - **`Q = matv`**（N51SUB の NBA=matv+9 / NBB=503−matv と一致）
  - **`bit_offset = 15`**
  - 224半語のフレーム周期の整数倍でないレコード長は固定長のリーダー部を持ち、継続レコードごとに詰め込み前に読み飛ばす必要がある
  - vkg.1↔vkg.47 照合: **2048/2048・フレーム完全一致**（ヘッダ一致箇所）
  - **レコード境界**: 次レコード半語の先読み（`iter_seisf_frames`）
  - archive全体のbit-exact失敗率: matv < 503で**0.08%**、matv = 503で**0.13%**、matv > 503で**0.11%**（3つとも同等に信頼できる。レコードごとの最後のチェーンフレーム位置にわずかな残差が残る）
  - 照合: `python3 validate_gold.py`
- 参考: `materials/N51SUB.jpg`、その他 `materials/`、`NOTICE`

---

## 典型的な作業手順

1. `--info` で SEISF/VUS とレコード構成を確認する。  
2. VUS なら `--summary` / `--csv` で本デコード。  
3. SEISF ならまずヘッダの年・DOY を `--summary` で確認し、科学値は VUS 等と突き合わせる。  
4. アンスクランブル実験時は `--raw` と通常実行の差分を見る。
