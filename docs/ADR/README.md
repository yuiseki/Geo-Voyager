# ADR（設計の決定）

決めたことと、その理由を残す。0003〜0008 は、決定の経緯を書いた設計メモをそのまま移したもので、形式がそろっていない。

| 番号 | 決定 | 日付 |
|---|---|---|
| [0001](0001-sandbox-and-gateway.md) | 生成コードは sandbox で動かし、外へは Gateway だけを通す | 2026-10-08 |
| [0002](0002-self-hosted-services-only.md) | 地理サービスは自前のものだけを使う | 2026-10-08 |
| [0003](0003-three-graphs-and-skill-library.md) | 構想: Dataset、World、Exploration の 3 つのグラフと Skill library | 2026-10-10 |
| [0004](0004-targets-by-stable-id.md) | 対象を stable ID で識別する（TargetRef） | 2026-10-09 |
| [0005](0005-local-aggregation-contract.md) | ローカル集計のコードの契約を決定的に検査する | 2026-10-10 |
| [0006](0006-named-function-skill-library.md) | Skill library を名前付き関数で作り直す（Voyager 型） | 2026-10-10 |
| [0007](0007-analysis-sandbox.md) | study-geoai の水準の分析を実行できる sandbox | 2026-10-10 |
| [0008](0008-study-geoai-experiments-as-goals.md) | study-geoai-algo-py の実験を Goal と oracle に変える（案） | 2026-10-10 |
| [0009](0009-held-out-evaluation-goals.md) | 評価用の Goal を取っておき、直すのに使わない | 2026-10-13 |
| [0010](0010-generic-table-primitives.md) | Dataset の読み込みを、データセットの reference から組み立てる汎用の Primitive にする | 2026-10-13 |
| [0011](0011-exploration-graph-checked-failures.md) | Exploration Graph: 次の試行に渡すのは、モデルを使わずに確かめた失敗だけ | 2026-10-14 |
| [0012](0012-goal-event-log-and-resume.md) | Goal の出来事の記録を正本にし、途中から再開する | 2026-10-14 |
| [0013](0013-results-passed-whole-shown-within-budgets.md) | 手の結果は次の手へ丸ごと渡し、プロンプトには予算の中で見せる | 2026-10-14 |
| [0014](0014-curiosity-from-prediction-error.md) | 予想の外れを curriculum のご褒美にして、好奇心を持たせる | 2026-10-17 |
