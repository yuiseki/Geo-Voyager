# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。Skill 検索の実行時依存は DuckDB 1.5.6 です。
テストには pytest が必要です。

`Question(text)`、`Hypothesis(text)`、`Observation(text)`、`Verdict(text)` は空文字列を拒否します。
`Intent(text, dataset_ids)` は空の text と空の dataset_ids を拒否します。
`dataset_ids` は1件以上の非空 id を持つ tuple です。1 Intent は1 measurable output とし、
必要なら空間結合や集計のために複数 Dataset を使えます。
`Planner().plan(question)` は、既存 k8s の llama.cpp に疑問を送り、
自由文の返答を `strip()` して Hypothesis 1件をリストで返します。
空の返答は拒否します。
接続先は `http://10.108.45.102:8080/v1/chat/completions`
（`knative-pool/llama-server`、モデル名 `gvt-llm`）です。
HTTP には標準ライブラリを使用し、structured output は使用しません。
`Planner().plan_intents(hypothesis, dataset_graph)` は、同じ llama.cpp に仮説と
登録済み Dataset の id・description を短いテキストで送り、
利用可能な Dataset の範囲内で調査を作るよう依頼します。
空の Dataset Graph は LLM 呼び出し前に拒否します。Dataset の選択ロジックはありません。
3〜5件程度の最小調査単位を、以下の簡易 YAML で返すよう依頼します。

```yaml
調査項目: 23区ごとの推計人口を算出する
利用データセット:
  - yuiseki/jp-admin-2026-09
  - yuiseki/worldpop-jp-2026-01
---
調査項目: 次の調査内容
利用データセット:
  - yuiseki/ekidata-jp
```

返答を `---` で分割して `strip()` し、空ブロックを除いた `list[Intent]` を返します。
各ブロックは「調査項目:」「利用データセット:」に続く
半角空白2つと `- ` の Dataset リストだけを許可し、
`Intent.from_block()` で `text` と `dataset_ids` に分離します。
YAML ライブラリや汎用 YAML parser、schema 制約は使用しません。
返された各 id は必ず `DatasetGraph.get()` で確認し、1件でも未登録なら `KeyError` になります。
この確認は Dataset の存在だけを保証し、調査内容とデータの意味的な整合性は検証しません。
全ブロックが空なら拒否します。Intent の実行可能性は検証しません。
`Worker(network=internal_network).execute_candidate(intent, candidate, library)` は、コードが呼ぶ Skill をリンクして
Docker sandbox で実行します。dataset_ids は1件だけを許可し、`dataset_id` としてコードに注入します。
stdout を `strip()` して Observation 1件を返します。保存はしません。
`IntentExecutor` が Skill の検索、生成、実行、repair、判定、保存をつなぎます。
`Planner().judge(hypothesis, observations)` は、入力によらず
「仮説はまだ十分に検証されていない」という Verdict 1件を返します。

```python
from geo_voyager.datasets import load_dataset_graph
from geo_voyager.planner import Planner
from geo_voyager.question import Question

planner = Planner()
hypotheses = planner.plan(Question("東京23区でコンビニの分布はどうなっている？"))
intents = planner.plan_intents(hypotheses[0], load_dataset_graph())
print(intents)
```

unit test は LLM client・HTTP・Docker プロセスを mock にしており、実モデルや Docker を起動しません。
上の使用例は手動確認用で、`plan()` と `plan_intents()` で
実モデルへのリクエストが各1回発生します。

テスト実行（環境にインストール済みの外部 pytest プラグインを読み込みません）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -W error
```

## Dataset Graph

公開 Dataset Card と Files を2026-10-08に調査し、5件のメタデータを
`geo_voyager/datasets.py` の静的 catalog に登録しています。
各項目は出典 Dataset URL を持ち、コメントのリビジョン SHA から
`<URL>/blob/<SHA>/README.md` と `<URL>/tree/<SHA>` で調査根拠を確認できます。
由来は description、収録内容は contents に記載しています。
データ本体は読み込まず、Hugging Face API の実行時呼び出しもありません。
`plan_intents()` のプロンプトに id・description を渡します。Worker は変更していません。

```python
from geo_voyager.datasets import load_dataset_graph

