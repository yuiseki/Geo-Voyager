
## 場所の名前と、呼ぶだけの関数の検査を足した後の 3 周目（2026-10-10）

judge を直し（勝者の区名を日本語、区を除いた形、ローマ字で照合）、2 つの検査を足した（`9d8b307`）。関数名に場所の名前（23 区のローマ字、今回の対象の名前の英字）が入っていたら作り直させる（`geo_voyager/place_names.py`）。本体が保存済みの Skill を 1 回呼んで返すだけの関数は、別の Skill として保存しない。記録は [evidence/adaptive_shared3/](evidence/adaptive_shared3/)。

正解の数は、今の judge で判定し直したもの。

| | 1 周目 | 2 周目（ハーネスの説明） | 3 周目（場所の名前、呼ぶだけの関数） |
|---|---|---|---|
| DONE で終わり、正解 | 16 / 22 | 17 / 22 | 17 / 22 |
| 学習した Skill | 31 | 29 | 29 |
| 保存済みの Skill を呼んだ回数 | 7 | 12 | 6 |
| うち、前の Goal で学習した Skill | 6 | 10 | 3 |
| 名前に区の名前を入れた Skill | 4 | 8 | 0 |

- 名前に区の名前を入れた Skill は 0 になった（検査が 3 回作り直させた）。
- しかし、同じ働きの Skill は、名前を一般的にしたまま増え続けた。relation ID を調べる Skill が 5 個（`get_osm_relation_id`、`get_relation_id`、`get_relation_id_for_target`、`get_osm_relation_id_for_target`、`get_osm_relation_id_via_nominatim`）、地物を数える Skill が 6 個（`count_cafe_in_target`、`count_ramen_in_target`、`count_hospitals_in_area`、`count_tag_in_target`、`count_tag_in_area`、`count_restaurants_in_target`）。`count_tag_in_area` や `count_tag_in_target` のように汎用な名前と引数の Skill ができても、後の Goal はそれを呼ばずに書いた。
- 再利用の回数は 2 周目の 12 から 6 に減った。1 周ずつなので、この差が検査の影響か揺らぎかは分からない。
- 名前の付け方は検査で直せたが、モデルが既存の Skill を呼ぶかどうか（今日の確かめでは、知識として分かっていても振る舞いが伴わない）は、名前の問題とは別にある。

正解は 3 周とも 16〜17 / 22 で、変わっていない。止まる Goal も同じ（GeoSPARQL の一部、人口の 2 本、最北の駅。計画の失敗と最終 Critic の失敗）。
