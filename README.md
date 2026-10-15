# Geo-Voyager v0.1.0

ローカル LLM が、地理の問いを自分で立て、自前の地理サービスと Hugging Face の Dataset を使って答えていく探索エージェント。
MineDojo/Voyager の automatic curriculum と Skill library を、地理空間の分析に移したもの。
目標は、[study-geoai-algo-py](https://github.com/yuiseki/study-geoai-algo-py) の水準の分析を、ローカル LLM だけで行えるようにすること。

- LLM: 自前の llama.cpp（`gvt-llm`、`http://10.108.45.102:8080/v1/chat/completions`）。structured output は使わない。
- embedding: 常駐の EmbeddingGemma 2（`embeddinggemma`、`http://localhost:30194`、768 次元）。Skill の検索に使う。
- 生成コードは Docker sandbox で実行し、外へは Gateway だけを通す（[ADR 0001](docs/ADR/0001-sandbox-and-gateway.md)）。地理サービスは自前のものだけを使う（[ADR 0002](docs/ADR/0002-self-hosted-services-only.md)）。

## 仕組み

```
curriculum（次の Goal を 1 件立てる）
 └ 適応ループ（Planner が Intent を 1 つずつ決める）
    └ Intent ごとに Skill を検索 → コードを生成 → sandbox で実行 → 失敗なら repair → Critic が判定 → 新しい関数を Skill として保存
 └ 最終 Critic が答えを認めたら World Graph に記録
```

詳しくは [docs/reference/pipeline.md](docs/reference/pipeline.md)。

## 現状

最新の測定は、評価用の 30 Goal（[ADR 0009](docs/ADR/0009-held-out-evaluation-goals.md)）を流した探索の 10 回目（2026-10-13、コード `fe42e0b`）で、答えが出たのは 18 / 30 件。答えが出たものから一様ランダムに選んだ 6 件のうち、5 件が正しかった。
1 回ごとの揺れが大きく、1 回の件数の差では修正の効果を判断できない。経過は [docs/reports/2026-10-11_exploration.md](docs/reports/2026-10-11_exploration.md)。

## 必要なもの

- Python 3.12 以降。リポジトリの `.venv/bin/python` を使う（DuckDB 1.5.6、rasterio 1.5.1）。
- Docker と、事前に用意したイメージ（実行時には取得しない）。
  - `python:3.12-slim`
  - `geo-voyager-worker:duckdb-1.5.6-rasterio-1.5.1`（`docker/worker/Dockerfile`）
  - 分析用の `docker/analysis/Dockerfile`（[ADR 0007](docs/ADR/0007-analysis-sandbox.md)）
- 上の LLM と embedding、自前の地理サービス（overpass、nominatim、valhalla、taginfo の各 `*.yuiseki.net`）に届くこと。

## テスト

単体テストは LLM、HTTP、Docker を mock にしていて、何も起動しない。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests -q -W error
```

実モデル、実 Docker、実サービスを使う確かめは `integration/` にあり、明示的に実行する（実行方法は [docs/reference/](docs/README.md#reference仕様) の各文書にある）。

## 探索を流す

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://localhost:30194 GEO_VOYAGER_EMBEDDING_MODEL=embeddinggemma \
  PYTHONPATH=. .venv/bin/python -u -m bench.run_explore \
  --out ~/tmp/geo-voyager-bench/NAME --library ~/tmp/geo-voyager-bench/NAME_library --goals 30
```

- `--goals N` は curriculum に N 件の Goal を立てさせる。`--replay FILE` は、ファイルの Goal（1 行 1 件）を順に流す。
- 評価用の Goal は `--replay docs/evidence/explore_9/goals.txt` で流す。
- 同じ `--out` と `--library` を指定すれば、前回の続きから再開する。`--library` が無ければ、`skill_library/` の seed から作る。
- `--out` に `STOP` という名前のファイルを置くと、流している Goal が終わったところで止まる。
- 終わりを待つときは、本体の PID を `tail --pid=PID -f /dev/null` で待つ。`pgrep -f` でコマンド行の文字列を探すと、待機自身のコマンド行にもその文字列があるため、いつまでも終わらない（2026-10-15、これで GPU が一晩遊んだ）。

## 構成

| 場所 | 中身 |
|---|---|
| `geo_voyager/` | 本体（Planner、Generator、Worker、Critic、curriculum、World Graph など） |
| `geo_voyager/control_primitives/` | sandbox の中で使う基礎操作（DuckDB、Dataset の読み込み、`call_service`、人口グリッド） |
| `skill_library/` | 探索の最初に写す seed の Skill（名前付き関数） |
| `bench/` | 探索、ベンチマーク、再生、集計の道具 |
| `docker/` | Worker と分析用のイメージ |
| `tests/`、`integration/` | 単体テストと、実物を使う確かめ |
| `docs/` | 文書（[一覧](docs/README.md)） |

## 文書

- [docs/reference/](docs/README.md#reference仕様): 今のコードの仕様
- [docs/ADR/](docs/ADR/README.md): 設計の決定
- [docs/reports/](docs/README.md#reports測定の記録): 日付ごとの測定の記録
