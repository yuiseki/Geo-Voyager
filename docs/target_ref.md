# 対象を stable ID で識別する（TargetRef）

2026-10-09 に、対象の識別を、名前から stable ID に変えた。名前は表示と、最初の調べ物にだけ使う。

## 背景

[identity_references.md](identity_references.md) で、対象を名前と ID で参照するようにしたが、解決の主キーは名前だった。実行の記録で、同じ場所が、Goal では `港区`、Nominatim の答えでは `港区, 東京都, 日本` と呼ばれ、Planner が `対象: 港区` と書くと、名前の一致で対象を解決できず step が失敗する実行があった（[observation_driven_recovery.md](observation_driven_recovery.md)）。名前は揺れるが、ID は揺れない。

## TargetRef

`geo_voyager/target_ref.py`。次の 3 つを持つ。

| 項目 | 意味 |
|---|---|
| `name` | 表示名。人が読む。揺れる |
| `id_type` | ID の種類（`relation_id`、`id` など） |
| `id_value` | ID の値。常に文字列（`1761717` も `"1761717"` も同じ） |

- 同じ対象かどうかは、ID で決める（`same_target`）。`id_type` と `id_value` が同じなら、名前が違っても同じ対象。同じ名前でも ID が違えば別の対象。
- ID を持たない `TargetRef`（名前だけ）は「まだ調べていない対象」で、`resolved` が偽。最初の step（例えば「港区の ID を取得する」）の対象は、この形になる。名前だけの対象は、名前でしか比べられず、ID を持つ対象とは同じと見なさない。

## 各部品の扱い

| 部品 | 扱い |
|---|---|
| `Intent` | `target_name` をやめ、`target: TargetRef \| None` を持つ。`target_name` は表示名を返す読み取り専用の property として残した（変更しない部品が使っているため） |
| 発見 | `discover_targets` が、前段の Observation から名前と ID を持つ対象を、`TargetRef` として取り出す。対象は ID で数える。同じ ID が別の名前で現れても、新しい対象ではない（最初の名前を残す）。同じ名前で ID が違えば、別の対象 |
| 履歴 | `HistoryEntry.targets` と `GoalHistory.targets()` が `TargetRef` を持ち、次の step 以降に引き継ぐ。同じ step かどうか（反復の検出）も、対象は ID で比べる |
| Planner | `対象:` に書かれた名前または ID を、履歴にある既知の `TargetRef` に解決する（`resolve_reference`）。ID（`relation_id=1761717`）を最優先、次に名前の完全一致、次にカンマの前の名前（`港区` と `港区, 東京都, 日本`）。同じ名前の対象が 2 つの ID に当たるときは、名前では決められないので拒否し、候補の ID を挙げる（`PlannerRejected`。履歴に残り、Planner は ID で書き直せる）。既知でない名前は、名前だけの `TargetRef`（これから調べる対象）になる。プロンプトの「判明した対象」には ID も出る |
| Worker | コードに `intent_target` を渡す。ID がある対象は `{"name", "id_type", "id_value"}`、名前だけの対象は `{"name"}` |
| Generator | ID がある対象では、コードに ID を主キーとして使わせる。前段の Observation から探すときも、`id_type` の値が `id_value` と一致する object を選ぶ（接続例）。名前の一致では選ばず、ID が一致する object が無ければ例外にする。名前だけの対象は、従来どおり名前で探す |
| Critic | ID がある対象では、まず決定的に検査する（`identity_conflict`）。Observation に対象と同じ種類の ID を持つ object があり、その中に対象の ID が 1 つも無ければ、名前が同じでも失敗にする。この場合はモデルを呼ばない。ID が一致するなら、名前が違っていても、モデルに判定させる。前段から ID で見つけた対象を「解決済み参照対象」としてプロンプトに出す |
| provenance | `Intent.target`（ID を含む）が、記録（`asdict`）と履歴の entry に残る。`bench/adaptive_trace.py` の trace には、`target_ref`、各 step の前に判明していた対象、その step で初めて判明した対象が、ID つきで出る。`bench/run_goals.py` の記録にも `target` を足した |

### 同名異 ID の扱い

同じ名前で ID が違うものは、別の対象として、各所で明示的に拒否する。

- Planner: 名前が 2 つの ID に当たると、`PlannerRejected` で拒否し、ID で書くよう促す。
- 生成コード: 前段に対象の ID を持つ object が無ければ、`assert` で例外になる（ID の不一致を、名前の一致で通さない）。
- Critic: 同じ種類の ID があって対象の ID と一致しなければ、モデルを呼ばずに失敗にする。

## 変更していないもの

- 適応ループ（`geo_voyager/goal_executor.py`）、runtime repair（`SkillCandidateRepairer`）、semantic repair（`SemanticRepairer`）、`IntentExecutor` は、編集していない。semantic repair は、`Intent.target_name`（表示名）を使い続ける。そのプロンプトは、対象を `intent_target["name"]` と書いたままである。

## 確認（focused test のみ。大規模なベンチマークは流していない）

| 確認項目 | テスト |
|---|---|
| 表示名が違っても、同じ stable ID なら成功する | 単体: Critic がモデルを呼び判定する（`test_the_critic_asks_the_model_when_the_id_matches_whatever_the_name`）、ID で前段の対象を見つける、Planner が短い名前を既知の対象に解決する。実 Docker: 前段が `港区, 東京都, 日本`、対象が `港区` でも、ID で見つかって成功する（`integration/test_target_ref.py`） |
| 同名異 ID は失敗する | 単体: Critic がモデルを呼ばず失敗にする、Planner が拒否して ID を挙げる、ID を指定すると決まる。実 Docker: 同じ名前で ID が違う前段に対し、生成コードの例が `no object has the target id` で失敗する |
| 前段で得た TargetRef を次の step が再利用する | 単体: step の Observation から `TargetRef` が履歴に入り、同じ ID が別の名前で現れても新しい対象にならず、次の Planner の呼び出しで ID つきで見える。実 Docker: 1 つ目の step の出力から得た `TargetRef` で、2 つ目の step（別名の `港区`）が成功する |

- 単体テスト: 650 件が通る。
- 実 Docker の focused integration `integration/test_target_ref.py`（LLM もサービスも使わない）: 4 件が通る。
- 既存の focused integration（`test_critic_llm`、`test_service_primitive`、`test_execution_failure`、`test_fetch_gateway`、`test_service_learning`、`test_adaptive_goal`）を合わせて流すと、16 件のうち 15 件が通った。落ちた 1 件は `test_service_learning` の `geosparql` で、同じテストの再実行で通る回と落ちる回があった。この Intent には対象が無く、今回変更した経路を通らない。実 LLM のコード生成の揺らぎである。

## 限界

- 生成コードが、実際の LLM で ID 優先の接続例どおりに書かれるかは、測っていない。確かめたのは、プロンプトの内容と、その接続例と同じコードが動くこと（実 Docker）である。
- Critic の決定的な検査は、対象と同じ種類の ID（`id_type` と同じキー）を持つ object がある場合だけ働く。ID が別のキー（例えば `osm_id`）で出ていれば、検査されず、モデルの判定に任せる。
- Planner の名前の解決は、完全一致と、カンマの前の名前の一致だけである。表記の揺れを、これ以上は吸収しない。名前が既知の対象のどれとも合わなければ、名前だけの対象（これから調べる対象）になる。
- 古い実行の記録（`target_name` だけを持つ）は、`bench/replay_semantic.py` が名前だけの対象として読み直す。

## 再現

```bash
.venv/bin/python -m pytest tests -q -W error
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest integration/test_target_ref.py -q -W error --import-mode=importlib
```
