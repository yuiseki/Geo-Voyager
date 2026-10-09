# 適応ループで 22 Goal を 1 周

2026-10-10。観察駆動の適応ループ（`GoalExecutor.execute_adaptive`）に、TargetRef、Planner と Generator の契約、最終 Critic、決定的な検査を積んだ版で、ベンチマークの 22 Goal を 1 回ずつ流した。それまでの変更は、2 つの Goal の E2E と保存済み記録の再生でしか確かめていなかったため。

- コード: `b8fa975`（1〜19 本目）。20 本目の `ward_pop_total` で、sandbox の 30 秒の timeout が例外のまま外へ出て、実行全体が止まった。Worker が timeout をその Candidate の失敗として返すように直し（`worker.py`、単体テスト 813 件）、残りの 3 本を流し直した。この修正は timeout のときだけ挙動を変えるので、1〜19 本目の結果には影響しない。止まった 20 本目の途中の記録は捨てた。
- 1 周だけなので、揺らぎは測っていない。以前の一括計画の方式の測定（[identity_references.md](identity_references.md)、21 Goal × 4 周で 50.6%）とは、方式も時期も違い、対照の比較ではない。
- 記録: [evidence/adaptive_all1/](evidence/adaptive_all1/)。集計は `python -m bench.adaptive_summary results.jsonl`。

## 結果

> 訂正（同日）: 最初の版は「正解 15 / 22」と書いた。これは harness の judge が最後の Observation を受け入れた数で、ループが DONE で終わったかを見ていなかった。DONE で終わって正解だったのは 12 本で、残る 3 本は、途中で止まったのに最後の Observation が judge の基準を満たしていた。`bench/adaptive_summary.py` を、DONE で終わったものだけを正解とするよう直した。

| 結果 | 件数 |
|---|---|
| DONE で終わり、正解 | 12 / 22 |
| DONE で終わったが誤答（最終 Critic が誤答を通した） | 0 |
| 途中で停止 | 10（max_steps 2、repeated_intent 3、final_critic_failed 3、planner_failure 2） |

途中で停止した 10 本のうち 3 本は、最後の Observation が judge の基準を満たしていた。

| Goal | 停止 | 最後の Observation と停止の理由 |
|---|---|---|
| `nom_setagaya_south` | final_critic_failed | bbox の `south` が答えの緯度そのものだが、最終 Critic は「最南端の緯度という回答値が明示されていない」と 3 回失敗にした。最終 Critic の過剰な厳しさの例 |
| `sparql_min_relation_ward` | final_critic_failed | 23 区の一覧で、最小の ID を選んでいない。最終 Critic の失敗は正しく、judge が一覧に答えが含まれるだけで受け入れている（judge が甘い） |
| `ward_pop_max` | planner_failure | 答え（世田谷区、943,664）は出ていたが、Planner が DONE を返さず、`利用データセット` の 1 行書きの形式エラーを 2 回続けて止まった |

誤答を正解として返した実行は無かった。以前の方式の失敗の多くは、全 step が通って答えだけが誤る型だった（[critic_accepted_wrong.md](critic_accepted_wrong.md)）。

### 検査の発火

| 検査 | 回数 | 備考 |
|---|---|---|
| 最終 Critic の失敗 | 13 | 正解した 6 本でも出ていて、早すぎる DONE を拒否したあと回復した |
| Planner の拒否: `対象:` が実体でない | 3 | `対象: 目的地` など |
| Planner の拒否: 形式 | 4 | `ward_pop_max`、`ward_pop_total` の `利用データセット: id` の 1 行書き（既知の未修正の形式） |
| Planner の拒否: API の詳細、その他 | 2 | |
| Generator の契約による拒否 | 1 | |
| runtime repair の拒否 | 2 | `cafe_shibuya_vs_shinjuku` |

## 正解の基準を満たさなかった 7 件の分類（最後の Observation も judge を満たさなかったもの）

| 型 | Goal | 何が起きたか |
|---|---|---|
| ローカル集計が前段の正しい Observation を選べない | `cafe_vs_restaurant_shibuya` | cafe の件数と restaurant の件数の Observation が、どちらも `{"name": "渋谷区", "relation_id": "1759477", "count": ...}` で、何を数えたか（タグ）が出力に無い。位置で選ぶことは禁じたので、比較のコードは区別できず、5 回続けて「cafe の件数が見つからない」で失敗し、8 step で止まった |
| 同上 | `cafe_shibuya_vs_shinjuku` | 名前で探すと、件数を持たない ID の Observation に当たり、`KeyError: 'count'` が 2 回。8 step 目で正しい比較が出たが、上限に達して止まった |
| サービス契約（Valhalla） | `route_auto_km`、`route_walk_minutes` | 応答のキーの誤り（`routes` は無い）、`costing` を渡せず HTTP 400 が 5 回、0.0 km |
| サービス契約（Taginfo の値ごとの件数） | `tag_ramen_vs_sushi` | ramen を求めて pizza を返す、ramen の件数を 1 と返して step の Critic が通す、sushi で失敗が続く |
| step の Critic の誤った棄却 | `sparql_four_char_wards` | step 2 は正しい `{"count": 3}` を出したが、step の Critic が自分で 4 文字の区を数え直して（8 区と誤って）棄却した。最終 Critic は、棄却された step の出力を見ないので、答えが無いとして 2 回失敗にした |
| Planner | `ward_pop_total` | 人口を Overpass に求めて null、Dataset の step は timeout、その後 `利用データセット` の 1 行書きで形式エラーが 2 回続いて止まった。`対象: 東京23区` は Goal にある語なので、`対象:` の検査を通っている（集合であって実体ではない） |