graph = load_dataset_graph()
dataset = graph.get("yuiseki/jp-admin-2026-09")
print(dataset.temporal_coverage)
print([dataset.id for dataset in graph.all()])
```

`DatasetGraph.register(dataset)` で登録、`get(id)` で取得、`all()` で一覧を返します。
未登録 id の取得は `KeyError` になります。同じ id の登録は置き換えます。
登録した5件の間に公開 Card で派生関係は確認できなかったため、edge は持ちません。

- [osm-japan-src-2026-08](https://huggingface.co/datasets/yuiseki/osm-japan-src-2026-08): 2026-08-31の日本OSM固定スナップショット。
- [mlit-toshi-keikaku-jp](https://huggingface.co/datasets/yuiseki/mlit-toshi-keikaku-jp): 国交省の2025年度都市計画決定GIS。層別の収録範囲とCardの利用条件を記録。
- [jp-admin-2026-09](https://huggingface.co/datasets/yuiseki/jp-admin-2026-09): 2026-09の行政名・コードと2020年国勢調査の境界・人口を結合。
- [ekidata-jp](https://huggingface.co/datasets/yuiseki/ekidata-jp): 駅データ.jpの無料版。新幹線駅は未収録で、独自利用規約。
- [worldpop-jp-2026-01](https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01): 2015〜2030年の日本人口推計・予測ラスターとCOG、ファイルメタデータ表。

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
bind/volume mount と Docker socket の共有は行いません。例外は分析の枠（`ANALYSIS_PROFILE`）で、固定した分析データを `/data` に読み取り専用で、空の出力ディレクトリを `/out` に書き込み可でマウントします（[docs/analysis_sandbox.md](docs/analysis_sandbox.md)）。コードは host 上では実行しません。
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


## Control Primitives と Skill Library

`geo_voyager/control_primitives/` は検証済みの4つの基礎操作を提供します。

- `connect_duckdb()`: sandbox 用の DuckDB 接続。既存の extension 設定・LOAD を維持します。
- `dataset_url(dataset_id)`: 対応する行政区・駅 Dataset id を Gateway URL に変換します。
- `load_admin_units(dataset_id, connection, *, area=None)`: Gateway の Parquet を読み、code5・name・population の relation を返します。
- `load_stations(dataset_id, connection)`: Gateway の駅 Parquet を読み、name・latitude・longitude の relation を返します。

Primitive が意味的な AOI を解決します。`area=None`（既定値）は全行政区域、
`area="東京都23区"` は23区の relation を返します。未対応 area は読み込み前に `ValueError` です。
東京23区を特定する行政コード知識は `load_admin_units.py` の内部だけに保持しています。
人口最大・最小の選択は Skill が行います。
DuckDB 接続を引数で渡すことで、Skill が接続の終了まで管理します。

Control Primitives は各機能を `connect_duckdb.py`、`dataset_url.py`、
`load_admin_units.py`、`load_stations.py` に分割し、`__init__.py` から再公開しています。

Skill と Skill Library は [下の節](#skill-library名前付き関数voyager-型) にあります。

## Critic

`Critic.check(intent, observations)` は Intent の要求した調査結果が Observation に
回答されているかだけを判定します。仮説の正否や結果の望ましさは評価しません。
戻り値は immutable な `Critique(success: bool, reason: str)` です。

Observation が0件、または本文を strip するとすべて空の場合は、LLM を呼ばず失敗を返します。
それ以外は既存の `LlamaClient` に Intent.text と Observation.text の一覧だけを渡します。
自由文の2行「判定: 成功/失敗」「理由: ...」を読み、行数・ラベル・判定値・非空理由を確認します。
不正な形式は `ValueError` になります。structured output は使用しません。
IntentExecutor が実行の後に Critic を呼び、成功のときだけ新しい関数を Skill として保存します。

```python
from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation

