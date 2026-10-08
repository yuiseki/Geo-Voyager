# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。実行時の外部依存関係はありません。
テストには pytest が必要です（`python -m pip install pytest`）。

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
`Worker(network=internal_network).execute(intent)` は、Intent の dataset_ids が
`("yuiseki/jp-admin-2026-09",)` であることを確認し、SkillLibrary から固定UUIDの Skill を取得して
Worker image の Control Primitives を使い東京23区の人口最大の1区を取得します。それ以外の Dataset 指定は拒否します。
Gateway を通じて取得した結果を stdout に出し、`strip()` して Observation 1件を返します。
Intent の text の解釈や LLM によるコード生成は行いません。
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
非0終了は `subprocess.CalledProcessError`、30秒の timeout は `subprocess.TimeoutExpired` になります。
timeout 時は専用の一意なコンテナ名を指定して強制削除します（削除コマンドは最大5秒）。
通常終了時は `--rm` でコンテナを削除します。

実行制約は UID/GID 65534、read-only root filesystem、
`/tmp:rw,noexec,nosuid,size=16m` の tmpfs、cap-drop ALL、no-new-privileges、
memory 128 MiB、CPU 1、PID 128、network none です。
bind/volume mount と Docker socket の共有は行いません。コードは host 上では実行しません。
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


## Worker.execute の固定人口最大区分析

事前 build 済みの `geo-voyager-worker:duckdb-1.5.6` と、internal network 上で
`gateway:8000` として到達できる登録済み行政区 Dataset の Gateway を使用します。
`DockerSandbox` の network は既定で `none` です。指定した network は Docker inspect で
internal であることを確認し、通常の external bridge を指定すると失敗します。
network 以外の sandbox 制約は同じです。

```python
from geo_voyager.intent import Intent
from geo_voyager.worker import Worker

intent = Intent(
    text="東京都23区で人口が最も多い区と人口を求める",
    dataset_ids=("yuiseki/jp-admin-2026-09",),
)
observations = Worker(network="既存のinternal network名").execute(intent)
print(observations[0].text)
```

`skill_library/72c549dd-e449-4bef-97f1-e3a2eab27d64/code.py` の Skill は Control Primitives から行政区域 relation を取得し、
`area="東京都23区"` で取得した行を population 降順・LIMIT 1で選択します。
Intent の dataset_ids は固定分析の対象確認と Gateway URL の組み立てに使用します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_worker_image.py integration/test_worker_population.py -q -s -W error
```

integration test は実験用の Gateway / internal network を作り、実際の
`Worker.execute(intent)` を呼び出します。実データで得た Observation は
「東京都23区で人口が最も多い区は世田谷区で、人口は943664人である」でした。
これは登録済み行政区 Dataset に収録された2020年国勢調査人口です。
終了時には実験用 container / network を削除します。


## Control Primitives と Skill Library

`geo_voyager/control_primitives/` は検証済みの3つの基礎操作を提供します。

- `connect_duckdb()`: sandbox 用の DuckDB 接続。既存の extension 設定・LOAD を維持します。
- `dataset_url(dataset_id)`: 対応する行政区 Dataset id を Gateway URL に変換します。
- `load_admin_units(dataset_id, connection, *, area=None)`: Gateway の Parquet を読み、code5・name・population の relation を返します。

Primitive が意味的な AOI を解決します。`area=None`（既定値）は全行政区域、
`area="東京都23区"` は23区の relation を返します。未対応 area は読み込み前に `ValueError` です。
東京23区を特定する行政コード知識は `load_admin_units.py` の内部だけに保持しています。
人口最大・最小の選択は Skill が行います。
DuckDB 接続を引数で渡すことで、Skill が接続の終了まで管理します。

Control Primitives は各機能を `connect_duckdb.py`、`dataset_url.py`、
`load_admin_units.py` に分割し、`__init__.py` から再公開しています。

`Skill(id, description, code)` の id は `uuid.UUID` です。Skill 名はありません。
`SkillLibrary(root=None)` は既定でリポジトリ直下の `skill_library/` を使用し、
`get(skill_id)` は UUID またはその文字列表現を受け取ります。
`all()` は直下の UUID ディレクトリだけを列挙し、`code.py` と
`description.txt` が両方あるものを UTF-8 で読み込みます。
`vectordb/`、不正な UUID、必須ファイルが欠けたディレクトリは一覧から除外します。
存在しない・不完全な Skill の `get()` は `KeyError`、不正な id は `ValueError` です。
`add(skill)` は Skill の id を使い、新しい UUID ディレクトリに code と description を
UTF-8 で保存します。新規 Skill は `Skill(id=uuid4(), description=..., code=...)` として
呼び出し側で UUID を指定します。既存 UUID は `FileExistsError` で拒否し、上書きしません。
実行の成功判定や Worker からの自動保存は行いません。

```text
skill_library/
  vectordb/
    .gitkeep
  72c549dd-e449-4bef-97f1-e3a2eab27d64/
    code.py
    description.txt
  e722f367-1ff1-4796-89a3-48cfd1dfcb68/
    code.py
    description.txt
