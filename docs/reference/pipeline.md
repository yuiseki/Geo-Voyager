# 主経路: 適応ループと自由な探索

地理の質問（Goal）を、ローカル LLM（自前の llama.cpp、`gvt-llm`、文脈 8192 トークン）が小さな調査（Intent）に 1 つずつ分け、Intent ごとに Python のコードを生成して Docker sandbox で実行し、自前の地理サービスと Dataset から答えを得る。うまくいった関数は Skill として保存し、似た Intent で再利用する（Voyager 型の Skill library。[0006](../ADR/0006-named-function-skill-library.md)）。

## 自由な探索（bench/run_explore.py）

決まった Goal を解く代わりに、モデルが自分で次の Goal を立てる（[0003](../ADR/0003-three-graphs-and-skill-library.md)、記録は [2026-10-11_exploration.md](../reports/2026-10-11_exploration.md)）。

- `geo_voyager/curriculum.py`: 次の Goal を 1 件だけ決める。読むのは、利用できるリソース、これまでの発見（新しいものから 20 件）、試した Goal とその結果（新しいものから 15 件）。
- `geo_voyager/world_graph.py`: 答えが出た Goal（DONE で終わり、最終 Critic も成功）を、答え、成功した step、使ったリソース、判明した対象（名前と安定 ID）とともに記録する。
- Skill library、World Graph、試した Goal の記録は Goal をまたいで引き継ぐ。`--replay FILE` で、curriculum の代わりに決まった Goal の一覧を流せる（評価用の Goal はこれで流す。[0009](../ADR/0009-held-out-evaluation-goals.md)）。

## 1 Goal の流れ

```
Goal
 └ GoalExecutor.execute_adaptive                         geo_voyager/goal_executor.py
    ├ Planner.next(goal, history) -> Intent | DONE       geo_voyager/planner.py
    │    履歴（GoalHistory）を読んで次の Intent を 1 件決める。対象は「対象:」、出力の名前は「結果名:」、使う前の結果は「入力:」
    ├ IntentExecutor.execute(intent)                     geo_voyager/intent_executor.py
    │    ├ SkillRetriever                 近い Skill（名前付き関数）を検索（embedding: granite-embedding）
    │    ├ SkillCandidateGenerator        Skill を呼んでよいコードを生成（新しい関数は 1 つまで）
    │    ├ Worker -> DockerSandbox        呼ぶ Skill をリンクして sandbox で実行（Gateway 経由でのみ外部へ、既定 30 秒）
    │    ├ SkillCandidateRepairer         実行が失敗したら traceback を見て直す（最大 2 回）
    │    ├ Critic.check                   Observation が Intent に答えたか判定
    │    ├ （Critic が成功なら）新しい関数を Skill として名前と版で保存
    │    └ SemanticRepairer（既定は無効） 実行は通ったが Critic が棄却したときに 1 回直す
    ├ GoalHistory に step、計画の失敗（PlannerFailure）、最終判定の失敗（FinalCriticFailure）を追記
    └ DONE のとき Critic.check(goal, 全 Observation, final=True)。失敗なら履歴に入れて Planner に戻る
```

- 停止の理由（`AdaptiveGoalExecution.stop_reason`）: `done`、`max_steps`（既定 8）、`repeated_intent`（成功した Intent か、2 回失敗した Intent をもう一度出した）、`planner_failure`（計画の失敗が 3 回）、`final_critic_failed`（最終判定の失敗が 3 回）、`planner_error`。
- 外部は自前のサービスだけを使う（[services.md](services.md)、[0002](../ADR/0002-self-hosted-services-only.md)）。
- 古い経路（`Planner.plan_goal` で Goal 全体を最初に計画する `GoalExecutor.execute`）も残っている（[planner_and_intents.md](planner_and_intents.md)）。

## 名前付きの結果

- Planner は各 Intent に `結果名:`（英小文字で始まり、英小文字・数字・`_`）を付け、前の結果を使う Intent は `入力:` に結果名を書く。使わないなら `入力: []`。
- 同じ結果名を付け直すと、新しいほうに置き換わる。
- 最初の手に `入力:` の結果名があれば、実行の前に拒否する（`planner._require_known_inputs`）。
- Worker は、コードの前に次の変数を定義する（`worker.injected_lines`）。
  - `dataset_id`: Dataset が 1 件のとき。
  - `intent_target`: 対象があるとき（`{"name", "id_type", "id_value"}`）。
  - `previous_observations`、`intent_text`: 前の Observation があるとき。
  - `results`: `入力:` があるとき。結果名から、JSON として読んだ値への dict。
- 文脈に収めるため、Critic に見せる前段の Observation は合わせて 4096 バイトまでに切り詰める（`critic.REFERENCE_BUDGET`。小さいものから順に配分）。

## 対象の識別（TargetRef）

