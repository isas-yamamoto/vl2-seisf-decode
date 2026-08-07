# N51SUB — 地上系デスクランブル・ルーチン

論文には含まれない、リポジトリ限定の技術付録です。**N51SUB**（かつて地上局でDAPUバッファをVUSフレームへデスクランブルしていたPDP-15サブルーチン）の3つのグローバル・エントリポイント **MAP** / **SET** / **SEISDT** がそれぞれ何を行うか、そしてそれが本デコーダの `Q = matv` 実装（`src/seisf_decode.py`）とどう対応するかをまとめます。

これは探索的な文字起こし・解析であり、論文本体と同等の検証は経ていません。作業用リファレンスとして扱ってください。写真原典の出典は `NOTICE` を参照。

## 原典と文字起こしの状況

以下のリストは N51SUB アセンブリ原典の写真（`materials/N51SUB.jpg`）からの文字起こしで、判読しづらいオペランド（`AXR`、`LAC T`、`BOUT`、`UNSCR+BOUT`）の拡大クロップと二重照合済みです。独立した別の文字起こしでは3番目のグローバル・エントリポイントを **SETSDT** と表記していますが、より完全な（4シート構成・`.END`で終わり内部一貫性がある — 例: `JMP* SEISDT`）文字起こしでは **SEISDT** と表記されており、本ドキュメントではこちらを採用します。

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

## MAP — アドレス／ポインタ表の構築

`MAP` は29個の8進定数(`BASE`)から512エントリの表 `MAT[]` を構築します。各定数を `MQ` にロードし、18回繰り返し9bitの `TEMP` レジスタを1bit左シフト（`MQ` の押し出されたbitを取り込む）しながら、連番 `Q`（`-511` から `0` まで、512個の値）を `MAT[TEMP]` に格納します。結果として `MAT[]` は、スクランブル済みバッファ先頭2語から得た9bitプローブ値を `[1, 512]` の値へ写す固定置換表になります — これが本デコーダで `matv` と呼ぶページポインタです。

`src/seisf_decode.py` の `build_map_table()` はこのループを同一の `_MAP_BASE` 8進定数・同一のシフト＆格納ロジックで再現し、本番デコーダの `_mat_probe()` が使う `MAT[]` 表と一致します。以前のバージョンのこの再実装は、`Q` が `0` に達した時点(その最後のエントリを格納する前)でループを1回早く打ち切ってしまい、9bitインデックスのうち1つだけがゼロ初期化された既定値のまま未設定になっていました。`estimate_q_from_matv()` の `matv <= 0` フォールバックは、この未設定の1エントリを誤って `matv = 503`(恒等・並べ替えなしのケース)に写していましたが、本来は `matv = 512` が正しい値でした。`matv = 512` と `matv = 503` はアンスクランブルの仕方が異なる(ページごとのセグメント長503/9対、恒等パスの1回通し)ため、この1つのインデックスに該当するフレームは全て誤ってデコードされていました。これが、以前のバージョンの付随論文で報告していた、`matv = 503` の全archive規模で約48%というbit-exact失敗率の全機構でした。

## SET — PDP-15側の一回限りの初期化

`SET` は呼び出しごとに一度だけ実行されます。呼び出し引数語に埋め込まれたインデックスレジスタ情報からバッファの基底インデックス(`XR0`)を求め、レコード間ハーフワード・ストライド `CXR = 0o340`（10進224 — 本デコーダ全体で使われる224ハーフワードのフレーム・ストライドと同じ。`SEISF_HEADER_HALFWORDS` や `vkg_format.py` を参照）を設定し、テープ出力レコード計数(`ACT`)・出力配列ポインタ・テープ書き込みフラグ(`KOUT`)を初期化します。

これらはデスクランブルの計算そのものには関与しません — 物理テープ装置への出力を駆動するためのPDP-15固有のアドレス設定です。本デコーダはメモリ上のハーフワード配列を直接読み、デコード済みフレームをPythonオブジェクトとして書き出すため、`SET` に対応する実装は `src/seisf_decode.py` にありません。原典の網羅性のためにここでのみ記載します。

## SEISDT — フレーム単位のメインループ

`SEISDT` はカセットレコードごとに一度呼ばれるエントリポイントです。672ハーフワードの論理フレームごとに:

1. 4語のエンジニアリング・ヘッダ持ち越し(`T1`–`T4`)を、アドレス`012`の自動増分出力ポインタ経由で出力ストリームへコピー。
2. レコードのハーフワードをストライド`CXR`で走査(`IN`ループ)し、ダミー語のセンチネル `0o1703` を監視（該当時は`DWD`分岐でパディングを充填）。
3. 先頭のスクランブル済みデータペアを読み、`MAP`表で`Q`を引く(`LAC 1,X; LMQ; LAC 0,X; LLS 1; AND 777; TAD (MAT; DAC TADD; LAC* TADD; TCA; DAC Q`) — これはPythonデコーダの`_mat_probe()`／`matv`とまったく同じです。
4. `Q`と503の比較で分岐:
   - **`QLT503`**（`Q < 503`）: `NBA = Q + 9`、`NBB = 503 - Q`、`EA = 503 - Q`、`EB = 0` を設定し、`CLP`を4回（512bitページごとに1回）ループ。各ページで`UNSCR`を2回呼ぶ — `EA`にある`NBA`bitセグメント、`EB`にある`NBB`bitセグメント — 呼び出し毎に`EA`/`EB`を512(`0o1000`)ずつ進める。
   - **`QEQ503`**（`Q >= 503`）: `EA = 0`から単発で2048bitを`UNSCR`（恒等順のケース）。
5. レコード末尾でフレーム末尾語(`LAC T; LRS 4`)を出力ストリームへ回転挿入し、`CXR`を次フレーム分の224ハーフワード進め、レコードの行動計数(`ACT`)が尽きるまで(`IN`)ループ、尽きたら`WRITET`／`RESET`を呼んで継続。

この分岐構造は `src/seisf_decode.py` の `n51_unscramble_2048()` と `pd7400072_readout_order()` に正確に対応します: `Q = matv`、同一の`NBA`/`NBB`/`EA`/`EB`式、同一の`Q < 503`／`Q >= 503`分岐（境界値`Q = 503`はPD7400072 §3.1.1.5.4.4.2に従い恒等順として扱う）。

## UNSCR / BOUT — ビット単位の直列抽出

`UNSCR`は`CXR`とセグメント長の小さな回転・補数演算から開始アドレスを求め、2つの整列ケース（`Q < 503`の「A」セグメント用`ALP`、「B」セグメントおよび`Q >= 503`用の`BB`/`BLP`）のいずれかへ分岐します。いずれも`BOUT`を繰り返し呼び、`LLS 1`（結合`AC`/`MQ`レジスタを1bit左シフトし、`MQ`の最上位bitをリンクへ入れる）に続く`RAR`（そのbitを出力語`T`へ回転挿入）で1bitずつ抽出します。18bitごとに、組み上がったハーフワードをアドレス`012`の自動増分ポインタ経由で書き出し、bit充填計数`ND`を再ロード。`BRTN`はその後、抽出続行（このセグメントでまだbitが必要）／次ハーフワードからの再充填（`NS`が尽きた）／`SEISDT`/`CLP`への復帰（セグメント完了、`ISZ NB`経由）を判定します。

`src/seisf_decode.py` にはこのbit walkの構造的再現(`_n51_unscr_segment`)があり、同じ`MAT[]`表を使い上記のアドレス設定・再充填グループ長と一致させています。ただしこれは副次的・探索的な経路であり、本番デコーダがbit-exactな出力を得ている手法（`n51_unscramble_2048`／`README.md`記載の本番 pair36 定数、すなわち36bitペア化して上位4bit破棄する方式）とは**別**です。`UNSCR`/`BOUT`を、そのペア＆破棄による再構成ではなく本物のPDP-15ビット直列エミュレーションで本番同等のbit-exact結果を再現する、サイクル精度の復元は未完のままです。

## まとめ: N51SUBと本デコーダの対応

| N51SUB | 本デコーダ |
|--------|-----------|
| `MAP` | `build_map_table()` — 同一の`MAT[]`構築 |
| `SET` | 対応なし（PDP-15のテープ／出力側初期化のみ） |
| `SEISDT`の`Q`検索 | `_mat_probe()` → `matv` |
| `SEISDT`の`QLT503`/`QEQ503`分岐 | `pd7400072_readout_order()` / `n51_unscramble_2048()` |
| `UNSCR`/`BOUT`のbit walk | `_n51_unscr_segment()`（探索的；本番経路はペア＆破棄方式を使用） |

原典: `materials/N51SUB.jpg`（写真）。出典は `NOTICE` を参照。
