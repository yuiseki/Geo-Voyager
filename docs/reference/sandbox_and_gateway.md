# Docker sandbox と Gateway

## Docker sandbox

Docker CLI と稼働中の daemon、および事前取得した公式イメージが必要です。

```bash
docker pull python:3.12-slim
```

`DockerSandbox().run(code)` は Python をコンテナの stdin に送り、stdout を文字列で返します。
非0終了は `subprocess.CalledProcessError`、timeout（既定の枠は30秒、分析の枠は600秒）は `subprocess.TimeoutExpired` になります。Worker は timeout をその Candidate の失敗（`TimeoutError`）として返します。
timeout 時は専用の一意なコンテナ名を指定して強制削除します（削除コマンドは最大5秒）。
通常終了時は `--rm` でコンテナを削除します。

実行制約は UID/GID 65534、read-only root filesystem、
`/tmp:rw,noexec,nosuid,size=16m` の tmpfs、cap-drop ALL、no-new-privileges、
memory 128 MiB（swap なし）、CPU 1、PID 128、network none です（既定の枠）。分析の枠は memory 8 GiB（swap なし）、CPU 4、PID 512、`/tmp` 2 GiB、600 秒、network none です。
bind/volume mount と Docker socket の共有は行いません。例外は分析の枠（`ANALYSIS_PROFILE`）で、固定した分析データを `/data` に読み取り専用で、空の出力ディレクトリを `/out` に書き込み可でマウントします（[2026-10-10_analysis_sandbox.md](../reports/2026-10-10_analysis_sandbox.md)）。コードは host 上では実行しません。
`--pull never` により実行時にはイメージを取得しません。

## Docker ネットワーク分離の検証

`integration/` にテスト専用の構成があります。実 Worker や DockerSandbox の
実行設定は変更していません。このネットワーク検証自体では単純な HTTP server を使い、
Dataset Fetch Gateway の検証は別の integration test で行います。

- Worker: user-defined bridge の internal network のみ
- Gateway: internal と external の両ネットワーク
- Origin: external network のみ
- Gateway と Origin: `/tmp` を公開する単純な HTTP server（port 8000）

外部 Internet へのアクセスや host port 公開、volume mount は行いません。
external はテスト用の通常 bridge で、通信先は Origin コンテナだけです。
既存の `python:3.12-slim` を使い、イメージ取得も行いません。

通常の unit test は Docker CLI を mock にします。
実 Docker の検証は明示実行し、default internal と isolated gateway mode を各1回試します。
isolated 非対応の Engine では default のケースだけを実行してください。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_docker_network.py -q -s -W error
# isolated 非対応の場合
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_docker_network.py -q -s -W error -k False
```

Worker→Gateway と Gateway→Origin の HTTP 200、Worker→Origin の DNS名・IP直接通信の失敗、
各コンテナの network 参加状況を確認します。終了・途中失敗時とも、専用の一意な名前の
コンテナと network を削除します。正常終了時は削除後の不存在もテストします。
Docker Engine 29.5.3 で両モードの2件が成功しています。

## 最小 Dataset Fetch Gateway

`geo_voyager.fetch_gateway.make_handler(dataset_graph)` を標準ライブラリの
`HTTPServer` に渡します。API は `GET /datasets/{dataset_id}` と
`HEAD /datasets/{dataset_id}` だけです。id に `/` が含まれていても取得できます。
`DatasetGraph.get()` で登録済み id を確認して、その `Dataset.data_url`（未指定なら `Dataset.url`）だけを使います。
今回の integration test は公開 catalog を使わず、固定の `test/fixed` 1件を登録します。

- GET: upstream body を返す。Range があればそのまま転送。
- HEAD: upstream に HEAD を送り、body は読み込まず返さない。
- Worker の他の header は転送しない。response は Content-Type、Content-Length、
  Content-Range、Accept-Ranges のみを引き継ぐ。
- 未登録 id は404、query parameter は400、POST/PUT/PATCH/DELETEは405。
- redirect は自動追跡せず、Location も返さない。upstream エラーは502。
- upstream HTTP は同期でtimeout 10秒。retry・cache・authentication はない。

テスト用 topology に実装を載せ、external 側の Origin コンテナが固定文字列
`0123456789` を返します。ファイル共有や Internet アクセスはしません。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_fetch_gateway.py -q -s -W error
```

GETは200と全10バイト、HEADは200とbodyなし、Range GETは206と`01234`を確認します。
未登録・変更系・任意URL queryの拒否、Worker→Originの名前/IP直接通信の失敗も確認し、
終了後に全テスト用コンテナ・networkを削除します。
既存の Worker 分析処理や DockerSandbox は Gateway に接続していません。


## 固定 DuckDB Worker 実験

`docker/worker/Dockerfile` は Python 3.12 と DuckDB **1.5.6** を使用します。
`httpfs` / `spatial` は build 時に公式配信元から install し、
`/opt/duckdb/extensions` に保存します。UID/GID 65534 から読み取れます。
runtime は extension 自動 install・autoload を無効にして `LOAD` のみ行い、
署名検証は有効なままです。署名検証の並列スレッドに対応するため、
ユーザー承認により sandbox の PID 上限を32から128へ変更しました。
他の sandbox 制約は維持しています。

```bash
# build と offline LOAD を先に確認する（network none）
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_worker_image.py -q -s -W error
# 成功後、実データを取得する明示的な実験
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_tokyo23_gateway.py -q -s -W error
```

Dataset に任意の1ファイルを指す optional `data_url` だけを追加しました。
`url` は紹介ページとして保持し、行政区 Dataset の `data_url` に固定 revision の
`municipalities.parquet` を登録しています。ファイル一覧や任意 path API はありません。
実験用 Gateway の起動時に、この登録 URL に HEAD を1回送り、
Hugging Face の署名付き CDN 配信先を HTTPS・固定ホスト・X-Xet-Hash と一致する
パスで明示検証して DatasetGraph に登録します。署名付き URL は保存しません。
Gateway はこの登録済み URL のみ使用し、redirect の自動追跡は無効のままです。

Worker は isolated internal network のみ、Gateway は internal + external に接続します。
固定スクリプト `scripts/analyze_tokyo23.py` の接続先は Gateway だけです。
AOI指定の Primitive で code5、name、population のみを取得し、東京23区が23行で
population が整数であることを確認して行数・人口合計を stdout に出します。
geometry は取得しません。LLM は変更していません。

2026-10-08 の実験結果は23行、人口合計 **9,733,276人** でした。
DuckDB から Gateway への HEAD 200 と Range GET 206（3回）、
Worker から Internet への直接接続の失敗を確認しています。
終了後には実験用の container / network を削除します。
