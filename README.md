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

unit test は LLM client または HTTP を mock にしており、実モデルを呼びません。
上の使用例は手動確認用で、`plan()` で実モデルへのリクエストが1回発生します。

テスト実行（環境にインストール済みの外部 pytest プラグインを読み込みません）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -W error
```
