# Geo-Voyager の研究記録（2026-10-08〜10-10）

この文書は、`v0.1.0` ブランチで 2026-10-08 から 10-10 に行った作業の全体像と、そこから分かったこと、残っている課題をまとめる。個々の測定の詳細は、末尾の一覧の各文書にある。ここに書く数字は、各文書の数字を写したもので、出典の文書を併記する。

## 1. 何を作っているか

地理の質問（Goal）を、実 LLM（自前の llama.cpp、`gvt-llm`）が小さな調査（Intent）に分け、Intent ごとに Python のコード（Skill）を生成して Docker sandbox で実行し、自前の地理サービスと Dataset から答えを得る。うまくいったコードは Skill として保存し、似た Intent で再利用する（Voyager 型の Skill library）。

主な部品と流れ（現在の主経路は、1 step ずつ決める適応ループ）:

```
Goal
 └ GoalExecutor.execute_adaptive                         geo_voyager/goal_executor.py
    ├ Planner.next(goal, history) -> Intent | DONE       geo_voyager/planner.py
    │    履歴（GoalHistory）を読んで次の Intent を 1 件決める。対象は「対象:」の行で書く
    ├ IntentExecutor.execute(intent)                     geo_voyager/intent_executor.py
    │    ├ SkillRetriever / SkillSelector  既存 Skill の検索と選択（embedding: granite-embedding）
    │    ├ SkillCandidateGenerator        無ければコードを生成
    │    ├ Worker -> DockerSandbox        sandbox で実行（Service Gateway 経由でのみ外部へ）
    │    ├ Critic.check                   Observation が Intent に答えたか判定
    │    ├ SkillCandidateRepairer         実行が失敗したら traceback を見て直す（最大 2 回）
    │    └ SemanticRepairer（既定は無効） 実行は通ったが Critic が棄却したときに 1 回直す
    ├ GoalHistory に step、計画の失敗（PlannerFailure）、最終判定の失敗（FinalCriticFailure）を追記
    └ DONE のとき Critic.check(goal, 全 Observation, final=True)。失敗なら履歴に入れて Planner に戻る
```

- 停止の理由: `done`、`max_steps`（8）、`repeated_intent`（成功した Intent か、2 回失敗した Intent をもう一度出した）、`planner_failure`（計画の失敗が 3 回）、`final_critic_failed`（最終判定の失敗が 3 回）、`planner_error`。
- 古い経路（`Planner.plan_goal` で Goal 全体を最初に計画し、順に実行する `GoalExecutor.execute`）も残っている。`plan_goal` のプロンプトは golden test（`tests/plan_goal_prompt.golden.txt`）で固定している。
- 外部は自前のサービスだけを使う（Overpass、Nominatim、Taginfo、Valhalla、YuisekinGeoSPARQL。`geo_voyager/services.py`）。公開の OSM サーバーは呼ばない。

## 2. 対象の識別（TargetRef）

- 対象は `TargetRef(name, id_type, id_value)`。同じ対象かどうかは ID で決め、名前は表示に使う。ID の無い TargetRef は「これから調べる対象」（[target_ref.md](target_ref.md)）。
- 「一覧の N 番目」で対象を指す方式は撤去した（[identity_references.md](identity_references.md)）。
- Planner は `対象:` に名前か ID（`relation_id=1761717`）を書く。履歴の既知の対象に、ID、名前の完全一致、カンマの前の名前の順で解決する。同名で ID が違えば拒否する。
- Worker は `intent_target`（`{"name", "id_type", "id_value"}`）をコードに渡す。Critic は、同じ種類の ID が Observation にあって対象の ID と違えば、モデルを呼ばずに失敗にする。

## 3. 契約と、決定的な検査

LLM の出力に対する決定的な検査（モデルを使わない。単体テストで固定）。拒否したら理由を添えて作り直させ、回数が尽きたら失敗を見える形で残す（既定値で成功を装わない）。

