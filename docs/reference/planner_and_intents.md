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

- `Planner.plan(goal: str)`（または `plan_goal`）は、登録した Dataset とサービスの説明を使って、Goal を順番つきの Intent に分ける。応答は厳密に読む。`plan(Question)` は、今も Hypothesis を返す。
- `GoalExecutor.execute` は計画を順に実行し、失敗した step で止まる。最後に、集めた測定と最後の答えのすべてに最終 Critic をかける。
- 後の Intent は、前の Observation を `previous_observations` として受け取る。Worker はその本文を `list[str]` として、今の `intent_text` と一緒にコンテナに渡す。生成したコードや再利用するコードは、前の答えをソースに書き込まず、この実行時の値を読む。地理的な分け方はコードに書き込んでいない。
- 計画に書けるのは `調査項目`、`利用データセット`、`利用サービス` だけ。
  - 一覧には登録した ID か `[]` を書く。未知の ID と余分な欄は、明示的に失敗にする。
  - ブロックは `---` か、次の `調査項目:` で区切る。
- ローカル集計（外部を読まず、前の結果だけを使う Intent）は、両方の一覧を空にできる。ただし、外部を読む step の後でなければならない。
  - この Intent は `requires_context=True` を持ち、Worker と Executor は実行の前に、実際の前の Observation があることを求める。
  - 外部を読む Intent には、今までどおり登録したリソースが要る。
- Generator と repair が見るのは、前の JSON 出力の形で、答えの値は見せない。
- 前の結果の中の対象は、一覧の位置ではなく、名前と安定 ID で選ぶ（[pipeline.md](pipeline.md) の「対象の識別」）。必須の ID や一覧の件数は確かめ、仮の値で埋めない。
- プロトコルとスキーマの契約はサービスの説明に置き、`call_service` は汎用の Gateway クライアントのままにする。
