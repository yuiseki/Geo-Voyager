# 計画の失敗と DONE 後の最終判定の失敗から、再計画に戻る

2026-10-09 に、観測に基づく経路（[observation_driven_planning.md](observation_driven_planning.md)）へ、2 つの回復を足した。

- Planner の出力が使えなかった場合（形式や契約の違反）を、Goal の終了にせず、履歴に `PlannerFailure(reason)` として追記し、次の `Planner.next()` で再計画する。
- Planner が `DONE` を返したあとの、Goal 全体の最終 Critic が失敗した場合を、履歴に `FinalCriticFailure(reason)` として追記し、Goal 未達として `Planner.next()` に戻る。

`Planner.next()` は、1 回の呼び出しで 1 回のモデル呼び出しのままである。`IntentExecutor`、runtime repair、semantic repair は変更していない。

## 変更点

- `geo_voyager/goal_history.py`: `GoalHistory` が、実行した step に加えて 2 種類の失敗を、起きた順に追記する。失敗は step ではないので、`len()` と step 番号には数えない。`events` が全体、`entries` が step だけ、`planner_failures()` と `final_critic_failures()` が種類別。
- `Planner.next()`: 使えない応答は `PlannerRejected`（`ValueError` の子クラス）として投げる。理由と、モデルが書いた応答そのものを持つ。`next()` の中で再試行はしない。プロンプトには、履歴にある失敗の理由と自分の応答が見え、「計画の失敗があれば、理由が示す契約を守り同じ誤りを繰り返さない。対象が複数あるときは対象ごとに Intent を分ける」「最終判定が未達なら、理由が示す不足を埋める Intent を返し、同じ DONE を繰り返さない」というルールを足した。
- `GoalExecutor.execute_adaptive`: 失敗を履歴に追記して、`Planner.next()` に戻る。
- 結果の `AdaptiveGoalExecution.events`: 実行した step と 2 種類の失敗が、起きた順に残る（provenance）。`bench/run_adaptive.py` の trace にも出る。

### 回復の上限と停止

| 停止理由 | 条件 | 既定 |
|---|---|---|
| `done` | `DONE` を返し、最終 Critic が成功 | |
| `planner_failure` | 計画の失敗が上限に達した、または前と同じ理由の失敗がもう一度起きた | 3 回 |
| `final_critic_failed` | DONE 後の最終 Critic の失敗が上限に達した、または前と同じ理由がもう一度出た | 3 回 |
| `max_steps` | 実行した step が上限に達した | 8 |
| `repeated_intent` | 成功済みの Intent をもう一度計画した、または失敗した同じ Intent を 2 回試した後にまた計画した | 2 回 |
| `planner_error` | 回復できない例外（空の Goal など） | |

ループの各回は、step を 1 つ実行するか、失敗を 1 つ記録するか、止まるかのどれかである。step、計画の失敗、最終 Critic の失敗は、それぞれ上限があるので、どんな失敗の組み合わせでも有限回で終わる。同じ理由の失敗が 2 回目に出たら、上限を待たずに止まる。単体テストで、延々と不正な応答を返す Planner、延々と `DONE` を返す Planner、両者が交互に出る場合が、それぞれ有限回の呼び出しで止まることを確かめた。

### 実行側の形式エラーの扱い（E2E で見つけた誤りの修正）

最初の実装は、`executor.execute` が投げた `ValueError` を、すべて計画の失敗として記録していた。E2E の記録に、`Candidate code must use a Python code fence`（コード生成の出力形式の不備）が、「計画の失敗」として履歴に入っている例があった。Planner に「あなたの計画が不正」と誤って伝える帰属の誤りである。次のように直した。

- 実行契約に反する Intent（データセットが 2 件以上、前段が無いのにローカル集計など）は、executor を呼ぶ前に、`IntentExecutor` と同じ条件で検査し、`PlannerFailure` にする。`IntentExecutor` は変更していない。
- executor の中で起きた `ValueError`（候補や判定の出力形式の不備）は、失敗した step として記録する。Planner は実行の失敗として読む。

## 評価

