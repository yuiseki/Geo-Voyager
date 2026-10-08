# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。Skill 検索の実行時依存は DuckDB 1.5.6 です。
テストには pytest と、明示セットアップ済みの DuckDB vss extension が必要です（下記参照）。

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
`Worker(network=internal_network).execute_skill(intent, skill)` は渡された Skill を
既存 Docker sandbox で実行します。dataset_ids は1件だけを許可し、`dataset_id` として
コードに注入します。0件・複数件は実行前に拒否します。行政区域・駅とも同じ Worker を使います。
stdout を `strip()` して Observation 1件を返し、既存 Skill の実行では昇格・保存しません。
`IntentExecutor` が検索・選択・既存 Skill 再利用と、該当なしの場合の生成・学習をつなぎます。
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


## Worker.execute_skill による人口最大区分析例

事前 build 済みの `geo-voyager-worker:duckdb-1.5.6` と、internal network 上で
`gateway:8000` として到達できる登録済み行政区 Dataset の Gateway を使用します。
`DockerSandbox` の network は既定で `none` です。指定した network は Docker inspect で
internal であることを確認し、通常の external bridge を指定すると失敗します。
network 以外の sandbox 制約は同じです。

```python
from geo_voyager.intent import Intent
from geo_voyager.worker import Worker
from geo_voyager.skill import SkillLibrary

intent = Intent(
    text="東京都23区で人口が最も多い区と人口を求める",
    dataset_ids=("yuiseki/jp-admin-2026-09",),
)
skill = SkillLibrary().get("72c549dd-e449-4bef-97f1-e3a2eab27d64")
observations = Worker(network="既存のinternal network名").execute_skill(intent, skill)
print(observations[0].text)
```

`skill_library/72c549dd-e449-4bef-97f1-e3a2eab27d64/code.py` の Skill は Control Primitives から行政区域 relation を取得し、
`area="東京都23区"` で取得した行を population 降順・LIMIT 1で選択します。
Intent の1件の dataset_id をコードへ注入し、Primitive が Gateway URL に解決します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_worker_image.py integration/test_worker_population.py -q -s -W error
```

integration test は実験用の Gateway / internal network を作り、実際の
`Worker.execute_skill(intent, skill)` を呼び出します。実データで得た Observation は
「東京都23区で人口が最も多い区は世田谷区で、人口は943664人である」でした。
これは登録済み行政区 Dataset に収録された2020年国勢調査人口です。
終了時には実験用 container / network を削除します。


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
Library 自体は実行を判定しません。Candidate の Critic 成功後だけ Worker が add を呼びます。

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
  befbc141-baad-41bc-abdf-dc34311c3111/
    code.py
    description.txt
  f2d4785a-779a-4927-b75d-65d1e4852ab2/
    code.py
    description.txt
  ccd6a22b-d795-4359-a06a-f2ac214e6a28/
    code.py
    description.txt
  fb0fb79f-10b3-424f-ae27-4d6292f474c4/
    code.py
    description.txt
```

`vectordb/` の Git 管理対象は `.gitkeep` のみです。実行時の `skills.duckdb` は再生成可能な派生物として Git 管理対象外です。
最初の Skill の description は「行政区域の集合から人口が最も多い区域と人口を求める」です。
code は AOI指定済みの relation から人口降順で1件を選択し、stdout を生成します。
区名・人口の答えは埋め込まず、取得した行から生成します。

Worker は呼び出し側から渡された Skill を使い、Intent の1件の Dataset id と
Skill.code を sandbox の stdin に送ります。固定 Skill の選択や Dataset id の固定チェックはありません。
image には Control Primitives を配置しており、Skill は host 側の filesystem から
読み込みます。host filesystem はコンテナに mount しません。
23行・人口合計を確認する既存実験スクリプトも接続 Primitive を再利用します。
検索・選択と Worker の接続は IntentExecutor が担当します。検索 index は DuckDB vss です。

## Critic

`Critic.check(intent, observations)` は Intent の要求した調査結果が Observation に
回答されているかだけを判定します。仮説の正否や結果の望ましさは評価しません。
戻り値は immutable な `Critique(success: bool, reason: str)` です。

Observation が0件、または本文を strip するとすべて空の場合は、LLM を呼ばず失敗を返します。
それ以外は既存の `LlamaClient` に Intent.text と Observation.text の一覧だけを渡します。
自由文の2行「判定: 成功/失敗」「理由: ...」を読み、行数・ラベル・判定値・非空理由を確認します。
不正な形式は `ValueError` になります。structured output は使用しません。
IntentExecutor が既存 Skill・Candidate の両経路で Critic を呼びます。既存 Skill の失敗判定時だけ Candidate 生成へ1回 fallback し、Candidate 成功時だけ保存します。

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