```

`vectordb/` は Git でディレクトリを保持するための空の `.gitkeep` のみです。
最初の Skill の description は「行政区域の集合から人口が最も多い区域と人口を求める」です。
code は AOI指定済みの relation から人口降順で1件を選択し、stdout を生成します。
区名・人口の答えは埋め込まず、取得した行から生成します。

Worker は `geo_voyager/skills.py` に固定した UUID を `SkillLibrary.get()` に渡し、
Intent の Dataset id と読み込んだ Skill.code を sandbox の stdin に送ります。
image には Control Primitives を配置しており、Skill は host 側の filesystem から
読み込みます。host filesystem はコンテナに mount しません。
23行・人口合計を確認する既存実験スクリプトも接続 Primitive を再利用します。
LLM による Skill 選択、検索、Vector DB は実装していません。

## Critic

`Critic.check(intent, observations)` は Intent の要求した調査結果が Observation に
回答されているかだけを判定します。仮説の正否や結果の望ましさは評価しません。
戻り値は immutable な `Critique(success: bool, reason: str)` です。

Observation が0件、または本文を strip するとすべて空の場合は、LLM を呼ばず失敗を返します。
それ以外は既存の `LlamaClient` に Intent.text と Observation.text の一覧だけを渡します。
自由文の2行「判定: 成功/失敗」「理由: ...」を読み、行数・ラベル・判定値・非空理由を確認します。
不正な形式は `ValueError` になります。structured output は使用しません。
Worker や SkillLibrary.add との自動接続はありません。

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

## SkillCandidate と成功時の保存

`SkillCandidate(code, description)` は frozen dataclass で、UUID を持ちません。
`promote(candidate)` は呼び出された時点で uuid4 を生成し、code と description を
そのまま持つ `Skill` を返します。

`Worker.execute_candidate(intent, candidate, critic, skill_library)` は、
Candidate の固定コードを既存の Docker sandbox 内で実行し、stdout から Observation を生成します。
次に `critic.check(intent, observations)` を呼び、success が True の場合だけ
`promote(candidate)` と `skill_library.add(skill)` を実行します。
戻り値は `(observations, critique)` です。失敗判定の場合は UUID も生成せず、保存しません。
実行・判定が例外になった場合も、その先の昇格・保存には進みません。

```python
from geo_voyager.critic import Critic
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate import SkillCandidate