intent = Intent("東京都23区で人口が最も多い区と人口を求める", ("yuiseki/jp-admin-2026-09",))
result = Critic().check(intent, [Observation("世田谷区、943664人")])
print(result.success, result.reason)
```

unit test は LLM を mock します。実ローカル LLM の2例は明示実行します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_critic_llm.py -q -s -W error
```

実モデルでは「世田谷区、943664人」は成功、
「23区の人口データを取得した」は区名・人口の回答がないため失敗になりました。

## SkillCandidateGenerator

`SkillCandidateGenerator.generate(intent) -> SkillCandidate` は既存のローカル
`LlamaClient` を使い、Intent.text、dataset_ids、利用可能な4つの Control Primitives の
名前・シグネチャ・説明を渡します。行政区域と駅の relation の列・API・必要な import を提示し、Primitive 名を変更しないよう指示します。
`aggregate(expression)` と `avg(population)`、集計後の `fetchone()[0]` も提示します。
AOIには `load_admin_units(dataset_id, connection, area="東京都23区")` を提示し、
行政コードを推測・生成せず Primitive に地域解決を任せるよう指示します。
prompt と既存の人口最大・最小 Skill は行政コード範囲を持ちません。
Dataset の読み込みは Primitive のみに限定するよう指示し、外部 URL の直接利用を禁止します。
`dataset_id` は実行環境に定義済みの変数を参照し、最終結果を stdout に出すコードを生成します。
既存 Skill の内容は prompt に渡しません。

自由文出力は「説明:」「---」「コード:」と Python code fence の単純形式です。
section 間の空行を許容し、description と code を取り出します。
必須ラベル・区切り・code fence が不正、または本文が空なら `ValueError` です。
Generator はコードを実行・保存しません。`generate(intent, skills)` に検索した Skill を渡すと、それを呼んでよいことをプロンプトに書きます。

```python
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

candidate = SkillCandidateGenerator().generate(intent, skills)
observations = worker.execute_candidate(intent, candidate, library)
```

通常の unit test では LLM を mock にします。（2026-10-08 に行った、生成した Skill を UUID で保存する実験の記録は、Skill の作り直しの前のもので、その integration テストは削除した。）

AOI対応後の実データ確認では、`area=None` は1,918行政区域、
`area="東京都23区"` は23区域を返しました。
既存の最大人口 Skill は世田谷区・943,664人、最小人口 Skill は千代田区・66,680人を維持しています。
実 LLM の生成 Candidate も AOI指定を使用し、行政コード範囲を含まずに人口最小を取得して
Critic の成功判定まで確認しました。この確認で生成された Skill は一時 Library のみに保存しています。

## EmbeddingClient

`EmbeddingClient(base_url, model).embed(texts: list[str]) -> list[list[float]]` は
標準ライブラリで llama.cpp の OpenAI互換 `POST /v1/embeddings` を呼びます。
constructor に server root または `/v1` までの base URL と model name を渡します。
リクエストは model、input 配列、`encoding_format="float"` を使用します。
レスポンスは index 順に並べ、入力順の float ベクトルを返します。

空の texts、data 件数の不一致、不正・重複・欠落 index、空 embedding、
非数値・非有限値、次元数の不一致は `ValueError` です。
HTTP error と不正 JSON の例外はそのまま呼び出し元へ伝えます。
EmbeddingClient は Skill の説明と Intent の文の embedding に使います（`SkillRetriever`）。

```python
from geo_voyager.embedding_client import EmbeddingClient

client = EmbeddingClient(
    base_url="http://10.105.167.163:8080",
    model="granite-embedding",
)
vectors = client.embed(["人口が最も多い区を調べる。", "人口が最も少ない区を調べる。"])
```

