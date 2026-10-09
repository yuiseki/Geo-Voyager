# 対象の参照を番号から identity に変える

2026-10-09 に、Planner、Generator、Critic が前段の一覧の対象を指す方法を、「一覧の N 番目」から、対象の名前と安定 ID（identity）に変えた。
旧方式と新方式を、同じ 21 Goal で比べた。repair、Critic の thinking、Selector は変更していない。

先行の測定は [failure_categories.md](failure_categories.md) にある。そこで「一覧の N 番目」を含む計画は、含まない計画より正解率が大きく低かったため、この変更を行った。

## 契約

3 つの部品が、同じ契約で対象を参照する。

- 一覧や単一の対象を出力する Intent は、各対象を `name` と安定 ID（`relation_id` など）を持つ JSON object で出力する。
- 対象を測る Intent は、Planner が任意の `対象: 名前` の行で対象の名前を指定する（`Intent.target_name`）。名前は Goal 文または前段の出力で与えられたものを使い、番号や位置では指定しない。
- Worker は、この名前を sandbox の実行時変数 `intent_target`（`{"name": ...}`）として渡す。
- 生成コードは、`previous_observations`（JSON の list でも単一の object でもよい）から、`name` が `intent_target["name"]` と完全一致する object を探し、その安定 ID を使う。一致が無い、または ID の異なる対象が複数あれば例外にする。位置で選ばない。
- Critic は、同じ規則（`geo_voyager/target_identity.py` の `resolve_target`）で対象を前段から解決し、「解決済み参照対象」として回答の名前と ID を照合させる。対象が一意に特定できないときは、その旨をプロンプトに書く。
- 名前が Goal にも前段にも無い全対象への同じ測定は、全対象を `name` と `relation_id` で識別して結果を一覧で返す 1 つの Intent にする（対象を 1 件ずつの Intent に分けない）。

撤去したもの:

- Planner の「一覧の N 番目」で 1 対象ずつ並べる指示。
- Generator の `re.search(r"([0-9]+)番", intent_text)` で番号を取り、添字を引く指示と接続例。
- Critic の「一覧の N 番目は N-1 番目の要素」と、それを解決するコード。

禁止のために位置の概念をプロンプトに書くことも避けた（言及自体が位置参照を連想させるため）。`tests/test_reference_contract.py` が、`geo_voyager/` のどこにも位置参照が残らないこと、3 つの部品が同じ語（`対象: 名前`、`intent_target`、`resolve_target`、`名前と安定ID`）を使うことを検証する。

### コミット

`930b667`（Intent と Worker と解決）、`7fbd7d0`（Planner）、`78ce287`（Generator）、`ca96e5f`（Critic）、`e6aabd1`（Planner の文言の修正）。

## 測り方

- 旧方式は、前の測定の条件 A（Critic の thinking なし）の記録をそのまま使った。新方式は、同じ Critic 設定で 21 Goal を新しく流した。
- 旧方式の記録は、新方式より数時間前に取ったものである。同じ時刻に交互に流した対照ではない。サービスや LLM の状態が時間で変わった可能性は、切り分けていない。
- 製品コード（`geo_voyager/`）は、新方式の計測の全期間で同一だった。
- 比べるのは、両側とも完全に揃った 1〜4 周目（各 84 実行、うち oracle が取れた 83 実行）。新方式は 5 周目の途中で打ち切った（費用の理由）。5 周目の 2 実行は比較に含めていない。
- 正否は、現在の judge で両側を再判定した。

## 結果

### 全体（1〜4 周目、測定済み 83 実行ずつ）

| 指標 | 旧（N 番目） | 新（identity） |
|---|---|---|
| Goal の正解 | 39 / 83（47.0%） | 42 / 83（50.6%） |
| ステップ 1〜2 での失敗 | 34 / 83（41.0%） | 23 / 83（27.7%） |
| success@0 / @1 / @2 | 63.7% / 80.6% / 83.9% | 63.0% / 79.6% / 86.1% |
| Critic 偽陽性 / 偽陰性 | 2 / 7 | 3 / 5 |

- Goal の正解率の差（+3.6 ポイント）は、有意ではない（Fisher の正確確率検定で p = 0.76）。1〜3 周目だけで比べても同じ（28/62 と 29/62、p = 1.0）。
- ステップ 1〜2 の失敗率の低下（−13.3 ポイント）も、有意ではない（p = 0.10）。
- 計画の例外で終わった実行はステップを持たないので、この率の分母にはあるが分子には入らない。例外で終わった実行を除いた率は、旧 44.7%（34/76）、新 34.8%（23/66）だった。

### failure category（失敗の件数）

| category | 旧 | 新 |
|---|---|---|
| codegen | 18 | 17 |
| semantic-completion | 11 | 6 |
| planning | 4 | 12 |
| aggregation | 3 | 3 |
| execution | 5 | 3 |
| retrieval-selection | 3 | 0 |

