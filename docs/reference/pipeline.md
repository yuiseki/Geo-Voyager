# 主経路: 適応ループと自由な探索

地理の質問（Goal）を、ローカル LLM（自前の llama.cpp、`gvt-llm`、文脈 8192 トークン）が小さな調査（Intent）に 1 つずつ分け、Intent ごとに Python のコードを生成して Docker sandbox で実行し、自前の地理サービスと Dataset から答えを得る。うまくいった関数は Skill として保存し、似た Intent で再利用する（Voyager 型の Skill library。[0006](../ADR/0006-named-function-skill-library.md)）。

## 自由な探索（bench/run_explore.py）

決まった Goal を解く代わりに、モデルが自分で次の Goal を立てる（[0003](../ADR/0003-three-graphs-and-skill-library.md)、記録は [2026-10-11_exploration.md](../reports/2026-10-11_exploration.md)）。

- `geo_voyager/curriculum.py`: 次の Goal を 1 件だけ決める。読むのは、利用できるリソース、これまでの発見（新しいものから 20 件）、試した Goal とその結果（新しいものから 15 件）。結果は「答えが出た」か「未達」で、未達ならモデルを使わずに確かめた失敗の種類と資源だけを添える。Critic の理由と止まり方は読まない（[0011](../ADR/0011-exploration-graph-checked-failures.md)）。
- `geo_voyager/event_log.py`: Goal ごとに、始まり（Goal と渡した記憶）、出来事（手、計画の失敗、最終判定の失敗）、終わり（止まり方と答えが出たか）を、起きるたびに `NNN/events.jsonl` へ 1 行ずつ書く。終わりに Critic の文は書かない。途中で壊れた Goal には終わりの行が無く、`bench/run_explore.py --resume` がその次の手から再開する。trace.json、exploration.jsonl の行、world.jsonl の発見は、このログから作る（[0012](../ADR/0012-goal-event-log-and-resume.md)）。
- `geo_voyager/world_graph.py`: 答えが出た Goal（DONE で終わり、最終 Critic も成功）を、答え、成功した step、使ったリソース、判明した対象（名前と安定 ID）とともに記録する。
- `geo_voyager/exploration_graph.py`: 試した Goal を 1 件 1 行で記録する。次に同じ Goal を試す Planner には、前の試行のうちモデルを使わずに確かめた失敗（実行のエラー、時間切れ、コードや Planner の契約違反、出力の上限超え、同じ行の重複）だけを渡す。Critic の判定と理由、Observation、stdout、Planner の応答は渡さない（[0011](../ADR/0011-exploration-graph-checked-failures.md)）。
- Skill library、World Graph、試した Goal の記録は Goal をまたいで引き継ぐ。`--replay FILE` で、curriculum の代わりに決まった Goal の一覧を流せる（評価用の Goal はこれで流す。[0009](../ADR/0009-held-out-evaluation-goals.md)）。

## 1 Goal の流れ

```
Goal
 └ GoalExecutor.execute_adaptive                         geo_voyager/goal_executor.py
    ├ Planner.next(goal, history) -> Intent | DONE       geo_voyager/planner.py
    │    履歴（GoalHistory）を読んで次の Intent を 1 件決める。対象は「対象:」、出力の名前は「結果名:」、使う前の結果は「入力:」
    │    履歴の各手は、結果（成功、実行失敗、Critic が不十分と判定）と Observation。Critic の理由は、棄却された手だけに添える
    ├ IntentExecutor.execute(intent)                     geo_voyager/intent_executor.py
    │    ├ SkillRetriever                 近い Skill（名前付き関数）を検索（embedding: embeddinggemma）
    │    ├ SkillCandidateGenerator        Skill を呼んでよいコードを生成（新しい関数は 1 つまで）
    │    ├ Worker -> DockerSandbox        呼ぶ Skill をリンクして sandbox で実行（Gateway 経由でのみ外部へ、既定 180 秒、1 GB、2 CPU。DuckDB は 512 MB と 2 スレッドで、超えた分は /tmp（256 MB）へ書き出す）
    │    ├ SkillCandidateRepairer         実行が失敗したら traceback を見て直す（最大 2 回）
    │    ├ Critic.check                   Observation が Intent に答えたか判定
    │    └ （Critic が成功なら）新しい関数を Skill として名前と版で保存
    ├ GoalHistory に step、計画の失敗（PlannerFailure）、最終判定の失敗（FinalCriticFailure）を追記
    └ DONE のとき Critic.check(goal, 全 Observation, final=True)。失敗なら履歴に入れて Planner に戻る
```