2026-10-08に既存 `default/embedding-server` を読み取り専用で確認しました。
model alias は `granite-embedding`、モデル実体は
`granite-embedding-97m-multilingual-r2.f16.gguf`（pooling cls）です。
実 endpoint は `http://10.105.167.163:8080/v1/embeddings` でした。
日本語2文の1回のbatchリクエストで384次元のベクトルが2件返り、すべて有限値でした。

unit test は HTTP を mock にします。integration は明示実行し、
次の環境変数がない場合は skip します。環境変数はテストが constructor に渡すためのものです。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_embedding_llama.py -q -s -W error
```

## Skill Library（名前付き関数、Voyager 型）

2026-10-10 に、MineDojo/Voyager の Skill library に合わせて作り直した。それまでの UUID ごとのトップレベルのスクリプト、DuckDB vss の index、Skill を 1 件選んで丸ごと再実行する Selector は廃止した。設計と経緯は [docs/skill_library.md](docs/skill_library.md)。

- Skill は、import とトップレベルの関数 1 つ（docstring つき）だけのコード（`geo_voyager/skill_function.py` の `parse_skill`）。関数名で呼ばれ、docstring が説明になる。
- `SkillLibrary(root)`（`geo_voyager/skill_library.py`）は Skill を名前で保存し、同じ名前を保存し直すと前の版を残す（`<名前>/v1/code.py`、`v2/` ...）。保存されていない Skill を呼ぶ Skill は拒否する。
- `link(program, library)` は、プログラムが呼ぶ Skill を呼び先までたどり、呼ばれる側を先にプログラムの前に並べる。Worker は実行の前にこれを行い、失敗の行番号はプログラムの行で返す。
- `SkillRetriever(library, embedding_client)` は、Skill の説明の embedding（版ごとに保存）と Intent の文の cosine で上位 k 件を返す。
- `IntentExecutor(retriever, worker, generator, critic, skill_library, repairer=None, semantic_repairer=None)` は、上位の Skill を Generator に見せ、生成コード（Skill を呼んでよい。新しい関数は 1 つまで）を Skill をリンクして実行し、失敗なら最大 2 回 repair し、Critic が成功としたら新しい関数を Skill として保存する。結果の `IntentExecution` は、見せた Skill（`retrieved_skills`）、呼んだ Skill（`called_skills`）、保存した Skill（`learned_skill`、`名前@v版`）を持つ。
- リポジトリの `skill_library/` には、v0.1.0 の最初の 6 Skill と同じ目的の関数（`most_populous_area`、`least_populous_area`、`top_areas_by_population`、`total_population`、`count_station_records`、`northernmost_station`）を置いた。

## Registered geographical services

`Service(id, description, base_url, protocol)` と `ServiceGraph.register/get/all` を追加しました。
`load_service_graph()` は overpass / nominatim / valhalla / taginfo の正確な HTTPS origin と、
検証用 YuisekinGeoSPARQL `http://geosparql:3030` を登録します。未知 ID は KeyError です。
`*.yuiseki.net` wildcard は許可しません。HTTP User-Agent は
`Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)` です。
この登録は探索用 metadata であり、Worker からの通信許可は別途 Gateway で制御します。

Service Gateway は `GET/POST /services/{service_id}/{path}?query` を提供します。
登録 origin を service_id から解決し、protocol ごとの read-only API path/method だけを許可します。
Nominatim / Taginfo は GET、Overpass interpreter・Valhalla route/locate・GeoSPARQL query は GET/POSTです。
任意URL・URL override・path traversal・PUT/PATCH/DELETE・administrative endpoint・SPARQL update media typeを拒否します。
User-Agent は Gateway 側で固定し、Worker の Host/Authorization 等は転送しません。
redirect は追跡もLocation転送もしません。upstream timeout 15秒、request body 64KiB、response 4MiBです。
既存 Dataset GET/HEAD も同じhandlerに渡せます。