評価は 2 つの Goal（`cafe_shibuya_vs_shinjuku` と `tag_top3_cuisine`）だけを、実 LLM、実 Docker、実サービスで流した。まず自然な実行を 8 回、その後で、自然には起きなかった経路を確かめるための注入を 3 回行った。

| 区分 | 実行 | 停止 | step 数 | 計画の失敗 | 最終 Critic の失敗 | Goal の Critic | 所要時間 |
|---|---|---|---|---|---|---|---|
| 自然 | cafe_shibuya_vs_shinjuku | done | 5 | 0 | 0 | 成功 | 96.8 秒 |
| 自然 | tag_top3_cuisine | repeated_intent | 5 | 0 | 0 | 失敗 | 98.2 秒 |
| 自然 | cafe_shibuya_vs_shinjuku | done | 7 | 0 | 0 | 成功 | 139.6 秒 |
| 自然 | tag_top3_cuisine | repeated_intent | 5 | 0 | 0 | 失敗 | 98.2 秒 |
| 自然 | cafe_shibuya_vs_shinjuku | done | 4 | 1 | 0 | 成功 | 66.5 秒 |
| 自然 | tag_top3_cuisine | max_steps | 8 | 0 | 0 | 失敗 | 166.5 秒 |
| 自然 | cafe_shibuya_vs_shinjuku | done | 4 | 1 | 0 | 成功 | 99.3 秒 |
| 自然 | tag_top3_cuisine | done | 1 | 0 | 0 | 成功 | 19.6 秒 |
| 注入 | cafe_shibuya_vs_shinjuku（対象: 2 行の応答を注入） | done | 4 | 1 | 0 | 成功 | 92.5 秒 |
| 注入 | cafe_shibuya_vs_shinjuku（DONE を早めに注入） | done | 4 | 1 | 1 | 成功 | 71.9 秒 |
| 注入 | cafe_shibuya_vs_shinjuku（DONE を早めに注入） | done | 7 | 0 | 1 | 成功 | 172.3 秒 |

「注入」は意図的な介入である。

- 「対象: 2 行の応答を注入」は、3 回目の Planner 呼び出しの応答を、以前の実行でモデルが実際に書いた、2 つの `対象:` を持つ応答に差し替える。本物のパーサが拒否し、履歴の記録と再計画は本物である。
- 「DONE を早めに注入」は、最初の件数が出た step の後で、モデルに聞かずに `DONE` を返す。2 つの件数が要る Goal では、早すぎる DONE になる。

### 確認項目

| 確認項目 | 記録 |
|---|---|
| 複数 `対象:` の Planner failure から分割計画へ復帰できる | 注入した実行で、step 2 の後に拒否され、step 3 が対象 1 つ（渋谷区）の Intent に戻った。「DONE を早めに注入」の 1 本目では、自然に、最初の呼び出しで「`対象:` が 2 行」の拒否が起き、そこから区ごとの分割計画（ID の取得、区ごとの件数）に復帰して DONE に至った |
| premature DONE から final Critic の理由を使って探索を継続できる | 注入した 2 本とも、最終 Critic が欠けている内容（1 本目は新宿区の件数、2 本目は比較の結論）を理由に挙げ、Planner がそれに沿った step を続けた。1 本目の次の step は、まさに新宿区の件数の取得だった |
| 最終的に DONE と最終 Critic の成功に到達する | 注入した 3 本、自然な cafe の 4 本が、すべて DONE と最終 Critic の成功に到達した |
| 無限ループしない | 全 11 本が有限回で終わった。自然な `tag_top3_cuisine` の 4 本は、DONE に至らず止まったものが 3 本あり、`repeated_intent` が 2 本、`max_steps` が 1 本だった。上限と反復の検出が働いた記録である |

自然な 8 本のうち、計画の失敗が 2 本で起き、どちらも再計画で DONE に至った。1 本は `Plan must start with 調査項目:`（項目の順序の違い）、もう 1 本は、上記の帰属の誤りの例（`Candidate code must use a Python code fence`）である。
自然な 8 本で、最終 Critic の失敗は 1 回も起きなかった。この経路は、注入でしか確かめていない。

### 分かったこと、限界