- retrieval-selection は 3 件から 0 件になった。一覧の先頭の区を、別の区の結果として使う誤りが消えた。
- semantic-completion は 11 件から 6 件に減った。
- planning は 4 件から 12 件に増えた（次節）。

### Planner の揺れ

| | 旧 | 新 |
|---|---|---|
| Goal ごとの異なる計画の数（平均） | 1.67 | 1.52 |
| 最頻の計画の割合（平均） | 0.78 | 0.83 |
| 計画や出力形式の例外で終わった実行 | 2 | 14 |

揺れはわずかに減った。ただし、この差の大きさは検定していない。

### 系統別の正解（1〜4 周目、分母は未測定を含む）

| 系統 | 旧 | 新 |
|---|---|---|
| geosparql | 9 / 12 | 9 / 12 |
| nominatim | 10 / 12 | 11 / 12 |
| taginfo | 6 / 12 | 8 / 12 |
| overpass | 10 / 24 | 10 / 24 |
| dataset | 3 / 16 | 4 / 16 |
| valhalla | 1 / 8 | 0 / 8 |

Goal ごとの内訳は、`evidence/identity_references/compare_rounds_1-4.json` にある。

## 新しく増えた失敗

計画や出力形式の例外が 2 件から 14 件に増えた。そのうち、計画の形式に関する例外は 1 件から 10 件になった（`Unexpected plan fields` が 5、`Plan must contain dataset and service lists` が 3、`Plan must start with 調査項目:` が 2）。残りは Generator の出力形式の例外である。
保存した応答を読むと、新しい任意の `対象:` 行が次の形で厳密なパーサを通らなかった。

- `対象:` の行が `調査項目:` より前に置かれる。
- `対象:` の行が 2 つ並ぶ（2 点間の経路など、対象が複数ある Intent）。
- 調査項目の途中に余分な行が入る。

また、対象の名前の使われ方では、61 個の Intent に名前が付いた。そのうち、名前が Goal 文に現れなかったものは 3 件で、名前でないもの（「ID 最小の区」、「各 23 区」）が書かれた。valhalla の Goal では、座標の点に「起点座標の地名」「地点 A」という名前が付けられた。
`intent_target` に起因する実行エラーは見つからなかった（変数の経路は動いている）。

### 結論に使えること

- 番号参照をやめたことで、一覧の先頭を別の対象として使う誤り（retrieval-selection）は 3 件から 0 件になった。この方向の効果は確認できた。
- Goal の正解率は、この数では改善と言えない。計画の形式エラーの増加が、効果を打ち消した可能性があるが、そうだと確かめるには、形式エラーを直した版で測る必要がある。測っていない。
- 新方式は、全対象を測る Goal（旧方式では 1 対象ずつの 23 ステップだった）を、1 つの大きな Intent にまとめる計画になる。この種の Goal は、今回の 21 Goal に含まれていない。

## 分かっていないこと

- 旧方式との差が、時刻やサービスの状態の変化によるものか。同時刻の対照は取っていない。
- 計画の形式エラーを直したときの正解率。
- 全対象を 1 つの Intent で測る Goal（旧方式では 23 ステップに分けていたもの）の成功率。

## 前回の変更に見つかった欠陥（修正していない）

repair に渡している「失敗した行の抜粋」は、元のコードの行番号で引いている。しかし Worker は、実行時変数の定義を数行、コードの先頭に足してから実行するので、traceback の行番号は元のコードより数行大きい。抜粋は、実際の失敗行からずれた行を指す。
今回は repair を変更しない方針なので直していない。この欠陥が、失敗行と履歴を渡す変更（前回の測定）の効果を弱めた可能性がある。

## テストの状況

- 単体テスト: 469 件が通る。
- integration: `test_critic_llm`、`test_service_primitive`、`test_execution_failure`、`test_fetch_gateway`、`test_service_learning` の 11 件が通る。
- `integration/test_burger_goal.py` は、旧方式の構造（23 個のステップ、学習済み Skill の再利用）を前提にしていたため、新しい契約に合わせて書き換えた。ただし、実行時間と費用の理由で、書き換え後は実行していない。通るかどうかは確かめていない。

## 再現

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.run_goals --out ~/tmp/geo-voyager-bench/identity_a --repeat 5
.venv/bin/python -m bench.compare OLD.jsonl NEW.jsonl --max-round 4
```

生の記録は [evidence/identity_references/](evidence/identity_references/) にある。

- `new_identity_references.jsonl`: 新方式の実行ごとの記録（5 周目の 2 件を含む）
- `compare_rounds_1-4.json`、`compare_rounds_1-3.json`: `bench.compare` の出力
- 旧方式の記録は、[evidence/failure_categories/condition_a_critic_default.jsonl](evidence/failure_categories/condition_a_critic_default.jsonl)
