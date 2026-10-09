# 観測に基づく Planner（1 step ずつ決める経路）

2026-10-09 に、Planner が Goal 全体の Intent を最初に作る代わりに、1 つ実行するごとに次の Intent を 1 件だけ決める経路を追加した。
評価は大規模なベンチマークを流さず、5 件の実行（4 Goal）で、確認項目だけを実 LLM、実 Docker、実サービスで確かめた。

## 変更点

- `Planner.next(goal, history) -> Intent | DONE`。1 回のモデル呼び出しで、次の Intent を 1 件だけ決めるか、`DONE` を返す。`DONE` は明示的な値（`geo_voyager/planner.py` の `DONE`）で、応答の最初の行が `DONE` のときだけ返す。応答に Intent が複数あっても、最初の 1 件だけを使う。
- `GoalExecutor.execute_adaptive(goal)`。1 step 実行するごとに Planner を呼び直す。Goal 全体を最初に計画する経路（`Planner.plan_goal` と `GoalExecutor.execute`）は残したが、この新しい経路では使わない。`plan_goal` のプロンプトは、共通のルール文を切り出したあとも 1 文字も変わっていない（保存したプロンプトとの一致を、テストで保つ）。
- `GoalHistory`（`geo_voyager/goal_history.py`）。追記だけできる履歴。
- `IntentExecutor` は変更していない。semantic repair は既定オフのまま、触っていない。

### 履歴に入るもの

各 step を `HistoryEntry` として追記する。

| 項目 | 内容 |
|---|---|
| Intent | 実行した Intent（対象、リソース、前段の Observation を含む） |
| Observation | その step の出力 |
| Critique | Critic の判定と理由 |
| ExecutionFailure | 実行が失敗した場合の失敗 |
| Skill | 再利用した Skill と、学習した Skill の ID |
| 判明した対象 | その step の Observation から初めて得た名前と安定 ID（`name` と `relation_id` か `id`） |

履歴は追記だけで、既存の entry は変更できない（`frozen` な entry、`tuple` で返す `entries`、step 番号が連続することの検査）。
Planner のプロンプトには、全 step の要約（結果、失敗の最終行、Critic の理由、Observation の先頭、Skill）と、「判明した対象」の一覧が入る。

### 前段で初めて分かった名前と ID を使う

> 追記: 判明した対象は、その後 `TargetRef`（名前と ID の種類と値）で持つようになり、対象は ID で識別する（[target_ref.md](target_ref.md)）。以下は、名前を主キーにしていた時点の説明である。

Planner は、履歴の「判明した対象」にある名前を `対象: 名前` で指定して、次の Intent を作る。実行時には、これまでの成功した step の Observation が `previous_observations` として渡るので、生成コードは名前の一致で対象の ID を解決する（前の変更で入れた identity ベースの参照）。Planner は、Intent の文にも ID を書ける（記録では `港区 (relation_id: 1761717)` と書いた）。

### 停止条件

| 条件 | 停止理由 | 結果 |
|---|---|---|
| Planner が `DONE` を返した | `done` | 成功した step の Observation 全体を、Goal の文に対して Critic が判定する。失敗した場合は履歴に追記して Planner に戻る（[observation_driven_recovery.md](observation_driven_recovery.md)） |
| step 数が上限（既定 8）に達した | `max_steps` | Goal は失敗 |
| 成功済みの Intent をもう一度計画した、または失敗した同じ Intent を 2 回試した後にまた計画した | `repeated_intent` | Goal は失敗 |
| Planner の出力が不正 | `planner_failure` | 履歴に追記して再計画する。上限に達するか同じ失敗が繰り返されたら Goal は失敗 |

同じ Intent かどうかは、空白を揃えた文面、リソース、対象で比べる。step が失敗しても Goal は終わらず、Planner は失敗を見て再計画する。失敗した step の出力は、次の step には渡さない。

## 確認した結果