Worker image は汎用 Primitive `call_service(service_id, *, path="", params=None, body=None, content_type=None) -> str`
を持ちます。登録IDを検証して Gateway にだけ HTTP request を送ります。bodyなしはGET、bodyありはPOSTです。
Overpass / routing / OSM等のクエリの意味はPrimitiveへ埋め込んでいません。
`Intent(text, service_ids=(...))` はDatasetなしで実行でき、Datasetとの併用も可能です。
現在Datasetは最大1件です。Workerは実行のみ、Critic・保存・index upsertはExecutorが担当します。
実DockerでGateway経由Taginfo成功と4公開サービスへの直接TCP接続不可を確認しました。
GeoSPARQLへの直接接続拒否と SPARQL SERVICE の無効化も、実pinned graphを起動するE2Eで確認しています。

### Service-aware candidate generation

`SkillCandidateGenerator` advertises the declared registered Service IDs, protocols,
and descriptions, together with `call_service()`. When no Service IDs are declared,
it exposes all five registered services. Origin URLs are resolved by
the Gateway, not exposed as request targets to generated code. Service-only
Intents use `service_ids=(...)` without an artificial Dataset; Dataset Intents
continue to use the existing DuckDB primitives. Service query languages and API
parameters are generated by the model, rather than encoded in primitives.

### Explicit service-learning integration

```bash
docker build -t geo-voyager-geosparql:jena-6.2.0 ../YuisekinGeoSPARQL/fuseki
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  integration/test_service_learning.py -q -s -W error --import-mode=importlib \
  --basetemp=/tmp/geo-service-learning-$(cat /proc/sys/kernel/random/uuid)
```

Each scenario uses its own empty temporary Library. After Critic success the new function is saved as a
named Skill; the same Intent is then retrieved again, and the generated code is expected to call the saved
Skill instead of rewriting it (rewritten for the named-function Skills on 2026-10-10, not yet run since). Critic still checks only Intent
completion; its prompt explicitly forbids inventing missing answers from external
knowledge, and its control flow and success-only promotion remain unchanged. Generated requests use
registered services only; no tag answer or country object ID is supplied in the
prompt. Registry descriptions contain API/schema metadata and abstract protocol
syntax, rather than concrete geographic queries. Those queries remain model
output. Service-only generation explicitly sets `temperature=0.2` and
`chat_template_kwargs.enable_thinking=true`, `reasoning_budget_tokens=1024` and
`max_tokens=3072` per request. Dataset generation retains its existing defaults; the Critic uses temperature zero. An explicit system message requests the strict description/code
layout and only the first description label is assistant-prefilled; malformed response formats are rejected. Generated-code execution failures use the bounded repair loop described below. These settings do not
guarantee that generated code succeeds. No model or Kubernetes configuration is changed.

The GeoSPARQL test reads only manifest-listed, SHA-256-verified pinned TTL files
from the existing sibling repository. Its server runs on a separate isolated
internal network shared only with the Gateway. The Gateway also joins the Worker
internal network and an external network. GeoSPARQL has no Internet egress, and
SPARQL `SERVICE` is disabled using a Fuseki context setting. Its data bind mount
is read-only and belongs only to the test origin server; Worker and Gateway have
no host mounts. Created containers and networks are removed in `finally`.

