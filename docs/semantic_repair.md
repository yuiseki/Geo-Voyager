# Critic が棄却した実行への semantic repair

2026-10-09 に、実行は成功したが Critic が失敗と判定した Candidate を、1 回だけ直す経路を追加した。
評価は新しいベンチマークを流さず、保存済みの semantic-completion の失敗 22 件を replay して行った。

## 動き

`IntentExecutor` に任意の引数 `semantic_repairer` を足した。渡さなければ何も変わらない（既定はオフ）。渡すと、次のときだけ発火する。

- 実行が成功し、かつ Critic が失敗と判定した（runtime repair で実行が通った後も含む）。実行が失敗した場合は発火しない。
- 1 つの Intent につき最大 1 回。
- 既存の `SkillCandidateRepairer`（runtime repair）とは別のクラスと別のメソッドで行う。runtime repair は呼ばれない。

流れ:

1. `SemanticRepairer.repair(...)` が、修正した Candidate を提案する。
2. 提案が `proposed` のときだけ、同じ Worker で再実行し、同じ Critic で判定し直す。
3. Critic が成功としたときだけ、元の結果を置き換え、その Candidate だけを Skill として保存する。実行が失敗した場合や Critic が再び失敗とした場合は、元の観察と判定がそのまま残る。つまり、この経路は Intent の結果を悪化させない。コストは、1 回の LLM 呼び出しと、1 回の実行と、1 回の Critic 判定である。

### semantic repair に渡すもの

Intent、対象（`intent_target`）、元の Candidate（説明とコード）、Critic が判定した現在の Observation、`critique.reason`、前段の Observation（形と値、各 1,500 文字まで）、Dataset、Service、Primitive の契約（`geo_voyager/contracts.py`）。
Primitive の契約は runtime repair が見せる文面と同じで、テストが一致を保つ。

プロンプトでは、Intent、対象、出力のキーを変えないこと、Observation や Critic の理由に出た値をコードに貼り込まないこと（hardcoded 禁止）を指示している。

### 提案の分類と保護

提案は、実行の前に次のいずれかに分ける。`proposed` 以外は実行しない。

| status | 意味 |
|---|---|
| proposed | 実行して Critic にかける |
| unchanged | 空行とコメントを除いて、元のコードと同一 |
| vibration | これまでの試行の、どれかと同一（前の版に戻った） |
| hardcoded | 新しく書いた定数が、Observation の値や Critic の理由の数字と一致した（`geo_voyager/hardcoding.py`、AST で比較） |
| invalid | LLM の出力形式が不正 |

### 出所の記録（provenance）

`ExecutionAttempt` に、`route`（`runtime` か `semantic`）、`critique`（その試行の観察への Critic の判定）、`trigger`（直そうとした Critic の理由）、`executed`、`note` を足した。
semantic repair の試行は、実行しなかった場合も含めて `IntentExecution.attempts` に残る。`repair_stats.intent_record` は、runtime の連鎖の統計から semantic の試行を除き、別に `semantic_repair` として要約する。

## 評価の方法

- 対象は、保存済みの 3 つの実行（前の測定の条件 A、条件 B、新方式）の、semantic-completion に分類された 33 件のうち、「実行は成功し、Critic が棄却した」22 件。残りの 11 件は、Critic が誤った答えを通したもので、発火の条件を満たさないので対象外にした。
- 各事例の保存済みの Candidate、観察、Critic の理由、前段の Observation、履歴を使って semantic repair を呼び、提案を同じ Docker sandbox とゲートウェイで再実行し、事例が記録されたときと同じ Critic の設定（条件 B の事例は thinking あり）で判定した。
- 1 事例につき 1 回だけ replay した。LLM の揺らぎは測っていない。
- Goal の最終回答でない中間のステップは、oracle で正否を判定できない。oracle の判定は、確認できた場合の補助としてだけ使う。

## 結果

### 件数（22 件）

| 分類 | 件数 | 意味 |
|---|---|---|
| rescued（救えた） | 4 | 提案を実行し、Critic が成功と判定した |
| still_failing | 3 | 実行でき出力も変わったが、Critic はまだ失敗とした |
| unchanged | 8 | コードは変わったが出力は同じ（コードが同一だったものは 0 件） |
| vibration | 1 | 前の版に戻った |
| invalid | 2 | LLM の出力形式が不正 |
| worsened（悪化） | 4 | 提案の実行が失敗した（実行エラー 4 件） |
| hardcoded（拒否） | 0 | 保護が拒否した事例はなかった |

- 悪化の 4 件は、提案の再実行が失敗したもので、上の流れのとおり元の結果は残る（結果は悪化しない）。実行エラーの内訳は、サービスの HTML エラー、`No data found` の例外、DuckDB の列の誤用の 3 件と、最後の行が `, 0` で種類を確認していない 1 件だった。
- 救えた 4 件は、条件 B の事例が 3 件、条件 A の事例が 1 件。
- 1 事例あたりの所要時間は平均 12.9 秒（LLM、実行、Critic を含む）。

### 救えた 4 件の中身