- 停止の理由（`AdaptiveGoalExecution.stop_reason`）: `done`、`max_steps`（既定 12）、`repeated_intent`（成功した Intent か、2 回失敗した Intent をもう一度出した）、`planner_failure`（計画の失敗が 6 回）、`final_critic_failed`（最終判定の失敗が 3 回）、`planner_error`。
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
| ローカル集計は、測定値の欠落を数値や None の既定値で代用しない、Observation を位置で選ばない | `contracts.code.local_aggregation_violations` | Generator と runtime repair（`requires_context` の Intent） | [0005-local-aggregation-contract.md](../ADR/0005-local-aggregation-contract.md) |
| 2 行以上ある入力（`results[...]`）の行を位置で選ばない（`area_ids[0]` など。ループや内包表記を通しても追う）。長さを k と確かめて 0 から k-1 をすべて位置で使う（経路の起点と終点）のは選択ではないので除く | `contracts.code.positional_input_picks` | Generator と runtime repair（入力のある Intent） | 2026-10-14。過去のコード 607 件で 12 か所を検出し、すべて 1 区だけを数えた誤り。除く条件を足したあと、647 件で同じ 12 か所を検出し、2 点の経路の 9 件は検出しない |
| WDI の指標のコードは、版を固定した series の表にあるものだけ（無ければ、近いコードを名前つきで添えて断る） | `indicator_codes.unknown_indicators`（一覧は `wdi_indicators.tsv`、`scripts/sync_wdi_indicators.py` で作る） | Planner.next、Generator と runtime repair（yuiseki/worldbank-wdi を読む Intent） | 2026-10-14。GeoAI-skills の小課題 14 で、陸地面積を EN.LND.TOTL.K2、密度を SP.POP.DNST と記憶で書き（正しくは AG.LND.TOTL.K2 と EN.POP.DNST）、絞り込みが 0 行になって「欠損」と答えた |
| DuckDB の球面・楕円体の関数（ST_Distance_Sphere、*_Spheroid）は、座標を ST_FlipCoordinates で入れ替えてから使う。コード生成には、面積（EPSG:6933）、距離、半径 r m の円（UTM）の測り方も渡す | `contracts.code.axis_order_problems`、`contracts.tables.MEASURING` | Generator と runtime repair | 2026-10-15。DuckDB 1.5.6 のこれらは緯度、経度の順を読み、東京と大阪の 396 km を 473 km、日本の面積を NaN にする。GeoAI-skills の小課題 17 で ST_Area_Spheroid を呼んだ |
| 出力が 256 KiB を超えない（超えたら切らずに失敗、`OutputTooLong`）。プロンプトには予算の中で見せる | `execution_failure.sandbox_program`、`critic.OBSERVED_BUDGET` | sandbox、Critic | [0013](../ADR/0013-results-passed-whole-shown-within-budgets.md) |
| 出力の JSON の一覧に、まったく同じ行が無い（`DuplicateRows`） | `contracts.output.output_problem` | Worker（Critic の前） | 2026-10-14。ekidata の 1 行は路線上の駅 |
| repair が、失敗に出た必須キーを `.get(k, 既定値)` や握りつぶす except で隠さない | `default_fallback.introduced_fallbacks` | runtime repair | [2026-10-09_runtime_repair_defaults.md](../reports/2026-10-09_runtime_repair_defaults.md) |
| Observation が空、または対象の ID と違う ID | `critic.py`、`target_identity.identity_conflict` | Critic | [0004-targets-by-stable-id.md](../ADR/0004-targets-by-stable-id.md) |

LLM のプロンプトだけで課している契約（決定的な検査は無い）:

- Critic: 手ごとの判定では、最後に実行したコードと、そのコードが読んだサービスとデータの説明を見せ、どう測ったかで判定させる。データの説明には、コードが名指しした表の 1 行が何かと、コードが使う列の意味と注意書きを含める（`dataset_references.critic_text`。説明だけでは、`ward IS NULL` で区を除いたコードを「区を除いていない」と退けた）。個々の地物の事実（どの区とどの区が接するか）を自分の知識で否定しない。0 や空、桁違いは疑ってよい（[2026-10-14_critic_stage4.md](../reports/2026-10-14_critic_stage4.md)）。Intent に出てくる読む元の列の名前（例: rep_lon）が出力のキーに無いこと、前段から引き継いだ名前や ID が今回読んだデータに無い種類であることは、失敗の理由にしない。判定は応答の最後の 2 行から読み、その前に書いた確かめの過程は許す（[2026-10-14_critic_stage5.md](../reports/2026-10-14_critic_stage5.md)）。値が 0 や空、矛盾する値は、根拠が Observation にあるときだけ成功（[2026-10-09_critic_accepted_wrong.md](../reports/2026-10-09_critic_accepted_wrong.md)）。比較・選択・集計を求める step では、答えそのもの（勝者など）が Observation に出ていること（[2026-10-10_adaptive_round_1.md](../reports/2026-10-10_adaptive_round_1.md)）。
- 最終 Critic（`final=True`）: Goal の答えそのものが Observation に出ていること。複数の数値から自分で比べて答えを作らない（[2026-10-09_entity_target_e2e.md](../reports/2026-10-09_entity_target_e2e.md)）。
- Generator: 出力の JSON のキーは値の意味を表す（固定のスキーマは無い）。`name` と `relation_id` は対象の出力にだけ使う。対象についての測定は、何を測ったか（`"tag": "amenity=cafe"`）を含める（[2026-10-09_planner_service_contract.md](../reports/2026-10-09_planner_service_contract.md)、[2026-10-10_adaptive_round_1.md](../reports/2026-10-10_adaptive_round_1.md)）。
- サービスの説明（`services.py`）は、自前のサービスに実際に問い合わせて確かめた内容だけを書き、integration の契約テストで保つ。Taginfo（`key/values` の page と rp、`tag/stats`、`search/by_value` は部分一致）は `integration/test_taginfo_contract.py`、Valhalla（POST、`costing` 必須、`trip.summary.length` と `time`）は `integration/test_valhalla_contract.py`。
- `call_service` は GET のパラメータの空白を `%20` で送る（`+` だと Valhalla が JSON を読めない）。

その他の実行時の扱い:

- sandbox の 30 秒の timeout は、その Candidate の失敗（`TimeoutError`）として返す。以前は例外が外へ出て実行全体が止まった。
- runtime repair の拒否は `SkillCandidateRepairer.rejected_fallbacks` に記録し、`bench/run_adaptive.py` の行にも出る。