| 実行 | 停止 | step 数 | Goal の Critic | oracle との一致 | 所要時間 | Planner 呼び出し |
|---|---|---|---|---|---|---|
| `hospital_minato` | done | 2 | 成功 | 一致 | 34.2 秒 | 3 |
| `cafe_shibuya_vs_shinjuku` | planner_error | 2 | 失敗 | 不一致 | 29.9 秒 | 3 |
| `hospital_minato`（1 回目の失敗を注入） | done | 3 | 成功 | 一致 | 40.9 秒 | 4 |
| `tag_top3_cuisine` | done | 5 | 失敗 | 不一致 | 88.7 秒 | 6 |
| `cafe_shibuya_vs_shinjuku`（最大 2 step） | max_steps | 2 | 失敗 | 不一致 | 35.0 秒 | 2 |

全体を最初に計画する方式では、Planner の呼び出しは 1 回だった。この方式では、step 数に 1 を足した回数だけ呼ぶ（上の表の「Planner 呼び出し」）。

### 確認項目との対応

| 確認項目 | 記録 |
|---|---|
| 前段で初めて分かった対象を次の step で使える | `hospital_minato` の 2 件で、step 1 が港区の ID を得て、step 2 が「港区 (relation_id: 1761717)」で件数を取った。`cafe_shibuya_vs_shinjuku` の step 2 も、step 1 で判明した渋谷区を知っていた |
| failure 後に再計画できる | 注入した失敗の後、Planner は使うサービスを Nominatim から GeoSPARQL に変えた Intent を出し、DONE まで進んだ。注入なしの `tag_top3_cuisine` でも、実行の失敗が 3 回続く間、毎回 Intent を変えて再計画した |
| learned Skill を後続の step で再利用できる | `cafe_shibuya_vs_shinjuku` の step 2 が、step 1 で学習した Skill（`9204890a`）を再利用した |
| DONE に到達できる | `hospital_minato` の 2 件で、Goal の Critic が成功とし、oracle と一致した。`tag_top3_cuisine` も `DONE` に到達したが、答えは不正解だった（下記） |
| 無限に反復しない | 最大 2 step の設定で `max_steps` により止まった。反復の検出と最大 step 数は、単体テストでも確かめた |

### 分かったこと

- `cafe_shibuya_vs_shinjuku`（制限なし）は、step 3 で止まった。Planner が「渋谷区と新宿区の件数」を 1 つの Intent にまとめ、`対象:` を 2 行書いたため、「1 つの Intent は対象を 1 つしか持たない」という契約に反するとして、パーサが拒否した。Goal は失敗したが、理由つきで止まり、無限に続くことはなかった。出力形式を間違えたときの再計画は、この時点では入れていなかった。その後、計画の失敗を履歴に追記して再計画する処理を入れた（[observation_driven_recovery.md](observation_driven_recovery.md)）。
- `tag_top3_cuisine` は、5 step かけて DONE に至った。step 1 から 3 は実行が失敗し、step 4 は Critic が棄却し（`cuisine` でなく `name` キーの値が返った）、step 5 は Critic が成功としたが、答えは不正解だった。DONE の後の Goal 全体の Critic が、「上位 3 つの値が提示されていない」と失敗にした。step の Critic の偽陽性を、最後の判定が止めた例である。
- Planner は、対象でないもの（「飲食店タグの値上位 3 件」「飲食」）を `対象:` に書くことがある。既に分かっている課題で、今回の変更では直していない。
- 5 件とも 1 回ずつの実行で、LLM の揺らぎは測っていない。注入した失敗の実行は、失敗の再計画を見るための意図的な注入である。

## テスト

- 単体テスト: 573 件が通る。履歴の追記専用性、対象の発見、`Planner.next`（DONE、1 件だけ、履歴のプロンプト、ローカル step の条件）、`execute_adaptive`（各 step 後の呼び出し、失敗後の再計画、成功した step の Observation だけを渡すこと、最大 step、反復の検出、計画のエラー）のテストを含む。
- focused integration: 既存の 11 件（`test_critic_llm`、`test_service_primitive`、`test_execution_failure`、`test_fetch_gateway`、`test_service_learning`）と、新しい `integration/test_adaptive_goal.py`（実 LLM。前段で判明した対象を後の step が知っていること、DONE に到達すること、oracle と一致すること）の 12 件が通る。
- `integration/test_burger_goal.py` は、前の変更で書き換えたまま、実行していない。