| 検査 | 実装 | どこで働くか | 詳細 |
|---|---|---|---|
| Intent に API のパスやパラメータ、Overpass QL、SPARQL を書かない | `intent_text.api_details_in` | Planner.next（拒否して履歴へ） | [planner_service_contract.md](planner_service_contract.md)、[entity_target_e2e.md](entity_target_e2e.md) |
| `対象:` は 1 つの実体だけ（履歴で ID が判明した対象か、Goal が名指しした名前。タグ、タグのキーや値、複数の対象、集合は不可） | `planner._require_an_entity`、`_not_an_entity` | Planner.next | [target_ref.md](target_ref.md)、[adaptive_round_1.md](adaptive_round_1.md) |
| `対象:` は 1 Intent に 1 行 | `planner._extract_target` | Planner | [identity_references.md](identity_references.md) |
| `id_type` を固定の文字列と比べない（`id_type == "relation"`） | `id_type_literals.id_type_comparisons` | Generator と runtime repair（対象に ID があるとき） | [entity_target_e2e.md](entity_target_e2e.md) |
| ローカル集計は、測定値の欠落を数値や None の既定値で代用しない、Observation を位置で選ばない | `local_aggregation_contract.local_aggregation_violations` | Generator と runtime repair（`requires_context` の Intent） | [local_aggregation_contract.md](local_aggregation_contract.md) |
| repair が、失敗に出た必須キーを `.get(k, 既定値)` や握りつぶす except で隠さない | `default_fallback.introduced_fallbacks` | runtime repair | [runtime_repair_defaults.md](runtime_repair_defaults.md) |
| repair が Observation の値をコードに貼り込まない | `hardcoding.py` | semantic repair | [semantic_repair.md](semantic_repair.md) |
| Observation が空、または対象の ID と違う ID | `critic.py`、`target_identity.identity_conflict` | Critic | [target_ref.md](target_ref.md) |

LLM のプロンプトだけで課している契約（決定的な検査は無い）:

- Critic: 値が 0 や空、矛盾する値は、根拠が Observation にあるときだけ成功（[critic_accepted_wrong.md](critic_accepted_wrong.md)）。比較・選択・集計を求める step では、答えそのもの（勝者など）が Observation に出ていること（[adaptive_round_1.md](adaptive_round_1.md)）。
- 最終 Critic（`final=True`）: Goal の答えそのものが Observation に出ていること。複数の数値から自分で比べて答えを作らない（[entity_target_e2e.md](entity_target_e2e.md)）。
- Generator: 出力の JSON のキーは値の意味を表す（固定のスキーマは無い）。`name` と `relation_id` は対象の出力にだけ使う。対象についての測定は、何を測ったか（`"tag": "amenity=cafe"`）を含める（[planner_service_contract.md](planner_service_contract.md)、[adaptive_round_1.md](adaptive_round_1.md)）。
- サービスの説明（`services.py`）は、自前のサービスに実際に問い合わせて確かめた内容だけを書き、integration の契約テストで保つ。Taginfo（`key/values` の page と rp、`tag/stats`、`search/by_value` は部分一致）は `integration/test_taginfo_contract.py`、Valhalla（POST、`costing` 必須、`trip.summary.length` と `time`）は `integration/test_valhalla_contract.py`。
- `call_service` は GET のパラメータの空白を `%20` で送る（`+` だと Valhalla が JSON を読めない）。

その他の実行時の扱い:

- sandbox の 30 秒の timeout は、その Candidate の失敗（`TimeoutError`）として返す。以前は例外が外へ出て実行全体が止まった。
- runtime repair の拒否は `SkillCandidateRepairer.rejected_fallbacks` に記録し、`bench/run_adaptive.py` の行にも出る。

## 4. 測定の経過