candidate = SkillCandidate(code=fixed_python_code, description="調査内容の説明")
observations, critique = worker.execute_candidate(
    intent, candidate, critic=Critic(), skill_library=SkillLibrary(),
)
```

code と description は呼び出し側が与えます。既存 Skill を使う `Worker.execute(intent)` は
昇格・保存を行いません。現在の Dataset 制約と sandbox 制約は同じです。
Candidate に対する LLM コード生成、description 生成、検索、Vector DB は実装していません。

## SkillCandidateGenerator

`SkillCandidateGenerator.generate(intent) -> SkillCandidate` は既存のローカル
`LlamaClient` を使い、Intent.text、dataset_ids、利用可能な3つの Control Primitives の
名前・シグネチャ・説明を渡します。DuckDB relation の列と API、必要な import も提示します。
AOIには `load_admin_units(dataset_id, connection, area="東京都23区")` を提示し、
行政コードを推測・生成せず Primitive に地域解決を任せるよう指示します。
prompt と既存の人口最大・最小 Skill は行政コード範囲を持ちません。
Dataset の読み込みは Primitive のみに限定するよう指示し、外部 URL の直接利用を禁止します。
`dataset_id` は実行環境に定義済みの変数を参照し、最終結果を stdout に出すコードを生成します。
既存 Skill の内容は prompt に渡しません。

自由文出力は「説明:」「---」「コード:」と Python code fence の単純形式です。
section 間の空行を許容し、description と code を取り出します。
必須ラベル・区切り・code fence が不正、または本文が空なら `ValueError` です。
Generator はコードを実行・保存せず、UUID も生成しません。

```python
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

candidate = SkillCandidateGenerator().generate(intent)
observations, critique = worker.execute_candidate(
    intent, candidate, critic=Critic(), skill_library=SkillLibrary(),
)
```

実 LLM・Docker・Gateway・Dataset・Critic・保存の確認は明示実行します。
通常の unit test では LLM を mock にします。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_generated_population_skill.py -q -s -W error
```

この integration は一時 Library に保存しており、実 Library には自動追記しません。
開発時の失敗は保存されず、prompt の契約と空行 parser を修正した後の実験で、
東京23区の人口最小として千代田区・66,680人を取得し Critic が成功と判定しました。
承認済み Skill は同じ UUID `e722f367-1ff1-4796-89a3-48cfd1dfcb68` のまま
リポジトリの Library にも保存しています。これは登録 Dataset の2020年国勢調査人口です。
自動 retry、self-repair、複数 Candidate の生成、Skill retrieval、Vector DB、
Planner 全体との E2E 接続は実装していません。

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
Skill retrieval や vectordb には接続していません。

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

### 最小 Skill 検索

`SkillRetriever(library, embedding_client).retrieve(intent, k=1)` は
`SkillLibrary.all()` の description をまとめて embedding し、続いて
`Intent.text` を embedding して cosine similarity の降順で `list[Skill]` を返します。
検索のたびに計算し、保存・Vector DB・Worker への自動接続は行いません。
空の Library は空リスト、非正の k・ゼロベクトル・次元不一致は例外です。
同点では Library の列挙順を維持します。

実モデルの確認では人口最大・最小の両 Intent に対して人口最小 Skill が上位でした。
embedding 類似度は Skill が要求に適合する保証ではありません。

実モデルでの検索確認は通常の unit test と分離しています。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_skill_retriever_llama.py -q -s
```

### Skill の適合性による選択

`SkillSelector(llm_client=None).select(intent, skills) -> Skill | None` は既存の
ローカル LLM に Intent.text と候補の UUID / description だけを渡します。
code・Dataset ID は渡しません。類似度順位で自動決定せず、最大/最小・対象・
集計方法・出力内容が Intent に適合するか判断させます。候補1件でも判定し、
候補0件は LLM を呼ばず `None` を返します。

LLM の返答は `選択: UUIDまたはなし` と `理由: ...` の2行に限定し、
不正形式・不正 UUID・候補外 UUID は `ValueError` にします。
Worker / SkillCandidateGenerator にはまだ接続していません。

通常の unit test は LLM を mock しています。実モデル確認は別途実行します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_skill_selector_llama.py -q -s -W error
```

既存2件の Skill を最小人口 Skill が先頭になるよう並べた実モデル確認で、
人口最大は最大人口 Skill、人口最小は最小人口 Skill、鉄道駅数は `None` を返しました。
