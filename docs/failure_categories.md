# 多様な Goal での失敗の種類の測定

2026-10-09 に、21 本の Goal を各 5 回、Critic の設定を変えて 2 条件で実行し、どの種類の失敗が支配的かを測った。
repair のロジック、Planner、Generator は変更していない。semantic repair は入れていない。
人間は Candidate のコードを一切修正していない。

先行の測定は [repair_benchmark.md](repair_benchmark.md) にある。今回は Goal を Overpass 以外へ広げ、失敗を分類した。

## 測り方

### Goal

21 本。使うサービスまたは Dataset で 6 系統に分けた。正解は Goal ごとの独立した oracle で取り、Planner、Generator、Repairer、Critic には渡していない。

| 系統 | Goal 数 | 内容 |
|---|---|---|
| overpass | 6 | 区ごとの OSM タグの地物数（cafe、ramen、hospital、hotel、library）と、cafe と restaurant の比較 |
| taginfo | 3 | cuisine=sushi の使用数、cuisine の上位 3 値、ramen と sushi の比較 |
| nominatim | 3 | 渋谷区の relation ID、世田谷区の最南端の緯度、東京タワーの緯度経度 |
| valhalla | 2 | 2 点間の自動車の距離（km）と徒歩の所要時間（分） |
| geosparql | 3 | 区の数、relation ID が最小の区、区名が 4 文字の区の数 |
| dataset | 4 | 東京 23 区の人口最大の区と人口の合計、駅データの件数と最北の駅 |

全 Goal の oracle は、本計測の前に 1 本ずつ実行し、値を確かめた（`bench/check_oracles.py`）。

### 条件

- 条件 A: Critic は従来のまま（thinking なし）。105 実行。
- 条件 B: Critic に `enable_thinking=True` を渡す（`Critic(thinking=True)`）。105 実行。
- どちらも Goal ごと・周回ごとに空の Skill Library で始める。LLM は同じローカル llama.cpp。
- 製品コード（`geo_voyager/`）は、全実行を通して同一だった（最初と最後の計測コミット間で `git diff` が空）。実行ごとに記録したコミットが異なるのは、計測中に `bench/` を更新したため。
- repair は、前回の測定で入れた「失敗行と試行履歴を渡す」版（v1）のまま。再サンプリング（v2）は既定でオフ。

### 記録と分類

各実行で、Goal の正誤、ステップ数、各 Intent、実行の成否、Critic の成否、oracle の出力、最初に誤ったステップ、使用したサービス・Dataset を記録した。
failure category への分類は、集計時に記録から導く（`bench/taxonomy.py`）。分類規則を直しても再実行は要らない。

| category | 規則 |
|---|---|
| planning | 計画が拒否された（形式不正、未登録のサービスや Dataset）。または Goal が必要とするリソースをどの Intent も宣言しない |
| codegen | 最初に誤ったステップで、Candidate の連鎖が全て失敗した（一過性のサービスエラーだけの場合を除く）。または Generator と Repairer が出力形式を破った |
| execution | sandbox のタイムアウト、Docker、ネットワークなどの例外。または連鎖が一過性のサービスエラーだけで尽きた |
| retrieval-selection | 実行は成功したが、Goal の対象の区と別の relation ID を返した |
| semantic-completion | 実行は成功したが Critic が棄却した。または全ステップが通ったのに答えが誤り（最終ステップがローカル集計でない場合） |
| aggregation | semantic-completion と同じ条件で、最終ステップが前段の観察だけを使うローカル集計の場合 |
| critic-format | Critic が出力形式を破り、例外が Goal の実行全体を止めた |

これは記録された信号に基づく推定である。各 category から 30 件ほど（planning、codegen、execution、retrieval-selection、critic-format、semantic-completion、aggregation）を、保存したプロンプトと応答、観察で読んで確かめた。

## 測定中に起きた問題と、その扱い

結果の数値を読む前提として、有効性に関わる出来事を記す。

- ゲートウェイの OOM。条件 A の途中で、ゲートウェイの Docker コンテナがメモリ上限（128MB）で kill された（`OOMKilled`、終了コード 137）。直前のログは、Dataset の Parquet の範囲取得の後の 502 だった。
  - 以後の実行は、サービスに届かず無効になった。ゲートウェイが落ちた時刻より後の行と、落ちる前から影響を受けていた可能性がある Dataset 系の行（合計 24 件）を破棄し、`evidence/failure_categories/discarded_gateway_oom.jsonl` に残した。
  - ゲートウェイのメモリを 1GB に増やして、不足分を再実行した。
