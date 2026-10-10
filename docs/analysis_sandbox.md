# 分析用 sandbox（実装と動作確認）

2026-10-10。[analysis_sandbox_design.md](analysis_sandbox_design.md) の決定に沿って、study-geoai-algo-py の水準の分析を実行できる sandbox を作り、G1（study-geoai の 001-B ロジスティック回帰）を Geo-Voyager の中で再実装して、study-geoai の README の数字を再現できることを確かめた。ローカル LLM はまだ使っていない。study-geoai のコードとデータは使っていない（README の数字と、問題設定の文章だけを使った）。

## 構成

| 部品 | 場所 | 中身 |
|---|---|---|
| 資源の枠 | `geo_voyager/docker_sandbox.py` の `SandboxProfile`、`DEFAULT_PROFILE`、`ANALYSIS_PROFILE` | 分析の枠: メモリ 8g（`--memory-swap` も 8g で swap なし）、CPU 4、PID 512、600 秒、`/tmp` の tmpfs 2g（noexec）。`data_dir` を `/data` に読み取り専用で、空の `out_dir` を `/out` に書き込み可でマウント。ネットワークなし。既定の枠は従来どおり（128m、1 CPU、30 秒）で、`--memory-swap` を足しただけ |
| イメージ | `docker/analysis/Dockerfile`、タグ `geo-voyager-analysis:2026-10-10`（2.34GB） | numpy、scipy、pandas、scikit-learn、statsmodels、DuckDB 1.5.6（spatial）、pyarrow、matplotlib、networkx、LightGBM、XGBoost、CatBoost、SHAP、verde、rasterio、OR-Tools、highspy。版は study-geoai が oracle の数字を出したときの版（DuckDB だけ Geo-Voyager の 1.5.6）。torch は入れていない |
| Primitive | `geo_voyager/analysis_primitives/` | `data_path(name)`（`/data` の下の固定データ。無ければ、ある名前の一覧を添えて例外）、`output_path(name)`（`/out` の下）、`connect_duckdb()`（メモリ上限 4GB、4 スレッド、spill は `/tmp`、spatial を読み込む） |
| 固定データ | `geo_voyager/analysis_data.py`、`scripts/fix_analysis_data.py` | 版を固定した URL と SHA-256 と大きさとライセンス。置き場所は `/sata_hdd_24tb/data/geo-voyager/analysis/`（環境変数 `GEO_VOYAGER_ANALYSIS_DATA` で変えられる）。既にあるファイルは確かめるだけで、食い違えば上書きせず失敗にする。リポジトリには入れない |
| oracle と照合 | `bench/study_oracles.py`、`bench/run_reference.py` | study-geoai の README の数字と許容誤差。参照解を分析の枠で動かし、項目ごとに照合する |
| 参照解 | `bench/reference/g1_undergrounding.py` | Claude Code が書いた G1 の解。Planner などには見せない |

固定したデータ（2026-10-10）:

| パス | 出どころ（固定した版） | 大きさ |
|---|---|---|
| `michiyomi/taito.parquet` | Hugging Face `finalvent/michiyomi-tokyo-streetscape` の `e4966cdceff6`（release 2026-09-13-r1）の `data/scenes/taito.parquet`。CC BY-SA 4.0 | 59,739,579 バイト、55,044 行 |
| `jp-admin/municipalities.parquet` | Hugging Face `yuiseki/jp-admin-2026-09` の `e6c87b1d7095`（Geo-Voyager が既に固定している版）。CC BY 4.0 | 148,639,909 バイト |

## 動作確認

`integration/test_analysis_sandbox.py`（実 Docker、4 件とも通る）:

- 全ライブラリが import でき、OR-Tools と highspy が 1 つのプロセスで共存する（scikit-learn 1.9.1、DuckDB 1.5.6）。
- `/data` のファイルは読めて（55,044 行）、書けない。`/out` に書いた PNG は実行後に残る。
- ネットワークに出られない。
- 9GB を確保するコードは、ホストではなくコンテナが OOM で止まる（終了コード 137）。

最初のビルドでは rasterio が `libexpat.so.1` が無くて import できなかった。slim のイメージに `libexpat1` を足した。

## G1 の再実装（001-B）

問題設定は study-geoai の README の文章から決めた。2 点は、データを開いて README の数字に合わせて決めた。

- 「台東区 53,948 シーン」は、ファイルの全 55,044 行ではなく、位置（`lat`、`lon`）が台東区の境界（jp-admin の `code5 = 13106`）の中にあるシーンの数だった。`computed_lat` では 53,882、`raw_lat` では 54,015 になる。
- 「左右の歩道の有無」は `presence == "あり"` かどうか。`画角外不明` などを空とみなすと、使う行が 32,593 にならない。

結果（`python -m bench.run_reference G1 bench/reference/g1_undergrounding.py`、5.8 秒、[evidence/analysis_sandbox/g1_reference.txt](evidence/analysis_sandbox/g1_reference.txt)）:

| 項目 | study-geoai の README | 再実装 | 許容誤差 |
|---|---|---|---|
| 区内のシーン | 53,948 | 53,948 | 0 |
| 使った行 | 32,593 | 32,593 | 0 |
| 無電柱化済の割合 | 11.6% | 0.1159 | 0.001 |
| すべて架空線ありの精度 | 0.884 | 0.8841 | 0.001 |
| AUC（ランダムな 5 分割） | 0.849 | 0.8491 | 0.01 |
| 精度 | 0.905 | 0.9049 | 0.01 |
| 電柱と電線を足した AUC | 0.988 | 0.9875 | 0.01 |
| 係数: 道路照明、緑、車道の幅、色、左の歩道、右の歩道 | -0.999、+0.674、-0.421、+0.144、-0.036、-0.009 | 同じ値（小数 3 桁まで一致） | 0.02 |
| 電柱の数の係数 | -5.9 | -5.946 | 0.1 |

14 項目すべてが許容誤差の中に入った。係数が小数 3 桁まで一致したので、データ、行の条件、ライブラリの版がそろっていると判断できる。5 分割の乱数（`KFold(shuffle=True, random_state=0)`）は study-geoai と同じとは限らないが、AUC と精度は 0.001 以内で一致した。

## まだやっていないこと

- Worker と IntentExecutor から分析の枠を使う経路（どの Intent を分析の枠で動かすか、Observation と `/out` の成果物の受け渡し）。今は `DockerSandbox` を直接呼ぶ参照解の道具だけがある。
- G1 をローカル LLM で解かせること。
- G2〜G4 のデータの固定と参照解。
- 同時に動かす分析のコンテナを 1 つに制限する仕組み（今は運用で守る）。
