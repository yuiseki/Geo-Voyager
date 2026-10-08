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
`Worker().execute(intent)` は、DockerSandbox で固定コード
`print("hello from sandbox")` を実行し、stdout を `strip()` して Observation 1件を返します。
Intent からのコード生成や実データ取得は行いません。
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
memory 128 MiB、CPU 1、PID 32、network none です。
bind/volume mount と Docker socket の共有は行いません。コードは host 上では実行しません。
`--pull never` により実行時にはイメージを取得しません。

## Docker ネットワーク分離の検証

`integration/` にテスト専用の構成があります。実 Worker や DockerSandbox の
実行設定は変更していません。Fetch Gateway API、proxy、取得ポリシーは未実装です。

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