| 日付 | 何を | 結果（要点） | 文書 |
|---|---|---|---|
| 10-08 | Skill の検索と選択、再利用、Critic と 1 回の fallback | 学習した Skill の連続再利用を確認 | [skill_evaluation.md](skill_evaluation.md)、[skill_growth.md](skill_growth.md)、[critic_fallback.md](critic_fallback.md)、[vector_retrieval.md](vector_retrieval.md)、[intent_execution.md](intent_execution.md) |
| 10-08〜09 | 登録サービスの学習と再利用、複合 Goal（ハンバーガー） | | [service_learning.md](service_learning.md)、[burger_goal_learning.md](burger_goal_learning.md)、[burger_count_and_natural_repair.md](burger_count_and_natural_repair.md) |
| 10-09 | repair の自然失敗ベンチマーク（6 Goal × 3 周） | Goal の正解 8/18。repair が尽きた 9 連鎖はすべて同じエラーの繰り返し。失敗行と試行履歴を渡す v1 を入れたが、全体の正解率を上げた証拠は無い | [repair_benchmark.md](repair_benchmark.md) |
| 10-09 | 21 Goal × 5 回、Critic の thinking あり・なしの 2 条件で失敗の種類を測る | 失敗の分類（codegen、semantic-completion、planning など）。「一覧の N 番目」を含む計画が大きく正解率を下げていた | [failure_categories.md](failure_categories.md) |
| 10-09 | 「一覧の N 番目」を identity 参照に変える | 1〜4 周で 47.0% → 50.6%（p = 0.76、有意でない）。retrieval-selection の失敗は 3 → 0 | [identity_references.md](identity_references.md) |
| 10-09 | semantic repair（Critic 棄却後に 1 回直す）を、保存済みの 22 件で再生 | Critic の基準で 4 件救えたが、oracle で確認できた救済は 0。3 件は出力のキーを変えて通っただけ。既定は無効のまま | [semantic_repair.md](semantic_repair.md) |
| 10-09 | 観察駆動の Planner（1 step ずつ）と、計画の失敗・最終判定の失敗からの再計画 | | [observation_driven_planning.md](observation_driven_planning.md)、[observation_driven_recovery.md](observation_driven_recovery.md) |
| 10-09 | TargetRef（stable ID を主キーに） | focused test のみ | [target_ref.md](target_ref.md) |
| 10-09 | Planner にサービス説明を全文見せ、API 詳細を Intent に書かせない。Taginfo の契約と出力キー | | [planner_service_contract.md](planner_service_contract.md) |
| 10-09 | runtime repair の既定値隠しの防止 | 保存済みの組で検査が拒否した 2 件のうち 1 件は明確な隠蔽、1 件は境界。実 LLM の再生では新旧プロンプトとも 0/6 で、差を示せない | [runtime_repair_defaults.md](runtime_repair_defaults.md) |
| 10-09 | Critic が誤答を通した 11 件の分類 | 退化した値 6、一覧を返した 4、Intent 不備 1。0・矛盾の指示で再生 0/9 → 2/9（件数 0 は防げない） | [critic_accepted_wrong.md](critic_accepted_wrong.md) |
| 10-09〜10 | `対象:` の制限、id_type、最終 Critic の答えの要求、ローカル集計の契約。`cafe_shibuya_vs_shinjuku` などの focused E2E | 最終 Critic の変更で、保存済み 21 実行の再生では誤答の通過 6 → 0、正解の通過 10 → 10 | [entity_target_e2e.md](entity_target_e2e.md)、[local_aggregation_contract.md](local_aggregation_contract.md) |
| 10-10 | 適応ループで 22 Goal を 1 周 | DONE で終わった正解 12/22、誤答の通過 0、停止 10 | [adaptive_round_1.md](adaptive_round_1.md) |
| 10-10 | 出力・サービス契約、`対象:` と step Critic の修正のあとの数本の E2E | Valhalla 2 本と `tag_ramen_vs_sushi` が正解に。`cafe_vs_restaurant_shibuya` は比較 step が勝者を出さず停止 | [adaptive_round_1.md](adaptive_round_1.md) |
| 10-10 | 適応ループで 22 Goal をもう 1 周 | DONE で終わった正解 15/22、誤答の通過 0、停止 7（うち計画の失敗 5） | [adaptive_round_2.md](adaptive_round_2.md) |