`Worker.execute_candidate(intent, candidate) -> list[Observation]` は、
コードを既存の Docker sandbox 内で実行し、stdout から Observation を生成します。
Worker は Critic・昇格・保存を扱いません。IntentExecutor が結果を検証し、
成功時だけ `promote(candidate)` と `skill_library.add(skill)` を実行します。
失敗判定の場合は UUID を生成せず、保存しません。例外は呼び出し側へ伝播します。

```python
from geo_voyager.skill_candidate import SkillCandidate

candidate = SkillCandidate(code=fixed_python_code, description="調査内容の説明")
observations = worker.execute_candidate(intent, candidate)
```

code と description は呼び出し側が与えるか SkillCandidateGenerator で生成します。
既存 Skill を使う `Worker.execute_skill(intent, skill)` は昇格・保存を行いません。
両経路とも Dataset は1件だけを許可し、既存 sandbox 制約を維持します。検索用 DuckDB vss index を追加しています。

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
Generator はコードを実行・保存せず、UUID も生成しません。

```python
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

candidate = SkillCandidateGenerator().generate(intent)
observations = worker.execute_candidate(intent, candidate)
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
自動 retry、self-repair、複数 Candidate の生成、Planner 全体との E2E 接続は実装していません。
既存 Skill が適合しない場合の生成・実行・成功時保存は IntentExecutor が接続します。

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
EmbeddingClient は Skill の派生 cache と query embedding に利用します。検索 index は DuckDB vss です。

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

### Skill 検索の3層構成

```text
skill_library/
  {uuid}/
    code.py                       # source of truth
    description.txt               # source of truth
    description_embedding.json    # derived cache / gitignore
  vectordb/
    .gitkeep
    skills.duckdb                 # derived index / gitignore
```

`SkillEmbeddingCache(embedding_client, root=library.root).get(skill)` は
実際に embedding へ渡す description の UTF-8 SHA-256、model、format_version=1、
dimensions=384 と非空・有限・非ゼロのベクトルを検証します。正常な cache は API を呼ばず返し、
欠損・不正 JSON・不一致は再生成します。書き込みは同一ディレクトリの一時ファイルから atomic replace します。
code と description の原本を変更しません。

`SkillVectorStore(path=None)` の既定パスは `skill_library/vectordb/skills.duckdb` です。
`sync(library, cache)` は起動時の full sync として UUID / description SHA / model の差分だけ INSERT / UPDATE し、
Library にない UUID は DELETE します。初回は全行投入後に HNSW index を作ります。
新 UUID の `upsert(skill, embedding, model)` は1件だけ INSERT します。既存 UUID の更新は1件だけ UPDATE しますが、
永続 HNSW の古い行が検索候補に残るケースを実テストで確認したため、更新・削除時だけ index を再作成します。
通常の新規学習は incremental INSERT で、全件 embedding や index 再作成は行いません。

```sql
CREATE TABLE skill_embeddings (
    skill_id UUID PRIMARY KEY,
    description_sha256 VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    embedding FLOAT[384] NOT NULL
);
CREATE INDEX skill_embedding_hnsw ON skill_embeddings
USING HNSW (embedding) WITH (metric = 'cosine');
```

`search(query_embedding, k)` は `ORDER BY array_cosine_distance(embedding, ?::FLOAT[384]) LIMIT ?`
で近い順の UUID を返します。k<1、次元不一致、非有限値、ゼロベクトルを拒否します。
HNSW の同点順位は保証しません。

`SkillRetriever(library, embedding_client).retrieve(intent, k=1)` は API を維持し、
constructor で1回 full sync し、起動後は Intent.text を1回だけ embedding して、store.search → library.get で Skill を返します。
retrieve() は Library 全件列挙・sync・description cache 取得・schema 作成を行いません。
空の index でも query を1回 embedding し、検索結果は空リストになります。

学習成功時は IntentExecutor が `SkillLibrary.add(learned)` の後に `retriever.upsert(learned)` を呼びます。
upsert はその Skill の cache を取得・生成し、`store.upsert(skill, embedding, model)` に渡します。
学習した Skill は次の検索で即座に対象になり、正常再利用・Critic 失敗時には upsert を呼びません。
Selector / Critic / 1回だけの fallback と判定 provenance は維持しています。

原本の手動変更・削除は次の起動時 full sync か明示的な `store.sync(library, cache)` で反映します。
起動後の外部ファイル変更を各 query で検出する仕組みはありません。

#### 明示セットアップ

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'duckdb==1.5.6' 'pytest>=8'
.venv/bin/python - <<'PYTHON'
import duckdb
with duckdb.connect() as connection:
    connection.execute("SET custom_extension_repository='https://extensions.duckdb.org'")
    connection.execute("INSTALL vss")
    connection.execute("LOAD vss")
PYTHON
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -W error \
  --basetemp=/tmp/geo-voyager-unit-$(cat /proc/sys/kernel/random/uuid)
```