## 分かったこと

- 新しい検査は、この 1 周では、誤答を返すことを止め、失敗を見える形に変えた。DONE で終わった正解は 12/22（55%）で、以前の方式の数字（50.6%）と方式も時期も違い、1 周なので、改善とは言えない。
- 停止した 10 本のうち 2 本（`nom_setagaya_south` の最終 Critic、`ward_pop_max` の Planner の形式）は、答えが出たあとで止まっている。
- `cafe_vs_restaurant_shibuya` の失敗は、今回の変更が生んだものである。位置で選ぶことを禁じた一方で、件数の出力に「何を数えたか」が無いので、同じ区の 2 つの件数を区別する手段が無い。以前の方式では、位置で選んで正解していた。
- 7 件のうち 3 件はサービス契約（Valhalla 2、Taginfo 1）で、これまでのベンチマークでも同じ系統が弱かった。

## 追記: 出力の契約とサービス契約を直したあとの 4 本（各 1 回）

直したもの（単体テスト 818 件）。

- 出力の契約: 対象についての測定の出力に、何を測ったか（例: `"tag": "amenity=cafe"`）をキーで含めるよう Generator に指示した。ローカル集計には、同じ対象の object が複数あるとき、何を測ったかのキーと測定値のキーを持つ object を選ぶよう指示した。プロンプトだけで、決定的な検査は無い。
- Valhalla: 自前の Valhalla に問い合わせて確かめた契約を説明に書いた（POST、`application/json`、`costing` が必須、答えは `trip.summary.length`（km）と `trip.summary.time`（秒）、`routes` は無い）。`integration/test_valhalla_contract.py`（3 件が通る）。
- `call_service` が、GET のパラメータの空白を `+` でなく `%20` で送るようにした。`json.dumps` の `", "` が `+` になると、Valhalla が JSON を読めず HTTP 400 になることを、自前の Valhalla で確かめた（`+` で 400、`%20` で 200）。
- Taginfo: 1 つのタグの使用数は `/api/4/tag/stats` の `type` が `"all"` の `count` であること、`search/by_value` は部分一致（`ramen` で `noodle;ramen` も返る）なので 1 つのタグの件数には使わないことを書いた。`integration/test_taginfo_contract.py` に 2 件足した（計 5 件が通る）。plan_goal の golden prompt は変わらない（説明の先頭は変えていない）。

| Goal | 結果 | 何が起きたか |
|---|---|---|
| `route_auto_km` | DONE、正解 | 1 step で 4.547 km |
| `route_walk_minutes` | DONE、正解 | 1 step で約 48.4 分 |
| `cafe_vs_restaurant_shibuya` | 停止（repeated_intent）、最後の Observation は judge を満たす | Planner が cafe と restaurant を 1 つの step で数えた（`cafe_count` と `restaurant_count`）ので、出力の契約の変更は試されなかった。比較の step は、勝者を書かずに 2 つの件数を出し直しただけで、step の Critic はそれを通した。最終 Critic が 2 回失敗にし、Planner が同じ比較の Intent を出し直して止まった |
| `tag_ramen_vs_sushi` | 停止（repeated_intent） | ramen は `/api/4/tag/stats` で 8,213（正しい、`tag` キーつき）。sushi の step は、Planner が `対象: sushi` と書き、生成コードが前段から名前 `sushi` の object を探して `AssertionError` で失敗した。`ramen` も `sushi` も Goal の文（`cuisine=ramen`）に含まれるので、`対象:` の検査を通った |

- Valhalla の 2 本は、以前の 1 周で失敗した原因（`+` の問題と応答のキー）が消えて、1 step で正解した。1 回ずつなので、直ったとまでは言えない。
- 新しく見えた問題は 2 つ。`対象:` にタグの値（`sushi`）や集合（`東京23区`）が書かれても、Goal の文に含まれれば検査を通ること。比較を求める step で勝者を出さない出力を、step の Critic が通すこと。
