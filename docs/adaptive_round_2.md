# 適応ループで 22 Goal を 2 周目

2026-10-10。[adaptive_round_1.md](adaptive_round_1.md) の 1 周目のあとに、次を直した版（コミット `004b33e`）で、同じ 22 Goal を 1 回ずつ流した。

- 出力の契約（測定に何を測ったかを含める）とローカル集計の選び方の指示
- Valhalla の契約と、`call_service` の空白の `%20`
- Taginfo の `tag/stats` の契約
- `対象:` の検査の強化（タグ、タグのキーや値、複数の対象、集合を拒否）
- step の Critic への、比較・選択・集計の答えそのものの要求

記録は [evidence/adaptive_all2/](evidence/adaptive_all2/)。集計は `bench/adaptive_summary.py`（DONE で終わったものだけを正解に数える）。

## 結果

| | 1 周目 | 2 周目 |
|---|---|---|
| DONE で終わり、正解 | 12 / 22 | 15 / 22 |
| DONE で終わったが誤答 | 0 | 0 |
| 途中で停止 | 10 | 7（planner_failure 5、repeated_intent 1、final_critic_failed 1） |

どちらも 1 周ずつで、Goal ごとの揺らぎを測っていない。12 と 15 の差は、この数では偶然と区別できない。

### Goal ごとの変化

| Goal | 1 周目 | 2 周目 | 変化の理由（記録から読めること） |
|---|---|---|---|
| `route_auto_km`、`route_walk_minutes` | 停止 | 正解 | Valhalla の契約と `%20`。1 step で正解 |
| `tag_ramen_vs_sushi` | 停止 | 正解 | `対象: ramen` を拒否、`tag/stats` で件数、最終 Critic の拒否のあと比較の step |
| `cafe_shibuya_vs_shinjuku` | 停止 | 正解 | 1 周目は上限の 8 step 目で比較が出た。2 周目は 6 step で DONE |
| `nom_setagaya_south` | 停止 | 正解 | 1 周目は最終 Critic が 3 回拒否。2 周目は 1 step で通った（変更との関係は分からない） |
| `tag_sushi_count` | 正解 | 停止 | step 1 で正しい 24,089 を得たが、最終 Critic が「OSM 全体の sushi 関連の件数」と解釈して 3 回拒否した。最終 Critic の過剰な厳しさ |
| `stations_northmost` | 正解 | 停止 | 1 周目は 1 step。2 周目は Planner が駅の一覧（CSV の文字列）を取ってから最大を選ぶ 2 段に分け、ローカル集計が誤った駅や null を返して止まった。`対象: 駅データ` が検査を通った（Goal に「駅データ」という語がある） |

## 停止した 7 件

| Goal | 停止 | 何が起きたか |
|---|---|---|
| `sparql_min_relation_ward` | planner_failure | Planner が `対象: 東京23区` を 2 回書き、2 回とも拒否された。step は正しい杉並区（1543055）を出したが、step の Critic が棄却した（最小の ID の区を選んだという説明が無い、という理由） |
| `sparql_four_char_wards` | planner_failure | `対象: []`、`対象: 東京23区`、外部リソース無しの初手で 3 回の計画の失敗 |
| `ward_pop_max` | planner_failure | `利用データセット: id` の 1 行書きで 2 回。世田谷区の人口の step は `{"error": "世田谷区が見つかりません"}` |
| `ward_pop_total` | planner_failure | `対象: 東京23区`、`対象:` 2 行、`利用データセット` の 1 行書きで 3 回 |
| `stations_northmost` | planner_failure | 上の表 |
| `cafe_vs_restaurant_shibuya` | repeated_intent | 2 つの件数は 1 つの step で `tag` つきで出たが、比較の step が 3 回失敗（Candidate の形式、`cafe count missing or ambiguous`、`KeyError: 'osm'`） |
| `tag_sushi_count` | final_critic_failed | 上の表 |

## 分かったこと

- 停止の最大の原因が、計画の失敗（5 件）に移った。中身は、拒否された `対象: 東京23区` を Planner が書き直さずに繰り返すことと、`利用データセット` の 1 行書きの形式エラーである。拒否の理由は履歴で Planner に見えているが、同じ誤りを繰り返し、3 回の上限で止まる。
- `対象:` の検査を強めたことで、集合を対象にした Intent は通らなくなった。これらの Goal は 1 周目も正解していなかったので、正解を減らしてはいないが、止まり方が早くなった。
- 最終 Critic が正しい答えを拒否する例が、1 周目の `nom_setagaya_south` に続いて `tag_sushi_count` で出た。最終 Critic は、正解を落とす側にも働く。
- 新しく `stations_northmost` が落ちた。`対象: 駅データ` のように、Goal に含まれる語なら Dataset の名前でも `対象:` の検査を通る。