## 再現

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.run_adaptive --out ~/tmp/geo-voyager-bench/adaptive_e2e \
  hospital_minato cafe_shibuya_vs_shinjuku hospital_minato:inject tag_top3_cuisine cafe_shibuya_vs_shinjuku:max=2
```

引数は Goal の ID。`:inject` は 1 つ目の step を失敗させ、`:max=N` は step 数の上限を指定する。
生の記録は [evidence/observation_driven_planning/](evidence/observation_driven_planning/) にある。

- `results.jsonl`: 実行ごとの記録
- `trace_*.md`: 実行ごとの trace（下に再掲）
- `planner_prompt_after_failure.txt`、`planner_reply_after_failure.txt`: 注入した失敗の直後に Planner へ渡したプロンプトと、その応答

## 実行 trace

#### hospital_minato (最大 8 step)
Goal: 港区の amenity=hospital（病院）の OSM 地物数を求める。

stop: done / Goal の Critic: 成功（港区の病院数（22件）が明示されているため、要求された調査結果が得られている。） / oracle との一致: True

step 1: 港区のOSM relation IDの取得
- 対象: 港区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: 港区のOSM relation IDとして1761717が取得された
- Observation: {"name": "港区", "relation_id": "1761717"}
- この step で初めて判明した対象: [{'name': '港区', 'relation_id': '1761717'}]
- 学習した Skill: 6ba725f0

step 2: 港区の amenity=hospital（病院）の OSM 地物数を求める
- 対象: 港区 / リソース: overpass
- この step の前に判明していた対象: [{'name': '港区', 'relation_id': '1761717'}]
- 結果: 成功（実行 2 回）
- Critic: Observationは港区(relation_id: 1761717)のamenity=hospitalの地物数(22)を報告しており、Intentの要求に完全に一致している。
- Observation: {"name": "\u6e2f\u533a", "relation_id": "1761717", "count": 22}
- 学習した Skill: 58f69e56

#### cafe_shibuya_vs_shinjuku (最大 8 step)
Goal: 渋谷区と新宿区の amenity=cafe の OSM 地物数をそれぞれ求め、どちらが多いかを示す。

stop: planner_error / Goal の Critic: 失敗（Goal を完了できなかった: planner_error（ValueError: An Intent has more than one 対象 line, but names one target）） / oracle との一致: False

step 1: 渋谷区の OSM relation
- 対象: 渋谷区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: Observation に渋谷区の OSM relation の名前と ID が含まれているため
- Observation: {"name": "渋谷区", "relation_id": "1759477"}
- この step で初めて判明した対象: [{'name': '渋谷区', 'relation_id': '1759477'}]
- 学習した Skill: 9204890a

step 2: 新宿区の OSM relation
- 対象: 新宿区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: [{'name': '渋谷区', 'relation_id': '1759477'}]
- 結果: 成功（実行 1 回）
- Critic: Observationのnameが「新宿区」でIntentの対象と一致し、relation_idが提供されているため、要求された調査結果が答えている。
- Observation: {"name": "新宿区", "relation_id": "1758858"}
- この step で初めて判明した対象: [{'name': '新宿区', 'relation_id': '1758858'}]
- 再利用した Skill: 9204890a

#### hospital_minato (1 回目の失敗を注入) (最大 8 step)
Goal: 港区の amenity=hospital（病院）の OSM 地物数を求める。

stop: done / Goal の Critic: 成功（港区のamenity=hospitalの地物数（22件）がObservationに含まれているため、Intentの要求を満たしている。） / oracle との一致: True

step 1: 港区の relation_id の取得
- 対象: 港区 / リソース: nominatim / 失敗を注入した step
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: injected failure for the first step
- Critic: Generated Python execution failed (injected)

step 2: 港区の relation_id の取得
- 対象: 港区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: Observationは港区のrelation_idとして1761717を返しており、Intentの要求を満たしている。
- Observation: {"name": "港区", "relation_id": "1761717"}
- この step で初めて判明した対象: [{'name': '港区', 'relation_id': '1761717'}]
- 学習した Skill: 50ddc941

step 3: 港区 (relation_id: 1761717) 内の amenity=hospital の地物数
- 対象: 港区 / リソース: overpass
- この step の前に判明していた対象: [{'name': '港区', 'relation_id': '1761717'}]
- 結果: 成功（実行 2 回）
- Critic: Observationは、指定された港区（relation_id: 1761717）内のamenity=hospitalの地物数が22件であることを示しており、Intentの要求を満たしている。
- Observation: {"name": "\u6e2f\u533a", "relation_id": "1761717", "key": "amenity", "value": "hospital", "count": 22}
- 学習した Skill: 8cee879d

#### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: done / Goal の Critic: 失敗（上位3つの値がソート順で提示されていないため、要求された調査結果が満たされていない。） / oracle との一致: False

step 1: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: ValueError: No values found for cuisine key
- Critic: Generated Python execution failed

step 2: Taginfo API で cuisine キーの値を使用数順に上位3件取得
- 対象: 対象: 飲食店タグの値上位3件 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 502: <!DOCTYPE HTML>
- Critic: Generated Python execution failed

step 3: Taginfo API の /api/4/key/tags エンドポイントで tag=cuisine, mode=frequency, count=3 を指定して、cuisine キーの値を使用数順に上位3件取得
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: AssertionError: Expected 3 results
- Critic: Generated Python execution failed

step 4: Taginfo API で cuisine キーの値を count 順に上位10件取得
- 対象: 飲食 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 1 回）
- Critic: cuisine キーの値ではなく name キーの値が取得されており、Intentの要求を満たしていないため。
- Observation: {"results": [{"key": "name", "value": "Cuisine communautaire", "count": 131}, {"key": "name", "value": "Cuisine", "count": 104}, {"key": "fixme", "value": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"key": "name", "value": "Cuisine centrale", "count": 54}, {"key": "name", "val

step 5: Taginfo API で cuisine キーの値を使用数順に上位3件取得
- 対象: 飲食店タグの値上位3件 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: 指定された上位3件のcuisineキーの値と使用数が取得されているため。
- Observation: [{"name": "name=Cuisine communautaire", "relation_id": "name=Cuisine communautaire", "count": 131}, {"name": "name=Cuisine", "relation_id": "name=Cuisine", "count": 104}, {"name": "fixme=Freeform tag `cuisine` used, to be doublechecked", "relation_id": "fixme=Freeform tag `cuisine` used, to be doubl
- この step で初めて判明した対象: [{'name': 'name=Cuisine communautaire', 'relation_id': 'name=Cuisine communautaire'}, {'name': 'name=Cuisine', 'relation_id': 'name=Cuisine'}, {'name': 'fixme=Freeform tag `cuisine` used, to be doublechecked', 'relation_id': 'fixme=Freeform tag `cuisine` used, to be doublechecked'}]
- 学習した Skill: cea0b79f

#### cafe_shibuya_vs_shinjuku (最大 2 step)
Goal: 渋谷区と新宿区の amenity=cafe の OSM 地物数をそれぞれ求め、どちらが多いかを示す。

stop: max_steps / Goal の Critic: 失敗（Goal を完了できなかった: max_steps） / oracle との一致: False

step 1: 渋谷区の OSM 関係 ID を取得
- 対象: 渋谷区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: 渋谷区のOSM関係IDが取得された
- Observation: {"name": "渋谷区", "relation_id": "1759477"}
- この step で初めて判明した対象: [{'name': '渋谷区', 'relation_id': '1759477'}]
- 学習した Skill: 888dde8c

step 2: 新宿区の OSM 関係 ID を取得
- 対象: 新宿区 / リソース: yuisekin-geosparql
- この step の前に判明していた対象: [{'name': '渋谷区', 'relation_id': '1759477'}]
- 結果: 実行失敗（実行 3 回）、失敗: AssertionError: 対象が見つかりません
- Critic: Generated Python execution failed