実行コードは extension の autoinstall / autoload を無効化し、`LOAD vss` だけを実行します。
永続 DB を ATTACH する前に vss を LOAD し、`hnsw_enable_experimental_persistence=true` を設定します。
この設定と検索形式は [DuckDB vss の公式文書](https://duckdb.org/docs/current/core_extensions/vss) に従います。
DB は原本ではなく派生 index です。失った場合は sync で cache から再構築できます。
同時書き込み・モデル移行・HNSW tuning は今回扱いません。

実 embedding と EXPLAIN / 再構築・6 Intent 評価・学習後の再利用は明示実行します。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -s -W error \
  --import-mode=importlib integration \
  --basetemp=/tmp/geo-voyager-integration-$(cat /proc/sys/kernel/random/uuid)
```

### Skill の適合性による選択

`SkillSelector(llm_client=None).select(intent, skills) -> Skill | None` は既存の
ローカル LLM に Intent.text と候補の UUID / description だけを渡します。
code・Dataset ID は渡しません。類似度順位で自動決定せず、最大/最小・対象・
集計方法・出力内容が Intent に適合するか判断させます。候補1件でも判定し、
候補0件は LLM を呼ばず `None` を返します。

LLM の返答は `選択: UUIDまたはなし` と `理由: ...` の2行に限定し、
不正形式・不正 UUID・候補外 UUID は `ValueError` にします。
IntentExecutor が選択結果を Worker に渡し、None または既存 Skill の Critic 失敗の場合に SkillCandidateGenerator を呼びます。

通常の unit test は LLM を mock しています。実モデル確認は別途実行します。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_skill_selector_llama.py -q -s -W error
```

既存2件の Skill を最小人口 Skill が先頭になるよう並べた実モデル確認で、
人口最大は最大人口 Skill、人口最小は最小人口 Skill、鉄道駅数は `None` を返しました。

### 駅 Primitive と6件の初期 Skill

`load_stations(dataset_id, connection)` は `yuiseki/ekidata-jp` の固定 revision
`a33321099406b47338be0d03a4887059473fde0c` にある
`parquet/2026-10-05/station.2026-07-31.parquet` を Gateway 経由で読み、
`name`（station_name）、`latitude`（lat）、`longitude`（lon）を返します。
読み込み・列の正規化だけを行い、集計・最北端判定は Skill に置きます。
DatasetGraph の既存 `data_url` に固定実ファイル URL を追加しました。

file-based Library に人口合計・人口上位5区・全国駅数・最北端駅の4 Skill を追加し、
合計6件にしました。各 Skill は実 DockerSandbox → Gateway → Dataset で実行し、
Critic の成功を確認しています。駅数は収録全レコード数であり、営業状態で絞ったり
同一駅の重複を除いたりしません。Worker は execute_skill に渡された Skill を実行します。

6 Intent の評価は recall@4 が6/6、Selector の正解が6/6でした。
人口最大は Retriever の4位から Selector が選びました。
[UUID・description・実行結果・全順位と cosine 値・再実行コマンド](docs/skill_evaluation.md)
を記録しています。その評価後に、IntentExecutor で既存 Skill の再利用と該当なしの場合の学習を接続しました。検索用 DuckDB vss index を追加しています。

## IntentExecutor: 既知なら再利用、未知なら学習

`IntentExecutor(retriever, selector, worker, generator, critic, skill_library)` に
同じ filesystem Library を検索・保存先として渡します。派生 cache / index は Retriever の起動時 sync と学習時 upsert で反映します。
`execute(intent, k=4) -> IntentExecution` は次の順で処理します。

1. Retriever の top-k Skill を取得し、UUID の順序を保持する。
2. Selector が Intent を完遂できる Skill または None を返す。
3. Skill があれば Worker.execute_skill → Critic と進み、成功なら生成・昇格・保存せず結果を採用する。
4. Skill が None、または既存 Skill の Critic が失敗なら、Generator → Worker.execute_candidate → Critic と進む。Candidate 成功後だけ新 UUID Skill を保存し、cache 生成・単一 Skill upsert へ進む。fallback は1回だけ。

`IntentExecution` は frozen dataclass で、次を保持します。

- observations: list[Observation]
- retrieved_skill_ids: tuple[UUID, ...]（検索順位の順）
- selected_skill_id: UUID | None（最初に選んだ既存 Skill。fallback 後も保持）
- learned_skill_id: UUID | None（Candidate の Critic 成功後だけ）
- selected_skill_critique: Critique | None（最初に選択した既存 Skill の判定。候補なしなら None）
- critique: Critique（採用または最終実行結果の成功・失敗理由）

正常再利用では両判定は同じです。fallback 時は selected_skill_critique に既存 Skill の失敗を保持し、critique に最終 Candidate の判定を保持します。

Worker と Executor は Dataset ID が1件だけの Intent を扱います。
Candidate の Critic 失敗なら Observation と失敗理由を返し、保存・UUID 生成は行いません。
実行・生成・判定・保存の例外は伝播し、例外時は fallback しません。retry、self-repair、
similarity threshold、複数 Dataset、Planner 接続は追加していません。

```python
from geo_voyager.critic import Critic
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from geo_voyager.worker import Worker

library = SkillLibrary()
executor = IntentExecutor(
    SkillRetriever(library, EmbeddingClient(embedding_base_url, embedding_model)),
    SkillSelector(), Worker(internal_network), SkillCandidateGenerator(), Critic(), library,
)
result = executor.execute(intent, k=4)
```

実 integration は初期6 Skill を一時 Library にコピーし、人口最大・最北端駅の再利用と
平均人口の新規学習を確認します。リポジトリの初期 Library は変更しません。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_intent_executor.py -q -s -W error
```

[3経路の実 retrieved / selected / learned、Observation・Critic・保存Skillの記録](docs/intent_execution.md)
を保存しています。平均人口は423185.9130434783で、Critic success後に一時 Library が6→7件になりました。
初期 Library は6件のままです。既存 Skill の通常実行では保存されません。

### 学習直後の同一 Intent・言い換え再利用

`integration/test_intent_executor.py` は同じ一時 Library を使い、平均人口を学習した後、
同じ Intent と「東京都23区について、1区あたりの平均人口を計算して」を連続実行します。
両方で学習 UUID の top-4 入り・Selector 選択、learned=None、生成・保存回数が増えないこと、
Observation の一致を確認します。Library は6→7→7→7でした。
[全 UUID と結果・専用一時ディレクトリでの再実行方法](docs/skill_growth.md)を記録しています。

現在の integration では再利用のたびに Critic を呼び、意図的な誤選択からの1回の fallback も確認します。過去の検証記録の critique=None は変更前の動作です。最新の結果は [Critic 検証と fallback](docs/critic_fallback.md) に記録します。

[派生 cache / HNSW index の実検証結果・6 Intent 評価・学習後の再利用](docs/vector_retrieval.md)を記録しています。

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

Each scenario uses its own empty temporary file-based Library. After Critic
success the UUID Skill is saved and indexed, then the same Intent is retrieved,
selected, executed and checked again without generation or another save.
The six initial repository Skills remain unchanged. Critic still checks only Intent
completion; its prompt explicitly forbids inventing missing answers from external
knowledge, and its control flow and success-only promotion remain unchanged. Generated requests use
registered services only; no tag answer or country object ID is supplied in the
prompt. Registry descriptions contain API/schema metadata and abstract protocol
syntax, rather than concrete geographic queries. Those queries remain model
output. Service-only generation explicitly sets `temperature=0.2` and
`chat_template_kwargs.enable_thinking=true`, `reasoning_budget_tokens=1024` and
`max_tokens=3072` per request. Dataset generation retains its existing defaults; Critic and Selector
use temperature zero. An explicit system message requests the strict description/code
layout and only the first description label is assistant-prefilled; malformed responses are rejected, not repaired. These settings do not
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
[llama.cpp request options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
[reasoning-budget request handling](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp).

[3本の実サービス学習・再利用結果、UUID、生成 Skill code / description](docs/service_learning.md) を記録しています。
