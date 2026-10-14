# Control Primitives、Skill、生成、Critic

## Control Primitives と Skill Library

`geo_voyager/control_primitives/` は sandbox の中で使う基礎操作を提供します。各機能を 1 ファイルずつに分け、`__init__.py` から再公開しています。

- `connect_duckdb()`: sandbox 用の DuckDB 接続。既存の extension 設定・LOAD を維持します。
- `dataset_url(dataset_id, table=None)`: 登録済み Dataset（とその表）を Gateway の URL に変換します。
- `read_table(connection, dataset_id, table)`: Dataset の reference が挙げる表の全列を、reference の列名のまま relation で返します。経度緯度の geometry は OGC:CRS84 にそろえます（[ADR 0010](../ADR/0010-generic-table-primitives.md)）。
- `sum_population_grid(connection, zones)`: geometry 列を持つ区域ごとに WorldPop 100m の画素を足し、`estimated_population` を返します（一度に 100 区域まで）。
- `call_service(service_id, *, path="", params=None, body=None, content_type=None)`: 登録サービスに Gateway 経由で問い合わせます（[services.md](services.md)）。

`sum_population_grid` は、先頭に dataset_id を渡す古い呼び方も受け付けます（`dataset_arguments.py`）。
地域は Primitive ではなく列の条件で絞ります。名前のついた地域とその条件（東京23区は `pref_code = '13' AND name LIKE '%区'`）は `table_contracts.py` の `NAMED_AREAS` だけに置き、表の契約としてプロンプトに出します。
DuckDB 接続を引数で渡すことで、Skill が接続の終了まで管理します。

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

`SkillCandidateGenerator.generate(intent, skills) -> SkillCandidate` は既存のローカル
`LlamaClient` を使い、Intent.text、dataset_ids と service_ids の説明、Control Primitives の
名前・シグネチャ・説明、検索した Skill（呼んでよい関数）を渡します。
地域は、表の契約に出る名前のついた地域の条件（`NAMED_AREAS`）で絞るよう示し、行政コードを推測・生成させません。
Dataset の読み込みは Primitive のみに限定するよう指示し、外部 URL の直接利用を禁止します。
実行環境が定義する変数（`dataset_id`、`intent_target`、`previous_observations`、`results`。[pipeline.md](pipeline.md)）を参照し、最終結果を stdout に出すコードを生成します。

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
    base_url="http://localhost:30194",
    model="embeddinggemma",
)
vectors = client.embed(["人口が最も多い区を調べる。", "人口が最も少ない区を調べる。"])
```

検索に使うのは、2026-10-10 から常駐の EmbeddingGemma 2（`default/embeddinggemma`、NodePort 30194、model `embeddinggemma`、768 次元）です。granite-embedding より、地物を数える Skill を上位 4 件に入れる率が高かった（3 周目の記録で 9 / 10 と 4 / 10。[2026-10-10_adaptive_shared_library.md](../reports/2026-10-10_adaptive_shared_library.md)）。Skill の embedding はモデル名と一緒に保存し、モデルが違えば作り直します（`skill_retriever.py`）。

以下は、それ以前に使っていた granite-embedding の確認の記録です。2026-10-08に既存 `default/embedding-server` を読み取り専用で確認しました。
model alias は `granite-embedding`、モデル実体は
`granite-embedding-97m-multilingual-r2.f16.gguf`（pooling cls）です。
実 endpoint は `http://10.105.167.163:8080/v1/embeddings` でした。
日本語2文の1回のbatchリクエストで384次元のベクトルが2件返り、すべて有限値でした。

unit test は HTTP を mock にします。integration は明示実行し、
次の環境変数がない場合は skip します。環境変数はテストが constructor に渡すためのものです。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://localhost:30194 \
GEO_VOYAGER_EMBEDDING_MODEL=embeddinggemma \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest integration/test_embedding_llama.py -q -s -W error
```

## Skill Library（名前付き関数、Voyager 型）

2026-10-10 に、MineDojo/Voyager の Skill library に合わせて作り直した。それまでの UUID ごとのトップレベルのスクリプト、DuckDB vss の index、Skill を 1 件選んで丸ごと再実行する Selector は廃止した。設計と経緯は [0006-named-function-skill-library.md](../ADR/0006-named-function-skill-library.md)。

- Skill は、import とトップレベルの関数 1 つ（docstring つき）だけのコード（`geo_voyager/skill_function.py` の `parse_skill`）。関数名で呼ばれ、docstring が説明になる。
- `SkillLibrary(root)`（`geo_voyager/skill_library.py`）は Skill を名前で保存し、同じ名前を保存し直すと前の版を残す（`<名前>/v1/code.py`、`v2/` ...）。保存されていない Skill を呼ぶ Skill は拒否する。
- `link(program, library)` は、プログラムが呼ぶ Skill を呼び先までたどり、呼ばれる側を先にプログラムの前に並べる。Worker は実行の前にこれを行い、失敗の行番号はプログラムの行で返す。
- `SkillRetriever(library, embedding_client)` は、Skill の説明の embedding（版ごとに保存）と Intent の文の cosine で上位 k 件を返す。
- `IntentExecutor(retriever, worker, generator, critic, skill_library, repairer=None, semantic_repairer=None)` は、上位の Skill を Generator に見せ、生成コード（Skill を呼んでよい。新しい関数は 1 つまで）を Skill をリンクして実行し、失敗なら最大 2 回 repair し、Critic が成功としたら新しい関数を Skill として保存する。結果の `IntentExecution` は、見せた Skill（`retrieved_skills`）、呼んだ Skill（`called_skills`）、保存した Skill（`learned_skill`、`名前@v版`）を持つ。
- リポジトリの `skill_library/` は、探索を始めるときに Library へ写す seed の 11 Skill（`most_populous_area`、`least_populous_area`、`top_areas_by_population`、`total_population`、`count_station_records`、`northernmost_station`、`get_relation_id`、`count_tag_in_area`、`count_tag_in_areas`、`tag_usage_count`、`route_summary`）。`tests/test_seed_skills.py` が数と中身を確かめる。