- 再開時の落ち方。再開を指示した実行が、止めたときの作りかけのディレクトリに衝突して落ちた。条件 A の不足分 13 実行は、条件 B の終了後に流した。残骸は退避する処理を入れた。
- judge の欠陥が 2 つあった。
  - judge が JSON の `\uXXXX` エスケープを解釈していなかった。名前を照合する Goal で、正しい答えが不正解になっていた。逆に、エスケープ列の中の数字が小さな件数に偶然一致して、誤って正解になった行もあった（`sparql_four_char_wards` の 1 件）。
  - 比較 Goal の judge が、勝者の件数だけでなく両方の件数を要求していた。
  - どちらも直し、記録済みの最終出力から正否を再判定した（再実行はしていない）。記録時の判定は各行の `correct_recorded` に残っている。
- oracle の失敗。oracle は一過性のサービスエラーで失敗することがある。最大 3 回リトライし、それでも取れなかった実行は「未測定」として正解率の分母から外した。条件 A で 2 件、条件 B で 7 件。主に Dataset 系の Goal。

## 結果

以下の数値は再判定後。

### 全体

| 指標 | 条件 A（Critic 従来） | 条件 B（Critic thinking） |
|---|---|---|
| 実行数 | 105 | 105 |
| 未測定（oracle 不可） | 2 | 7 |
| Goal の正解 | 50 / 103（48.5%） | 42 / 98（42.9%） |
| Critic の偽陽性（成功と判定したが誤り） | 4 | 4 |
| Critic の偽陰性（失敗と判定したが正しい） | 7 | 4 |
| Critic の出力形式エラーで止まった実行 | 0 | 2 |
| success@0 | 65.6% | 66.2% |
| success@1 | 81.9% | 78.1% |
| success@2 | 85.0% | 85.4% |
| 振動（同じコードに戻った連鎖） | 14 | 13 |
| 1 実行の平均所要時間 | 30 秒 | 41 秒 |

Critic の thinking を有効にしても、Goal の正解率に改善は見えない（48.5% と 42.9% の差は、この数では揺らぎと区別できない）。偽陰性は 7 から 4 に減ったが、件数が少ない。偽陽性は変わらず、出力形式エラーで Goal が止まる実行が 0 から 2 に増え、所要時間も約 1.4 倍になった。

Critic が失敗と判定した時点で GoalExecutor は Goal を打ち切るので、偽陰性は、正しい途中結果を捨てる形で正解率を下げる。

### failure category（A と B を合わせた 201 実行、失敗 109 件）

| category | 件数 | 割合 |
|---|---|---|
| codegen | 40 | 36.7% |
| semantic-completion | 27 | 24.8% |
| planning | 15 | 13.8% |
| aggregation | 13 | 11.9% |
| execution | 8 | 7.3% |
| retrieval-selection | 4 | 3.7% |
| critic-format | 2 | 1.8% |

条件別では、条件 A が codegen 21、semantic-completion 15、planning 5、execution 5、aggregation 4、retrieval-selection 3。条件 B が codegen 19、semantic-completion 12、planning 10、aggregation 9、execution 3、critic-format 2、retrieval-selection 1。

最初に誤ったステップは、ステップ 1 が 45 件、ステップ 2 が 37 件、ステップ 3 が 5 件、ステップ 4 が 4 件（残りの 18 件は実行全体が例外で止まったため、ステップがない）。

支配的なのは、規則どおりに数えると codegen（37%）で、次に semantic-completion（25%）である。ただし、後述のとおり、semantic-completion と aggregation の一部は、計画の誤りが原因とみられる。

### 系統別の正解率（A と B を合わせた値）

| 系統 | 正解 | 主な失敗 |
|---|---|---|
| geosparql | 23 / 30 | semantic-completion 7 |
| nominatim | 23 / 30 | aggregation 4 |
| taginfo | 14 / 30 | semantic-completion 10、aggregation 3 |
| overpass | 23 / 60 | codegen 17、planning 9、aggregation 4、retrieval-selection 4 |
| valhalla | 4 / 20 | codegen 10、semantic-completion 6 |
| dataset | 5 / 40 | codegen 10、execution 8、planning 4 |

表の分母は未測定の実行を含む（dataset は 40 実行のうち 9 件が未測定で、失敗の内訳に現れるのは 26 件）。

dataset 系の結果は、sandbox のタイムアウト（Parquet の読み取りが制限時間に収まらない）と未測定が多く含まれる。コード生成の質だけを反映した数値ではない。

10 回とも正解しなかった Goal は、`cafe_vs_restaurant_shibuya`、`route_walk_minutes`、`stations_northmost`、`ward_pop_max`、`ward_pop_total` の 5 本。

### Planner の揺れ