- cafe の 7 回（自然 4、注入 3）は、すべて DONE と最終 Critic の成功に到達し、2 区の件数（459 と 343）も正しかった。ただし、最終 step の出力に勝者が明示されていたのは 2 回だけである。残りは、件数が別々の step にあり、比較の結論がない。最終 Critic は、全 step の出力を読んで「渋谷区の方が多い」と判断し、成功とした。私の oracle 判定（最終出力のみ）は、この暗黙の比較を認めないので、7 回中 2 回だけ一致した。
- `tag_top3_cuisine` は、自然な 4 本のうち DONE と成功に至ったのは 1 本（1 step）だった。最終 Critic の失敗を使った回復は、この Goal では確かめていない（自然には起きなかった）。
- 最終 Critic の理由は、正確でないことがある。注入の 2 本目では、「渋谷区の件数が欠落」と書いたが、実際には渋谷区の件数は出ていて、欠けていたのは比較の結論だった。Planner は、それでも続行して DONE に至った。
- Planner が `対象:` に、判明した対象の名前と違う短い名前を書くと、名前の一致で対象を解決できず、step が失敗する。実際、Nominatim が名前を `港区, 東京都, 日本` と返す実行で、Planner が `対象: 港区` と書いて失敗した。この問題には、その後、対象を stable ID で識別する形で対処した（[target_ref.md](target_ref.md)）。
- 各実行は 1 回ずつで、揺らぎは測っていない。注入した 3 本は、回復の経路を見るための意図的な介入である。
- 1 実行の所要時間は 20 秒から 172 秒（Planner の呼び出しを含む）。

## テスト

- 単体テスト: 613 件が通る。履歴の追記（失敗の種類、順序、step 番号）、`Planner.next` の拒否と履歴のプロンプト、`execute_adaptive` の回復（復帰、同じ理由の反復、上限、有限回で止まること、実行側の形式エラーの扱い、provenance）、trace、注入のテストを含む。
- focused integration: 既存の 11 件と `test_adaptive_goal` の 12 件を流した。`test_service_learning` の 2 件が、同じコードの再実行で通ったり落ちたりした（Skill の再利用の揺らぎと、コード生成の失敗）。このテストは、今回変更した部品を使っていない。
- `test_adaptive_goal`（実 LLM）は、揺らぐことがある。現在のコードで 6 回流したところ 2 回だけ通った。落ちた 4 回のうち 3 回は、「判明した対象の名前が `港区` と完全に一致する」検査で落ちたもので、Goal 自体は DONE と最終 Critic の成功に至っていた（Nominatim が名前を `港区, 東京都, 日本` と返す実行があるため）。検査を、表示名を認める形に緩めた。残る 1 回は、件数 0 を誤って答え（oracle は 22）、Critic も通した、コード生成の誤りだった。緩めたあとは 3 回連続で通った。
- 回復を入れる前のコミット（`5c40a75`）との比較として、同じ Goal（`hospital_minato`）を 4 回ずつ、DONE と oracle の一致で数えた。現在のコードが 3 回、以前のコミットも 3 回で、差はなかった。step 2（件数の取得）が最初に失敗した実行は、現在のコードで 4 回中 4 回、以前のコミットで 4 回中 2 回だったが、4 回では差と言えない。どちらにも、対象の名前の違い（`港区` と `港区, 東京都, 日本`）が見られた。
- `integration/test_burger_goal.py` は、前の変更で書き換えたまま、実行していない。

## 再現

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.run_adaptive --out ~/tmp/geo-voyager-bench/adaptive_injected \
  cafe_shibuya_vs_shinjuku:twotargets=3 cafe_shibuya_vs_shinjuku:earlydone tag_top3_cuisine
```

`:twotargets=N` は N 回目の Planner 呼び出しの応答を、2 つの `対象:` を持つ応答に差し替え、`:earlydone` は最初の件数の後で DONE を返す。
生の記録は [evidence/observation_driven_recovery/](evidence/observation_driven_recovery/) にある。

- `natural_1/`、`natural_2/`: 自然な 8 本（`results.jsonl` と、実行ごとの trace）
- `injected/`: 注入した 3 本
- `flaky_current/`、`flaky_before/`: `test_adaptive_goal` の揺らぎを見た 4 回ずつの trace（現在のコードと、回復を入れる前のコミット）