## 5. 現在の数字

最新の測定は、22 Goal を適応ループで 1 回ずつ流した 2 周目（コミット `004b33e`、[adaptive_round_2.md](adaptive_round_2.md)）。

| | 1 周目（`b8fa975`） | 2 周目（`004b33e`） |
|---|---|---|
| DONE で終わり、正解 | 12 / 22 | 15 / 22 |
| DONE で終わったが誤答 | 0 | 0 |
| 途中で停止 | 10 | 7 |

- 1 周ずつなので、12 と 15 の差は偶然と区別できない。以前の一括計画の方式（[identity_references.md](identity_references.md)、21 Goal × 4 周で 50.6%）とは方式も時期も違う。
- 2 周目で正解になったのは Valhalla の 2 本、`tag_ramen_vs_sushi`、`cafe_shibuya_vs_shinjuku`、`nom_setagaya_south`。落ちたのは `tag_sushi_count`（最終 Critic が正しい答えを 3 回拒否）と `stations_northmost`（2 段に分けた計画のローカル集計の失敗）。
- 2 周目の停止 7 件のうち 5 件は計画の失敗。拒否された `対象: 東京23区` の繰り返しと、`利用データセット` の 1 行書きの形式エラーが主。
- 誤答を正解として返した実行は、2 周とも 0 件。失敗は止まる形で見えている。

正解した Goal（2 周目）: `cafe_shibuya`、`ramen_shinjuku`、`hospital_minato`、`hotel_taito`、`library_setagaya`、`cafe_shibuya_vs_shinjuku`、`tag_top3_cuisine`、`tag_ramen_vs_sushi`、`nom_shibuya_relation`、`nom_setagaya_south`、`nom_tokyo_tower`、`route_auto_km`、`route_walk_minutes`、`sparql_ward_count`、`stations_count`。

止まった Goal（2 周目）: `cafe_vs_restaurant_shibuya`、`tag_sushi_count`、`sparql_min_relation_ward`、`sparql_four_char_wards`、`ward_pop_max`、`ward_pop_total`、`stations_northmost`。

## 6. 残っている課題

各項目の根拠は括弧の文書にある。