| 事例 | Critic の判定の変化 | 出力で起きたこと |
|---|---|---|
| sparql_four_char_wards.r1 のステップ 1 | 「gs:osmRelation、件数（23）、言語の明記がない」から「それらが明示されている」へ | 各行に `"osm_relation": "gs:osmRelation"`、`"count": 23`、`"language": "日本語"` を足した（固定の値の追加） |
| sparql_four_char_wards.r2 のステップ 1 | 「URI と日本語名が欠落」から「全 23 区の URI と名前が取得されている」へ | `relation_id` を捨て、`uri` と `relation_uri` に置き換えた（下流が頼る安定 ID のキーが消えた） |
| sparql_four_char_wards.r4 のステップ 1 | 「外部 ID（URI）と言語が明記されていない」から「明記されている」へ | `language` と `uri` を足した |
| sparql_four_char_wards.r5 のステップ 2 | 「回答の対象が千代田区で、一覧の 1 番目の世田谷区と一致しない」から「対象の区（世田谷区）が前段と一致」へ | 取り違えた対象を直した（本物の修正） |

3 件は、Critic が欠落を指摘した項目を、出力に足して通ったものである。出力の契約（キー）が変わっており、そのうち 1 件は元の `relation_id` を失っている。4 件目だけが、対象の選び方を直した修正である。
出力のキーが変わった事例は 4 件（救えた 3 件と、`error` キーを足しただけの still_failing 1 件）。

### oracle による確認

oracle で正否を判定できた 15 件のうち、「正しい」に変わった事例は 0 件だった（15 件とも、修正前も後も不正解）。救えた 4 件も、oracle の判定は変わっていない。ただし、これらは Goal の最終回答でない中間のステップである。oracle は最終回答でしか判定できないので、「救済が誤り」とは言えず、「救済を oracle では確認できなかった」までが言えることである。

### unchanged の 8 件

Valhalla の距離が 0 のままの事例が 4 件、Taginfo の事例が 3 件（空の配列が出る 2 件と、`count` と `count_all` の取り違え 1 件）、`sparql_four_char_wards` が 1 件。LLM は Critic の理由を読んでコードを書き換えるが、出力は変わらなかった。原因（例えば Valhalla の GET の `+` の問題）が Critic の理由から読み取れないためと考えられるが、確かめていない。

## 分かったこと、限界

- この replay の範囲では、semantic repair は 22 件中 4 件を Critic の基準で救えたが、oracle で確認できた救済は 0 件で、救えた 3 件は出力の契約を変えた。Critic の指摘を満たす項目を足すだけで通る事例があり、Critic の基準に合わせて出力を整えているだけで、答えを良くしているとは限らない。
- hardcoded の保護は、拒否した事例が 0 件だった。保護が見るのは、Observation の値と、Critic の理由の中の数字だけである。救えた事例の `"gs:osmRelation"` のような、Critic の理由の文章から取った文字列は検出しない。理由の文章に出る語を全て拒否すると、「欠けたキーを足す」正当な修正も止まるので、そうしていない。
- 出力の契約（キー）を守ることは、プロンプトの指示だけで、実行時の検査ではない。キーの変化は、replay の指標としてだけ数えた。
- 1 事例につき 1 回の replay で、LLM の揺らぎは測っていない。22 件のうち 18 件は、条件 A と B の古い方式（「一覧の N 番目」）の実行の事例である。
- 全体の正解率への影響は、end-to-end では測っていない。

### 次の候補（実装していない）

出力のキーを変えた提案を、実行時に拒否する（キーの追加も削除も不可にする）検査を足せば、上の救済のうち、キーを足した 3 件は通らず、対象の選び方を直した 1 件だけが残る。決定的で安価な検査だが、4 件だけでは効果を主張できず、試していない。

## テスト

- 単体テスト: 526 件が通る。新しい経路には、発火しない条件、最大 1 回、元の結果を残す条件、提案を実行しない 4 つの場合、provenance、保存を成功した提案だけにすること、のテストがある。
- focused integration: `test_critic_llm`、`test_service_primitive`、`test_execution_failure`、`test_fetch_gateway`、`test_service_learning` の 11 件が通る。semantic repair を有効にした end-to-end の integration テストは書いていない（評価は replay のみ）。

## 使い方と再現

```python
executor = IntentExecutor(retriever, selector, worker, generator, critic, library, repairer,
                          semantic_repairer=SemanticRepairer(llm))
```

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.replay_semantic --out ~/tmp/geo-voyager-bench/semantic_replay \
  --results RUN_A/results.jsonl RUN_B/results.jsonl RUN_NEW/results.jsonl
.venv/bin/python -m bench.semantic_replay_stats ~/tmp/geo-voyager-bench/semantic_replay/replay.jsonl   # 再集計
```

生の記録は [evidence/semantic_repair/](evidence/semantic_repair/) にある。

- `replay_raw.jsonl`: 事例ごとの記録（Critic の前後の理由、前後の出力、実行エラーを含む）
- `replay_refreshed.json`: 出力のキーの変化を、list の出力まで見て再計算した集計と事例
- `cases.json`: 事例の件数と、除外した件数