- 対象は `TargetRef(name, id_type, id_value)`。同じ対象かどうかは ID で決め、名前は表示に使う。ID の無い TargetRef は「これから調べる対象」（[0004-targets-by-stable-id.md](../ADR/0004-targets-by-stable-id.md)）。
- 「一覧の N 番目」で対象を指す方式は撤去した（[2026-10-09_identity_references.md](../reports/2026-10-09_identity_references.md)）。
- Planner は `対象:` に名前か ID（`relation_id=1761717`）を書く。履歴の既知の対象に、ID、名前の完全一致、カンマの前の名前の順で解決する。同名で ID が違えば拒否する。
- Worker は `intent_target`（`{"name", "id_type", "id_value"}`）をコードに渡す。Critic は、同じ種類の ID が Observation にあって対象の ID と違えば、モデルを呼ばずに失敗にする。

## 契約と、決定的な検査

LLM の出力に対する決定的な検査（モデルを使わない。単体テストで固定）。拒否したら理由を添えて作り直させ、回数が尽きたら失敗を見える形で残す（既定値で成功を装わない）。

| 検査 | 実装 | どこで働くか | 詳細 |
|---|---|---|---|
| Intent に API のパスやパラメータ、Overpass QL、SPARQL を書かない | `intent_text.api_details_in` | Planner.next（拒否して履歴へ） | [2026-10-09_planner_service_contract.md](../reports/2026-10-09_planner_service_contract.md)、[2026-10-09_entity_target_e2e.md](../reports/2026-10-09_entity_target_e2e.md) |
| `対象:` は 1 つの実体だけ（履歴で ID が判明した対象か、Goal が名指しした名前。タグ、タグのキーや値、複数の対象、集合は不可） | `planner._require_an_entity`、`_not_an_entity` | Planner.next | [0004-targets-by-stable-id.md](../ADR/0004-targets-by-stable-id.md)、[2026-10-10_adaptive_round_1.md](../reports/2026-10-10_adaptive_round_1.md) |
| `対象:` は 1 Intent に 1 行 | `planner._extract_target` | Planner | [2026-10-09_identity_references.md](../reports/2026-10-09_identity_references.md) |
| `id_type` を固定の文字列と比べない（`id_type == "relation"`） | `id_type_literals.id_type_comparisons` | Generator と runtime repair（対象に ID があるとき） | [2026-10-09_entity_target_e2e.md](../reports/2026-10-09_entity_target_e2e.md) |
| ローカル集計は、測定値の欠落を数値や None の既定値で代用しない、Observation を位置で選ばない | `local_aggregation_contract.local_aggregation_violations` | Generator と runtime repair（`requires_context` の Intent） | [0005-local-aggregation-contract.md](../ADR/0005-local-aggregation-contract.md) |
| repair が、失敗に出た必須キーを `.get(k, 既定値)` や握りつぶす except で隠さない | `default_fallback.introduced_fallbacks` | runtime repair | [2026-10-09_runtime_repair_defaults.md](../reports/2026-10-09_runtime_repair_defaults.md) |
| repair が Observation の値をコードに貼り込まない | `hardcoding.py` | semantic repair | [2026-10-09_semantic_repair.md](../reports/2026-10-09_semantic_repair.md) |
| Observation が空、または対象の ID と違う ID | `critic.py`、`target_identity.identity_conflict` | Critic | [0004-targets-by-stable-id.md](../ADR/0004-targets-by-stable-id.md) |

LLM のプロンプトだけで課している契約（決定的な検査は無い）:

- Critic: 値が 0 や空、矛盾する値は、根拠が Observation にあるときだけ成功（[2026-10-09_critic_accepted_wrong.md](../reports/2026-10-09_critic_accepted_wrong.md)）。比較・選択・集計を求める step では、答えそのもの（勝者など）が Observation に出ていること（[2026-10-10_adaptive_round_1.md](../reports/2026-10-10_adaptive_round_1.md)）。
- 最終 Critic（`final=True`）: Goal の答えそのものが Observation に出ていること。複数の数値から自分で比べて答えを作らない（[2026-10-09_entity_target_e2e.md](../reports/2026-10-09_entity_target_e2e.md)）。
- Generator: 出力の JSON のキーは値の意味を表す（固定のスキーマは無い）。`name` と `relation_id` は対象の出力にだけ使う。対象についての測定は、何を測ったか（`"tag": "amenity=cafe"`）を含める（[2026-10-09_planner_service_contract.md](../reports/2026-10-09_planner_service_contract.md)、[2026-10-10_adaptive_round_1.md](../reports/2026-10-10_adaptive_round_1.md)）。
- サービスの説明（`services.py`）は、自前のサービスに実際に問い合わせて確かめた内容だけを書き、integration の契約テストで保つ。Taginfo（`key/values` の page と rp、`tag/stats`、`search/by_value` は部分一致）は `integration/test_taginfo_contract.py`、Valhalla（POST、`costing` 必須、`trip.summary.length` と `time`）は `integration/test_valhalla_contract.py`。
- `call_service` は GET のパラメータの空白を `%20` で送る（`+` だと Valhalla が JSON を読めない）。

その他の実行時の扱い:

- sandbox の 30 秒の timeout は、その Candidate の失敗（`TimeoutError`）として返す。以前は例外が外へ出て実行全体が止まった。
- runtime repair の拒否は `SkillCandidateRepairer.rejected_fallbacks` に記録し、`bench/run_adaptive.py` の行にも出る。