Protocol metadata references: [Taginfo API](https://taginfo.openstreetmap.org/taginfo/apidoc),
[Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL),
[Fuseki context](https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html),
[SPARQL JSON results](https://www.w3.org/TR/sparql11-results-json/),
[llama.cpp request options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
[reasoning-budget request handling](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp).

[3本の実サービス学習・再利用結果、UUID、生成 Skill code / description](docs/service_learning.md) を記録しています。

Generated Python syntax/runtime errors are returned by `Worker` as bounded,
redacted `ExecutionFailure` values. The container wrapper reserves exit code 73
for these errors. Docker startup/daemon failures still raise exceptions. Captured
stdout and stderr are each limited to 8 KiB; container environment values are
redacted, and failure diagnostics omit sensitive/environment-dump lines.

`IntentExecutor` repairs generated-code failures with `SkillCandidateRepairer`
at most twice (three executions total). Repair receives the original Intent,
registered resources and Primitive contracts, Candidate and bounded diagnostics.
Critic only checks executable Observations. Exhaustion returns `failure` with an
unsuccessful critique and never promotes or saves the Candidate. Infrastructure
exceptions remain exceptions. Existing Skill failures can fall back to generation.

`IntentExecution.attempts` preserves original code, Observations and failure for
all selected-Skill, initial-Candidate and repaired-Candidate executions in order.
`selected_skill_critique` continues to describe the selected Skill only; `critique`
describes the adopted/final result. Failed executions have no Critic verdict.

`Planner.plan(goal: str)` (or `plan_goal`) decomposes a Goal into ordered,
strictly parsed Intents using registered Dataset/Service metadata. The original
`plan(Question)` API still returns Hypotheses. `GoalExecutor` executes the plan
sequentially, stops on a failed step, and applies final Critic to all accumulated measurements and the final answer.
Each later Intent receives earlier Observations as `previous_observations`;
Worker exposes their text as `list[str]` and the current `intent_text` in the
container. Generated/reused code reads these runtime values, rather than fixing
previous answers into its source. No geographic decomposition is hardcoded.


Goal plans contain only `調査項目`, `利用データセット`, and `利用サービス`.
Lists accept registered IDs or `[]`; unknown IDs and extra fields fail explicitly.
Blocks are separated by `---` or by the next unambiguous `調査項目:` header.
A local aggregation can declare both lists empty, but is valid only after an
external step. Such an Intent has `requires_context=True`; Worker and Executor
require actual previous Observations before execution. External reads still
require registered resources. The original Intent validation stays unchanged
for Intents without that explicit context requirement.

Generator/Repairer see the shape of previous JSON outputs, not answer values.
The sandbox supplies the actual `previous_observations` and `intent_text` at
runtime. A collection-measurement Skill chooses its target from these runtime
inputs, so later positional Intents can reuse the same saved code. Critic receives
the prior data and a mechanically resolved list-position reference, so it does
not have to recount a long JSON list to identify the requested target. Required
entity IDs and expected collection cardinality must be verified rather than
replaced by placeholder values. Protocol/schema contracts stay in Service
metadata; `call_service` remains a generic Gateway client.

Registered upstream HTTP errors expose only a bounded, redacted diagnostic
body (8 KiB) to the Worker. Redirects remain rejected. Service metadata also
states the actual Taginfo data array and SPARQL results/bindings/value envelope,
so Generator and Repairer can interpret raw text responses without adding
service-specific parsing to the Primitive. This allows repair of an
actual query error without opening a new origin or forwarding arbitrary headers.
Repair preserves the original reusable operation description, repairs the
failure cause, and does not introduce answer constants or new resources.

The explicit burger integration uses an empty temporary Library, an intentional
first-Candidate syntax fault, real LLM repair, real service requests and Critic.
Learned measurement code is reused for subsequent targets. All 23 measurements
are independently checked by fresh per-area Overpass requests after the Goal
has completed; this verification code never enters any generation/repair prompt
or Skill Library. No fixed answer is embedded in the tests.

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  integration/test_burger_goal.py -q -s -W error --import-mode=importlib \
  --basetemp=/tmp/geo-burger-goal-$(cat /proc/sys/kernel/random/uuid)
```

This is one sequential plan, with at most two repairs per generated Candidate.
Critic checks task completion; it is not a substitute for independent numerical
verification. There is no guarantee of success for every LLM generation.

[複合 burger Goal の実測レポート（全25 Intent、失敗code/stderr、repair差分、UUID再利用、23区集計）](docs/burger_goal_learning.md) を記録しています。
