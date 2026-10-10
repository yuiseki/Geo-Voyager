# 分析用 sandbox の検討（study-geoai-algo-py の水準の分析を実行できるようにする）

2026-10-10。Geo-Voyager の究極のゴールは、[study-geoai-algo-py](https://github.com/yuiseki/study-geoai-algo-py)（Claude Code が開発した、台東区と東京 23 区の実データで GeoAI のアルゴリズムを一通り動かした記録。38 実験）でやっているデータ分析、検定、可視化、最適化を、ローカル LLM にやらせることである。そのために、まず生成コードを実行する sandbox が、何を満たす必要があるかを調べた。この文書は検討で、まだ何も実装していない。

次の段階では、study-geoai の実験を Goal と oracle に変える（各実験の README に、Claude Code が得た数字が残っている）。sandbox の設計は、その Goal を実行できることを基準にする。

## 0. 決まったこと（2026-10-10、お嬢様の判断）

- Geo-Voyager は study-geoai-algo-py から完全に独立させる。コードもデータも使わない（パッケージを入れない、キャッシュを複製しない、study-geoai 側も変えない）。study-geoai は、README に書かれた数字を oracle の出典として使うだけ。データの取得と固定、Primitive は、Geo-Voyager が自前で持つ。
- データは、Geo-Voyager が版を固定して取得したものを、分析のコンテナに読み取り専用でマウントする（2.3 の案 A）。README の「bind/volume mount は行わない」方針は、この読み取り専用のデータに限って変える。
- 分析の枠のメモリは 8GB（swap なし）。CPU 4、実行時間 600 秒、同時に 1 つは推奨のまま（明示の判断はまだ）。

以下の 2.1、2.3、2.4、3 には、独立させる前の案（study_geoai のパッケージとキャッシュを使う案）が残っている。決まったことと食い違うところは、上の決定が優先する。食い違いを直した節は「（独立版）」と書いた。

## 1. 今の sandbox と、study-geoai が必要とするもの

| 項目 | 今の Geo-Voyager の Worker | study-geoai の実験 | 出典 |
|---|---|---|---|
| Python ライブラリ | DuckDB 1.5.6（httpfs、spatial）だけ（`docker/worker/Dockerfile`） | numpy、scipy、scikit-learn、statsmodels、lightgbm、xgboost、catboost、shap、verde、networkx、ortools、highspy、pyarrow、rasterio、matplotlib、DuckDB 1.5.5 以上。任意で tabpfn、timesfm（torch） | study-geoai の `pyproject.toml` |
| メモリ | 128MB。DuckDB は 64MB | 重い処理は `MemoryMax=8G` で囲む。DuckDB は 4GB | `docker_sandbox.py`、study-geoai `docs/setup.md` |
| CPU | 1 | 制限なし（ホストは 32 コア） | |
| 実行時間 | 30 秒で打ち切り | 数分以上のものがある（AgERA5 の初回の取得は約 10 分） | study-geoai `docs/setup.md` |
| 書ける場所 | `/tmp` の tmpfs 16MB（noexec） | `/tmp/study-geoai/` にキャッシュ（今は 395MB）、DuckDB の spill、`output/` に地図の PNG | `aoi.CACHE_DIR`、`db.SPILL_DIR` |
| ネットワーク | 外へ出られない。Gateway 経由で、登録した 5 サービスと 2 つの Dataset（Range の中継あり）だけ | Hugging Face（コミット固定の Parquet）、Overture の S3（STAC で絞る）、z.yuiseki.net/static/ のミラー、source.coop の PMTiles、FAO FERSPAS の COG、nominatim.yuiseki.net。すべて Range 要求で必要な行と列だけ読む（CNG） | study-geoai `docs/setup.md` の「使った出どころ」 |
| 結果の受け渡し | stdout の JSON 1 行（8,192 バイトまで） | 表、係数、スコア、地図の PNG、ソルバーの解 | |
| 共通のコード | Control Primitives 6 つ（`call_service`、`connect_duckdb`、`load_admin_units` など） | `study_geoai` パッケージ（範囲、読み込み、特徴量、メッシュ、Dijkstra と A*、被覆、施設配置、スケジュール、地図） | study-geoai `src/study_geoai/` |

ホストは 32 コア、メモリ 94GB（swap なし。常駐の LLM などで約 43GB 使用中、利用可能は約 50GB）。swap が無いので、メモリが尽きると機械ごと止まる。コンテナのメモリ上限は必須。

## 2. 層ごとの選択肢と推奨

### 2.1 イメージ

- 推奨: 分析用の別イメージ（例: `geo-voyager-analysis`）を作る。study-geoai の `uv.lock` から書き出した版で依存を固定し、`study_geoai` パッケージも入れる。今の軽い Worker（`geo-voyager-worker:duckdb-1.5.6`）は、今の 22 Goal のために残す。
- 理由: oracle の数字は study-geoai の版で出ている。版を揃えないと、数字の違いがライブラリの違いか LLM の違いか分からない。ortools と highspy の版の組み合わせ（同梱の HiGHS の soname）にも、study-geoai で既に答えがある。
- 任意の torch（tabpfn、timesfm）は最初は入れない。イメージが数 GB 大きくなり、対象の実験も 2 つだけ。

### 2.2 資源

- 推奨: Intent の種類ごとに「資源の枠」を持つ。今の枠（128MB、1 CPU、30 秒）はそのまま残し、分析の枠を足す。
- 分析の枠の初期値の案: メモリ 4GB（swap なし、`--memory-swap` を同じ値に）、CPU 4、実行時間 600 秒、`/tmp` の tmpfs 1GB、PID 512。study-geoai の 8GB は 23 区の重い実験のためで、台東区なら 4GB で足りる見込み（確かめていない）。
- 同時に走らせる分析のコンテナは 1 つ。ホストの空きメモリと、常駐の LLM を守るため。

### 2.3 データの読み方

ここが最大の分かれ目で、3 つの案がある。

| 案 | 中身 | 良い点 | 悪い点 |
|---|---|---|---|
| A. 固定したデータの読み取り専用マウント | study-geoai の読み込みを一度ホストで流して作ったキャッシュ（`/tmp/study-geoai/` 相当）を、版を固定したディレクトリに置き、分析のコンテナに読み取り専用でマウントする。コンテナは外へ出ない | 速い。再現できる（oracle と同じデータを確実に読む）。ネットワークの失敗が混ざらない。安全（外へ出られない） | CNG の読み方（Range で必要な行と列だけ）を LLM が書く練習にならない。今の README は「bind/volume mount は行わない」と書いているので、その方針を変える |
| B. Gateway を Range の中継として広げる | 許可した出どころ（Hugging Face のコミット固定の URL、z.yuiseki.net/static/、Overture の S3、source.coop、FAO）への GET と Range だけを、Gateway が中継する | CNG で読むところから LLM にやらせられる。study-geoai と同じ読み方 | 遅い（初回の取得に分単位）。ネットワークの失敗やキャッシュの不一致が、LLM の誤りと混ざる。Gateway の許可リストと Range 中継の作り込みが要る |
| C. 特徴量を Dataset として登録 | study-geoai の特徴量の表（`features-*.parquet`）を Dataset として Gateway から配る | 今の仕組み（Dataset と Gateway）に乗る | 特徴量を作る部分を LLM がやらなくなる。分析の前半が消える |

- 推奨: まず A で始め、B を後で足す。最初に知りたいのは「ローカル LLM が、分析（モデル、検定、最適化、地図）を組み立てられるか」で、データの取得の失敗をそこに混ぜない方が、どこで詰まるかがはっきりする。データの取得を LLM にやらせるのは、分析が回ってからの段階にする。
- A の注意: `study_geoai` のキャッシュの場所は `tempfile.gettempdir()/study-geoai` で、spill（DuckDB の一時領域）も同じ下に書く。読み取り専用のキャッシュと書ける spill を分ける必要がある（例: キャッシュを `/data/study-geoai` に読み取り専用でマウントし、`study_geoai` 側でキャッシュの場所を環境変数で変えられるようにする）。study-geoai への小さな変更が要る。

### 2.4 Control Primitives の粒度

- 推奨: `study_geoai` の「読み込みと特徴量」（`aoi`、`census`、`overture`、`features`、`mesh`、`osm`、`worldpop`、`ksj` など）と「地図」（`plot`）を Primitive として渡す。「課題そのもの」（`tasks.density` のように、学習用の配列まで作るもの）と「アルゴリズムの実装」（`graph`、`cover`、`facility`、`schedule`）は渡さない。
- 理由: 分析の組み立て（モデルの選択、交差検証の切り方、評価、最適化の定式化）こそ、LLM にやらせたい部分である。アルゴリズムの実装まで渡すと、LLM は呼ぶだけになる。逆に、データの取得まで書かせると、最初の段階で詰まる（2.3 と同じ理由）。
- 実験によっては、自前の実装（`graph` の Dijkstra）そのものが課題なので、Goal ごとに渡す Primitive を選べるようにする。

### 2.5 結果の受け渡し

- 推奨: stdout の JSON（要約の数字）に加えて、成果物のディレクトリを持つ。コンテナの中の `/out`（書ける tmpfs）に、地図の PNG や表を書かせ、実行の後でホストに取り出して、Goal の実行記録に残す。Observation には、成果物の名前と要約の数字だけを入れる。
- 理由: Observation が 8,192 バイトの JSON 1 行という今の前提では、表や図を扱えない。後段の step が前段の表を使うとき（特徴量を作ってから学習する、など）、受け渡しの場所が要る。
- Critic と oracle は、まず要約の数字（R²、係数の符号、最適値など）で判定する。図の判定は後回し。

### 2.6 安全

- 分析のコンテナも、UID 65534、読み取り専用のルート、cap-drop ALL、no-new-privileges、メモリと PID の上限、ネットワークなし（案 A）を保つ。
- 変わるのは、読み取り専用のデータのマウント（案 A）と、書ける `/out` と大きめの `/tmp` だけ。Docker の socket やホームディレクトリは渡さない。

## 2.7（独立版）データ、Primitive、oracle の関係

study-geoai のコードを使わないので、oracle の数字（study-geoai の README）を Geo-Voyager の環境で再現できることを、別に確かめる必要がある。

1. データの準備: Geo-Voyager に、元の出どころ（study-geoai が使ったのと同じ出どころと版。Hugging Face のコミット、Overture のリリース、z.yuiseki.net のミラーなど）から、必要な範囲だけを取得して Parquet に固定するスクリプトを自前で書く。出どころと版は、study-geoai の README と `docs/datasets/` の記述（文書）を読んで合わせる。コードは読まずに書く。
2. 参照解: Claude Code が Geo-Voyager の中に、各 Goal の参照解（分析のコード）を書き、分析のコンテナで動かす。study-geoai の README の数字が許容誤差の中で出れば、データと環境が oracle を再現できると判断する。出なければ、データの定義の違い（特徴量の作り方、除外の条件）を README の記述から探して合わせるか、その Goal を外す。
3. Goal と oracle: 参照解で再現できた数字だけを oracle にする。ローカル LLM の答えは、この oracle と比べる。
4. Primitive: Geo-Voyager が自前で書く。データの読み込み（固定したデータを DuckDB で開く）だけを渡し、特徴量の作り方と分析は LLM に書かせる。地図を描く関数を渡すかは、可視化の Goal を作るときに決める。

study-geoai の README は、データの定義（行、目的変数、特徴量、除外の条件）を文章で詳しく書いているので、コードを読まずに再現できる見込みがある。ただし、Overture の POI の束ね方（`basic_category` を名前の語で束ねる）のように、文章だけでは完全に決まらない定義もある。そうした Goal は、最初の候補から外す。

## 3. 進め方の案

1. 分析用イメージを作り、study-geoai の `uv.lock` と同じ版で import できることをテストで確かめる（`tests/test_env.py` の ortools と highspy の同居も）。
2. 資源の枠を DockerSandbox と Worker に足す（今の枠は変えない）。単体テストで、枠ごとの docker の引数を確かめる。
3. データのマウント（案 A）と成果物の取り出しを足す。最初の Goal の参照解（2.7、Claude Code が Geo-Voyager の中に書く）を分析のコンテナで動かし、study-geoai の README の数字が出ることを確かめる。ここで「環境が oracle を再現できる」ことを、ローカル LLM なしで確かめる。（独立版。当初は study-geoai の `run.py` をそのまま動かす案だった）
4. ここまでできたら、次の段階（study-geoai の実験を Goal と oracle に変える）に進む。

## 4. 決めていただいたこと

- データの読み方: 案 A から始める。
- 分析の枠のメモリ: 8GB。
- study-geoai 側の変更: しない。Geo-Voyager は study-geoai から完全に独立させる（0 節）。
