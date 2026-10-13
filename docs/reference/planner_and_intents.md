# Planner と Intent（一括計画の経路と基本の型）

現在の主経路は 1 step ずつ決める適応ループで、[pipeline.md](pipeline.md) にある。ここには、最初に作った型と、Goal 全体を最初に計画する古い経路を書く。

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
Docker sandbox で実行します。dataset_ids が1件のときは `dataset_id` としてコードに注入します（複数のときは Primitive が読む Dataset を知っている）。
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

## Goal 全体の計画（plan_goal）

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
