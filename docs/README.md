# 文書の一覧

- [reference/](#reference仕様): 今のコードがどう動くか。コードを変えたら、ここを合わせる。
- [ADR/](ADR/README.md): 決めたことと、その理由。
- [reports/](#reports測定の記録): 日付ごとの測定の記録。書いた時点のコードについての記録で、後から書き換えない。
- [evidence/](evidence/): reports が引く生の記録（trace、プロンプトと応答、`exploration.jsonl` など）。

## reference（仕様）

| 文書 | 内容 |
|---|---|
| [pipeline.md](reference/pipeline.md) | 主経路。自由な探索、適応ループ、名前付きの結果、対象の識別、決定的な検査の一覧 |
| [skills_and_generation.md](reference/skills_and_generation.md) | Control Primitives、Skill library、Generator、Critic、EmbeddingClient |
| [services.md](reference/services.md) | 登録した地理サービス、Service Gateway、`call_service`、repair |
| [datasets.md](reference/datasets.md) | Dataset Graph と登録した 5 件 |
| [sandbox_and_gateway.md](reference/sandbox_and_gateway.md) | Docker sandbox の制約、ネットワーク分離、Dataset Fetch Gateway、Worker image |
| [planner_and_intents.md](reference/planner_and_intents.md) | 最初の型（Question、Hypothesis、Intent）と、Goal 全体を最初に計画する古い経路 |

## reports（測定の記録）

最新は [2026-10-11_exploration.md](reports/2026-10-11_exploration.md)（自由な探索。1 回目から順に追記している）。

| 日付 | 文書 |
|---|---|
| 10-08 | [Skill の検索と選択](reports/2026-10-08_skill_evaluation.md)、[学習した Skill の連続再利用](reports/2026-10-08_skill_growth.md)、[Critic と 1 回の fallback](reports/2026-10-08_critic_fallback.md)、[DuckDB vss の検索](reports/2026-10-08_vector_retrieval.md)、[IntentExecutor の integration](reports/2026-10-08_intent_execution.md)、[登録サービスの学習と再利用](reports/2026-10-08_service_learning.md) |
| 10-09 | [複合 Goal（ハンバーガー）](reports/2026-10-09_burger_goal_learning.md)、[件数差と自然発生の repair](reports/2026-10-09_burger_count_and_natural_repair.md)、[repair の自然失敗ベンチマーク](reports/2026-10-09_repair_benchmark.md)、[失敗の種類](reports/2026-10-09_failure_categories.md)、[番号から identity へ](reports/2026-10-09_identity_references.md)、[semantic repair](reports/2026-10-09_semantic_repair.md)、[1 step ずつ決める Planner](reports/2026-10-09_observation_driven_planning.md)、[再計画への回復](reports/2026-10-09_observation_driven_recovery.md)、[Planner とサービスの契約](reports/2026-10-09_planner_service_contract.md)、[repair の既定値隠し](reports/2026-10-09_runtime_repair_defaults.md)、[Critic が誤答を通した 11 件](reports/2026-10-09_critic_accepted_wrong.md)、[`対象:` の制限の E2E](reports/2026-10-09_entity_target_e2e.md) |
| 10-10 | [適応ループ 1 周目](reports/2026-10-10_adaptive_round_1.md)、[2 周目](reports/2026-10-10_adaptive_round_2.md)、[Library の持ち越し](reports/2026-10-10_adaptive_shared_library.md)、[ハーネスの理解の確かめ](reports/2026-10-10_harness_understanding.md)、[分析用 sandbox と G1 の再現](reports/2026-10-10_analysis_sandbox.md)、[10-08〜10-10 のまとめ](reports/2026-10-10_research_summary.md) |
| 10-11〜 | [自由な探索](reports/2026-10-11_exploration.md) |
