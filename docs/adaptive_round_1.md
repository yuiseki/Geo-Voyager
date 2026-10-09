# 適応ループで 22 Goal を 1 周

2026-10-10。観察駆動の適応ループ（`GoalExecutor.execute_adaptive`）に、TargetRef、Planner と Generator の契約、最終 Critic、決定的な検査を積んだ版で、ベンチマークの 22 Goal を 1 回ずつ流した。それまでの変更は、2 つの Goal の E2E と保存済み記録の再生でしか確かめていなかったため。

- コード: `b8fa975`（1〜19 本目）。20 本目の `ward_pop_total` で、sandbox の 30 秒の timeout が例外のまま外へ出て、実行全体が止まった。Worker が timeout をその Candidate の失敗として返すように直し（`worker.py`、単体テスト 813 件）、残りの 3 本を流し直した。この修正は timeout のときだけ挙動を変えるので、1〜19 本目の結果には影響しない。止まった 20 本目の途中の記録は捨てた。
- 1 周だけなので、揺らぎは測っていない。以前の一括計画の方式の測定（[identity_references.md](identity_references.md)、21 Goal × 4 周で 50.6%）とは、方式も時期も違い、対照の比較ではない。
- 記録: [evidence/adaptive_all1/](evidence/adaptive_all1/)。集計は `python -m bench.adaptive_summary results.jsonl`。

## 結果

| 結果 | 件数 |
|---|---|
| 正解 | 15 / 22 |
| 誤答を最終 Critic が通した | 0 |
| 途中で停止（max_steps 2、repeated_intent 3、final_critic_failed 1、planner_failure 1） | 7 |

不正解の 7 件は、すべて DONE に至らず止まった。誤答を正解として返した実行は無かった。以前の方式の失敗の多くは、全 step が通って答えだけが誤る型だった（[critic_accepted_wrong.md](critic_accepted_wrong.md)）。

### 検査の発火

| 検査 | 回数 | 備考 |
|---|---|---|
| 最終 Critic の失敗 | 13 | 正解した 6 本でも出ていて、早すぎる DONE を拒否したあと回復した |
| Planner の拒否: `対象:` が実体でない | 3 | `対象: 目的地` など |
| Planner の拒否: 形式 | 4 | `ward_pop_max`、`ward_pop_total` の `利用データセット: id` の 1 行書き（既知の未修正の形式） |
| Planner の拒否: API の詳細、その他 | 2 | |
| Generator の契約による拒否 | 1 | |
| runtime repair の拒否 | 2 | `cafe_shibuya_vs_shinjuku` |

## 不正解の 7 件の分類

| 型 | Goal | 何が起きたか |
|---|---|---|
| ローカル集計が前段の正しい Observation を選べない | `cafe_vs_restaurant_shibuya` | cafe の件数と restaurant の件数の Observation が、どちらも `{"name": "渋谷区", "relation_id": "1759477", "count": ...}` で、何を数えたか（タグ）が出力に無い。位置で選ぶことは禁じたので、比較のコードは区別できず、5 回続けて「cafe の件数が見つからない」で失敗し、8 step で止まった |
| 同上 | `cafe_shibuya_vs_shinjuku` | 名前で探すと、件数を持たない ID の Observation に当たり、`KeyError: 'count'` が 2 回。8 step 目で正しい比較が出たが、上限に達して止まった |
| サービス契約（Valhalla） | `route_auto_km`、`route_walk_minutes` | 応答のキーの誤り（`routes` は無い）、`costing` を渡せず HTTP 400 が 5 回、0.0 km |
| サービス契約（Taginfo の値ごとの件数） | `tag_ramen_vs_sushi` | ramen を求めて pizza を返す、ramen の件数を 1 と返して step の Critic が通す、sushi で失敗が続く |
| step の Critic の誤った棄却 | `sparql_four_char_wards` | step 2 は正しい `{"count": 3}` を出したが、step の Critic が自分で 4 文字の区を数え直して（8 区と誤って）棄却した。最終 Critic は、棄却された step の出力を見ないので、答えが無いとして 2 回失敗にした |
| Planner | `ward_pop_total` | 人口を Overpass に求めて null、Dataset の step は timeout、その後 `利用データセット` の 1 行書きで形式エラーが 2 回続いて止まった。`対象: 東京23区` は Goal にある語なので、`対象:` の検査を通っている（集合であって実体ではない） |

## 分かったこと

- 新しい検査は、この 1 周では、誤答を返すことを止め、失敗を見える形に変えた。正解率 15/22 は以前の方式の数字より高いが、方式と時期が違い、1 周なので、改善とは言えない。
- `cafe_vs_restaurant_shibuya` の失敗は、今回の変更が生んだものである。位置で選ぶことを禁じた一方で、件数の出力に「何を数えたか」が無いので、同じ区の 2 つの件数を区別する手段が無い。以前の方式では、位置で選んで正解していた。
- 7 件のうち 3 件はサービス契約（Valhalla 2、Taginfo 1）で、これまでのベンチマークでも同じ系統が弱かった。
