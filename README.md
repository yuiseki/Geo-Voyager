# Geo-Voyager v0.1.0

Python 3.12 以降を使用します。実行時の外部依存関係はありません。
テストには pytest が必要です（`python -m pip install pytest`）。

`Question(text)` と `Hypothesis(text)` は空文字列を拒否します。
`Planner().plan(question)` は、入力によらず
「コンビニ密度には区ごとの差がある」という仮説1件をリストで返します。
LLM、Graph、DB、Worker は実装していません。

```python
from geo_voyager.planner import Planner
from geo_voyager.question import Question

hypotheses = Planner().plan(Question("東京23区でコンビニの分布はどうなっている？"))
print(hypotheses[0].text)
```

テスト実行（環境にインストール済みの外部 pytest プラグインを読み込みません）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -W error
```