1. 比較の step が勝者を出さない。「どちらが多いかを示す」 Intent に、件数と差だけを出すコードが続き、step の Critic も通す。step Critic への指示は、保存済みの step の再生では効いたが、実行中には効かなかった（[adaptive_round_1.md](adaptive_round_1.md)）。決定的な検査（比較を求める Intent の出力に勝者の値があるか）は未着手。
2. ローカル集計の契約検査（位置参照と既定値の禁止）は、保存済みのローカル集計コードの 25% に当たる。実 LLM が 2 回の作り直しで契約を守れるかは、まとまった数では測っていない（[local_aggregation_contract.md](local_aggregation_contract.md)）。
3. step の Critic は、件数 0 を通すことがある。プロンプトでは防ぎ切れない。0 が正しい Goal がベンチマークに無いので、決定的に拒否したときの誤拒否は測れない（[critic_accepted_wrong.md](critic_accepted_wrong.md)）。
4. 最終 Critic が厳しすぎる例がある（1 周目の `nom_setagaya_south` で bbox の `south` が答えなのに 3 回失敗、2 周目の `tag_sushi_count` で正しい 24,089 を 3 回拒否）。一方で、harness の judge は甘い例がある（`sparql_min_relation_ward` で、一覧に答えが含まれるだけで受け入れる）（[adaptive_round_1.md](adaptive_round_1.md)）。
5. step の Critic が、自分で数え直して正しい答えを棄却する（`sparql_four_char_wards` の 4 文字の区の数 3 を、8 と数え直して棄却）（[adaptive_round_1.md](adaptive_round_1.md)）。
6. Planner の形式エラー: `利用データセット: id` の 1 行書きが拒否され、答えが出たあとでも止まる（`ward_pop_max`、`ward_pop_total`）。調査項目の途中の余分な行なども未修正（[identity_references.md](identity_references.md)、[adaptive_round_1.md](adaptive_round_1.md)）。2 周目の停止の最大の原因（[adaptive_round_2.md](adaptive_round_2.md)）。
6a. Planner が、拒否された `対象: 東京23区` を書き直さずに繰り返し、計画の失敗の上限（3 回）で止まる。拒否の理由は履歴で見えている（[adaptive_round_2.md](adaptive_round_2.md)）。
6b. `対象:` の検査は、Goal に含まれる語なら Dataset の名前（`駅データ`）なども通す（[adaptive_round_2.md](adaptive_round_2.md)）。
7. Planner が履歴の値（459、343 など）を Intent の文面に書き写す（[entity_target_e2e.md](entity_target_e2e.md)）。
8. Planner が人口を Overpass に求めるなど、Dataset と Service の選び方（`ward_pop_total`）。Dataset の step が 30 秒で timeout した原因は見ていない。
9. semantic repair は既定で無効。救済を oracle で確認できていない。出力のキーの変化を拒否する検査は未実装（[semantic_repair.md](semantic_repair.md)）。
10. `integration/test_burger_goal.py` は新しい契約に合わせて書き換えたが、一度も実行していない。
11. 実 LLM を使う integration テスト（`test_service_learning` の geosparql と taginfo_overpass、`test_adaptive_goal`）は、実行ごとに通ったり落ちたりする。
12. どの測定も 1 周か少数回で、LLM の揺らぎは測っていない。以前の一括計画の方式との比較は、方式と時期が違い、対照ではない。

## 7. 道具と再現

前提:

- Python は repo の `.venv/bin/python`（anaconda の python は DuckDB 1.5.6 が無い）。
- LLM: `http://10.108.45.102:8080/v1/chat/completions`（`gvt-llm`、`geo_voyager/llama_client.py`）。embedding: 環境変数 `GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080`、`GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding`。
- ベンチマークの環境（`bench/infra.py`）: 隔離 network の Worker と、1 つの Gateway（メモリ 1g。128MB では OOM で落ちた）。Worker の image は `geo-voyager-worker:duckdb-1.5.6`。

```bash
# 単体テスト（LLM、HTTP、Docker を使わない）
.venv/bin/python -m pytest tests -q -W error
# サービス契約の integration（自前サービスに問い合わせる。届かなければ skip）
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest integration/test_taginfo_contract.py integration/test_valhalla_contract.py -q --import-mode=importlib
# 適応ループの E2E（Goal id を並べる。:inject、:earlydone、:twotargets=N、:max=N の指定ができる）
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  PYTHONPATH=. .venv/bin/python -u -m bench.run_adaptive --out ~/tmp/geo-voyager-bench/NAME GOAL_ID ...
# 集計（DONE で終わったものだけを正解に数える）
PYTHONPATH=. .venv/bin/python -m bench.adaptive_summary ~/tmp/geo-voyager-bench/NAME/results.jsonl
```