同じ Goal でも、Planner は異なる計画を出す。Goal ごとの、異なる計画（各ステップが使うリソースの並び）の数は、1 から 5 だった。

- `ward_pop_max` は、10 実行で 5 通りの計画（最頻の計画は 38%）。
- `cafe_vs_restaurant_shibuya` は 4 通り（最頻は 40%）、ステップ数は 1 から 4 に散らばった。
- `route_auto_km`、`route_walk_minutes`、`tag_sushi_count`、`stations_count`、`nom_tokyo_tower` は 1 通りで、揺れなかった。
- 計画の段階で例外になった実行は、`ward_pop_total` で 10 中 5、`stations_northmost` で 4 だった。

### 「一覧の N 番目」テンプレート

Planner のプロンプトは、対象が複数あるとき「一覧の N 番目」の形で、1 対象ずつ測る Intent に分けるよう指示している。この形の Intent を含む計画は、含まない計画より、正解率が大きく低かった。

| | 実行数 | 正解 |
|---|---|---|
| 「一覧の N 番目」を含む計画 | 23 | 3 |
| 含まない計画 | 178 | 89 |

同じ Goal の中で比べても、傾向は同じだった（例: `cafe_shibuya` で含む 0/1 と含まない 6/9、`hotel_taito` で 0/1 と 5/9、`ramen_shinjuku` で 0/3 と 4/7）。テンプレートを含む計画の失敗 20 件は、codegen 10、planning 4、aggregation 3、semantic-completion 2、retrieval-selection 1 に分類されていた。
抜き取りでは、`sparql_four_char_wards` が「4 文字の区の数」を数える代わりに「一覧の 1 番目の区の文字数」を測り、`tag_top3_cuisine` が「一覧の 1 番目の値を上位 3 つとして特定する」という成り立たないステップを作っていた。

これはテンプレートが原因だという証明ではない。テンプレートを使うかどうかは Goal ごとの計画の揺れと混ざっており、23 実行と少ない。

## 抜き取り確認で分かった分類の限界

- 原因が複数重なる実行がある。例えば `ramen_shinjuku` の 1 ステップだけの計画は、Overpass を使うステップがない（planning）うえに、一覧の先頭の世田谷区を新宿区として返している（retrieval-selection）。規則は先に当たったほうを選ぶ。
- planning は過小に検出される。「Goal に必要なリソースを宣言しない」計画しか自動では見つけられず、「リソースは宣言したが、ステップが Goal に答えられない」計画（上の `sparql_four_char_wards` など）は semantic-completion や aggregation に分類される。
- 抜き取りで規則の誤りが 2 件見つかり、直した（`Candidate` の形式エラーを planning と誤分類、切り詰めた観察の対象 ID を誤判定）。

## 分かっていないこと

- テンプレートが失敗の原因かどうか。Planner のプロンプトを変えた比較をしていない。
- Critic の thinking が偽陰性を減らすかどうか。件数が少なく（7 から 4）、揺らぎと区別できない。
- dataset 系の失敗のうち、コード生成の質に由来する分。タイムアウトと未測定が混ざっている。
- Goal の偏り。同じ種類の問い（1 件の測定、比較、集計）が多く、地図以外の分析は含まない。
- 実行は 1 回ずつの 5 周で、LLM の揺らぎがある。

## サービス側で見つかった罠（今回は変更していない）

- Valhalla の `/route` を GET の `json=` で呼ぶとき、空白を含む JSON を `urlencode` に渡す（`json.dumps` の既定）と HTTP 400 になった。区切りの空白を詰めた JSON は成功した。`call_service` が空白を `+` にエンコードすることが原因ではないかと考えているが、確かめたのは、空白あり・なしの結果の違いだけである。
- Critic が出力形式を守らないと `ValueError` が Goal の実行全体を止める。

## 再現

```bash
# 前提検査: 全 Goal の oracle を 1 本ずつ実行する
.venv/bin/python -m bench.check_oracles

GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.run_goals --out ~/tmp/geo-voyager-bench/run --repeat 5             # 条件 A
  .venv/bin/python -m bench.run_goals --out ~/tmp/geo-voyager-bench/run_b --repeat 5 --critic-thinking   # 条件 B
.venv/bin/python -m bench.report ~/tmp/geo-voyager-bench/run/results.jsonl
```

生の記録と集計は [evidence/failure_categories/](evidence/failure_categories/) にある。

- `condition_a_critic_default.jsonl`、`condition_b_critic_thinking.jsonl`: 実行ごとの記録（1 行 1 実行）
- `discarded_gateway_oom.jsonl`: 破棄した行
- `report_a.json`、`report_b.json`、`report_ab.json`: `bench.report` の出力（再判定後）
