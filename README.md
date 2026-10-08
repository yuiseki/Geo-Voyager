# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。実行時の外部依存関係はありません。
テストには pytest が必要です（`python -m pip install pytest`）。

`Question(text)`、`Hypothesis(text)`、`Intent(text)`、`Observation(text)`、`Verdict(text)` は空文字列を拒否します。
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
1行につき1つ、3〜5件程度の調査内容を自由文で返すよう依頼します。
返答を改行で分割して `strip()` し、空行を除いた `list[Intent]` を返します。
全行が空なら拒否します。Intent の実行可能性は検証しません。
`Worker().execute(intent)` は、入力によらず
「調査対象は東京23区である」という Observation 1件をリストで返します。
Worker は固定実装で、実際のデータ取得は行いません。
`Planner().judge(hypothesis, observations)` は、入力によらず
「仮説はまだ十分に検証されていない」という Verdict 1件を返します。

```python
from geo_voyager.datasets import load_dataset_graph
from geo_voyager.planner import Planner
from geo_voyager.question import Question
from geo_voyager.worker import Worker

planner = Planner()
hypotheses = planner.plan(Question("東京23区でコンビニの分布はどうなっている？"))
intents = planner.plan_intents(hypotheses[0], load_dataset_graph())
observations = Worker().execute(intents[0])
verdict = planner.judge(hypotheses[0], observations)
print(verdict.text)
```

unit test は LLM client または HTTP を mock にしており、実モデルを呼びません。
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