| 道具 | 用途 |
|---|---|
| `bench/goals.py` | 22 Goal と、Planner などに渡さない独立の oracle と judge |
| `bench/run_goals.py`、`bench/report.py`、`bench/taxonomy.py`、`bench/compare.py` | 一括計画の経路のベンチマーク、集計、失敗の分類、2 回の比較（Fisher の正確確率検定） |
| `bench/run_adaptive.py`、`bench/adaptive_trace.py`、`bench/adaptive_summary.py` | 適応ループの E2E、人が読む trace、結果と検査の発火の集計 |
| `bench/replay_repair.py`、`bench/replay_repair_fallback.py` | runtime repair の再生 |
| `bench/replay_semantic.py`、`bench/semantic_replay_stats.py` | semantic repair の再生 |
| `bench/replay_critic.py`、`bench/replay_final_critic.py`、`bench/replay_step_critic.py` | Critic、最終 Critic、比較などの step の Critic を、保存済みの入力で聞き直す |
| `bench/check_oracles.py` | oracle を 1 回ずつ実行して確かめる |

生の実行記録は `~/tmp/geo-voyager-bench/<名前>/`（実行ごとの LLM のプロンプトと応答、`results.jsonl`、`trace.md`）にあり、文書が引く記録は `docs/evidence/` に写してある。

## 8. 測り方で学んだこと

- harness の judge は最後の Observation だけを見る。ループが DONE で終わったかを見ないと、止まった実行を正解に数える（10-10 に 15/22 と誤って報告し、12/22 に訂正した）。
- 再生（保存済みの入力で Critic を聞き直す）は安くて速いが、実行中と同じプロンプトにならないことがある（前段の Observation や対象の照合の指示を省くなど）。step Critic の指示は、再生では効き、実行中には効かなかった。
- 2 つ直して動いても、どちらが効いたかは分からない。repair の v1 は「失敗行」と「試行履歴」を同時に入れたので、切り分けていない。
- trace から見つけて直すと、その Goal に合わせ込む恐れがある。直したら、全 Goal を 1 周流して確かめる。
- 契約を締めると、別の失敗を生むことがある。位置で選ぶことを禁じた結果、何を測ったかが出力に無い `cafe_vs_restaurant_shibuya` は、2 つの件数を区別できなくなった（出力に `tag` を含める契約で対処）。
- 自前サービスの振る舞いは、説明に書く前に実際に問い合わせて確かめる。Valhalla の失敗は、説明の不足ではなく、`call_service` の空白の `+` だった。

## 9. 文書の一覧

- 全体と最新: この文書、[adaptive_round_1.md](adaptive_round_1.md)、[adaptive_round_2.md](adaptive_round_2.md)
- 究極のゴールに向けて（study-geoai-algo-py の水準の分析）: [analysis_sandbox_design.md](analysis_sandbox_design.md)、[study_geoai_goals_proposal.md](study_geoai_goals_proposal.md)、[analysis_sandbox.md](analysis_sandbox.md)（実装と G1 の再現）
- 計画（Planner）: [observation_driven_planning.md](observation_driven_planning.md)、[observation_driven_recovery.md](observation_driven_recovery.md)、[planner_service_contract.md](planner_service_contract.md)
- 対象: [identity_references.md](identity_references.md)、[target_ref.md](target_ref.md)、[entity_target_e2e.md](entity_target_e2e.md)
- コード生成の契約: [local_aggregation_contract.md](local_aggregation_contract.md)
- repair: [repair_benchmark.md](repair_benchmark.md)、[runtime_repair_defaults.md](runtime_repair_defaults.md)、[semantic_repair.md](semantic_repair.md)
- Critic: [critic_accepted_wrong.md](critic_accepted_wrong.md)、[critic_fallback.md](critic_fallback.md)
- 失敗の分類: [failure_categories.md](failure_categories.md)
- Skill の検索と再利用、サービスの学習（10-08〜09）: [skill_evaluation.md](skill_evaluation.md)、[skill_growth.md](skill_growth.md)、[vector_retrieval.md](vector_retrieval.md)、[intent_execution.md](intent_execution.md)、[service_learning.md](service_learning.md)、[burger_goal_learning.md](burger_goal_learning.md)、[burger_count_and_natural_repair.md](burger_count_and_natural_repair.md)
