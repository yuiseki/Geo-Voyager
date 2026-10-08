# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。実行時の外部依存関係はありません。
テストには pytest が必要です（`python -m pip install pytest`）。

`Question(text)`、`Hypothesis(text)`、`Intent(text)`、`Observation(text)`、`Verdict(text)` は空文字列を拒否します。
`Planner().plan(question)` は、入力によらず
「コンビニ密度には区ごとの差がある」という仮説1件をリストで返します。
`Planner().plan_intents(hypothesis)` は、入力によらず
「東京23区ごとのコンビニ件数を調べる」という Intent 1件をリストで返します。
`Worker().execute(intent)` は、入力によらず
「調査対象は東京23区である」という Observation 1件をリストで返します。
Worker は固定実装で、実際のデータ取得は行いません。
`Planner().judge(hypothesis, observations)` は、入力によらず
「仮説はまだ十分に検証されていない」という Verdict 1件を返します。

```python
from geo_voyager.planner import Planner
from geo_voyager.question import Question
from geo_voyager.worker import Worker

planner = Planner()
hypotheses = planner.plan(Question("東京23区でコンビニの分布はどうなっている？"))
intents = planner.plan_intents(hypotheses[0])
observations = Worker().execute(intents[0])
verdict = planner.judge(hypotheses[0], observations)
print(verdict.text)
```

テスト実行（環境にインストール済みの外部 pytest プラグインを読み込みません）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -W error
```
