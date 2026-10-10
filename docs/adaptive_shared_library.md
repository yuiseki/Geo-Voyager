# Skill library を Goal をまたいで持ち越した 1 周

2026-10-10。名前付き関数の Skill library（[skill_library.md](skill_library.md)）で、22 Goal を 1 回ずつ、1 つの Library を Goal から Goal へ持ち越して流した（`bench/run_adaptive.py --library`。最初はリポジトリの 6 つの Seed Skill）。コードは `b421ce6`。記録は [evidence/adaptive_shared1/](evidence/adaptive_shared1/)（結果、集計、終わった後の Library の全コード）。

## 結果

| | 2 周目（持ち越しなし、[adaptive_round_2.md](adaptive_round_2.md)） | 今回（持ち越しあり） |
|---|---|---|
| DONE で終わり、正解 | 15 / 22 | 16 / 22 |
| DONE で終わったが誤答 | 0 | 0 |
| 途中で停止 | 7 | 6（final_critic_failed 3、planner_failure 3） |

1 周ずつで、15 と 16 の差は偶然と区別できない。Skill の形と生成のプロンプトも 2 周目から大きく変わっているので、持ち越しの効果だけを取り出した比較でもない。

停止した 6 本は、GeoSPARQL の 3 本（`sparql_ward_count`、`sparql_min_relation_ward`、`sparql_four_char_wards`。最終 Critic の失敗が上限）と、`ward_pop_max`、`ward_pop_total`、`stations_northmost`（計画の失敗。`利用データセット` の 1 行書きの形式エラーと、`対象:` の拒否）。どれも以前から止まっていた Goal で、Skill library の変更とは別の原因である。

## Skill は Goal をまたいで使われたか

- 学習した Skill: 29 個（Seed 6 個に加えて、Library は 35 名前、37 版になった）。
- 保存済みの Skill を呼んだ step: 7 回。うち 6 回は、前の Goal で学習した Skill だった。
  - `hospital_minato` の step 1: 新しい関数 `get_ward_info` が、`cafe_shibuya` で学習した `get_osm_relation_id` を呼んだ（モデル自身の合成）。
  - `cafe_vs_restaurant_shibuya`、`nom_shibuya_relation`、`sparql_four_char_wards`、`ward_pop_max`、`ward_pop_total`: 前の Goal の Skill（`count_osm_amenity_cafe`、`get_osm_relation_id_for_shibuya`、`get_tokyo_ward_ids` など）を呼んだ。
  - `cafe_shibuya_vs_shinjuku` の step 4: 同じ Goal の step 3 で学習した `count_osm_amenity_cafe@v2` を、新宿区で呼んだ。
- Seed Skill（人口、駅）は一度も呼ばれなかった。人口の Goal は、Planner が Dataset でなく GeoSPARQL の step から始め、そこで止まった。

## 見えた問題: 同じ働きの Skill が増える

終わった後の Library には、同じ働きの Skill が名前を変えて何個もある。

- relation ID を調べる Skill が 7 個: `get_osm_relation_id`、`get_osm_relation_id_for_target`、`get_osm_relation_id_for_ward`、`get_osm_relation_id_for_setagaya`、`get_osm_relation_id_for_shibuya`、`get_shibuya_osm_relation_id`、`get_ward_info`。中身はどれも Nominatim で名前を引くもので、引数は `intent_target`。区の名前を関数名に入れたものもある（中身は区に依存しない）。
- 地物を数える Skill が 6 個: `count_osm_amenity_cafe`、`_ramen`、`_hospital`、`_hotel`、`_library`、`_restaurant`。タグが関数の中に書き込まれていて、別のタグには使えない。

原因として考えられること（仮説で、確かめていない）:

- Intent の条件（タグなど）は、Intent の文にあるだけで、実行環境から関数の引数として渡す値（`intent_target` など）に含まれていない。関数が条件を受け取る方法が無いので、モデルはタグを関数の中に書き込み、関数名にもそれを入れる。
- 検索で似た Skill が見えていても、名前が対象やタグで分かれているので、モデルは「別物」として新しく書く。

## 次の候補（決めていない）

- Intent の条件を、関数の引数として渡せるようにする（例えば、既定値つきの引数を推奨し、`count_tag_in_area(intent_target, tag="amenity=hospital")` のように、今回の値を既定値に書かせる。次の Intent はタグを変えて呼べる）。
- 関数名や中身に、対象の名前（`setagaya`、`shibuya`）を入れることを拒否する検査。
- 同じ働きの Skill を見つけてまとめる（例えば、本体が同じで名前だけ違う Skill を、保存のときに既存の名前の版として扱う）。

## ハーネスの説明を足した後の 2 周目（2026-10-10）

[harness_understanding.md](harness_understanding.md) の確かめで、モデルは「自分の関数が保存され、後の Intent から引数を変えて呼ばれること」と「条件を既定値つきの引数で受け取ること」を理解していなかった。プロンプトの先頭にその説明と実例を置き（`4e04069`）、持ち越しの 1 周を流し直した。記録は [evidence/adaptive_shared2/](evidence/adaptive_shared2/)。

| | 1 周目（`b421ce6`） | 2 周目（`4e04069`） |
|---|---|---|
| DONE で終わり、正解 | 16 / 22 | 16 / 22 |
| DONE で終わったが judge が誤答とした | 0 | 1（下記） |
| 学習した Skill | 31 | 29 |
| 保存済みの Skill を呼んだ回数 | 7 | 12 |
| うち、前の Goal で学習した Skill | 6 | 10 |
| 地物などを数える Skill のうち、条件を引数（既定値つき）で受け取るもの | 0 / 8 | 6 / 11 |
| 名前に区の名前を入れた Skill | 4 | 8 |

- 再利用は増えた。`cafe_shibuya` で学習した `get_ward_relation_id` が、`hospital_minato`、`hotel_taito`、`library_setagaya`、`cafe_vs_restaurant_shibuya`、`nom_shibuya_relation` の 5 つの Goal で呼ばれた。`tag_ramen_vs_sushi` の比較の関数は、同じ Goal で学習した 2 つの件数の Skill を呼んだ。Seed の `count_station_records` も初めて呼ばれた。
- 条件を引数で受け取る関数が増えた（`count_hotels_in_taito(intent_target, ..., key="tourism", value="hotel")` など）。ただし、そうした数える Skill が別の Goal から呼ばれた例は無い。Goal ごとに新しい数える関数を書いている。
- 名前に区の名前を入れた Skill は、かえって増えた（`count_hotels_in_taito`、`count_cafe_in_shibuya`、`get_setagaya_relation_id` など）。`get_setagaya_relation_id` は中で `get_ward_relation_id` を呼ぶだけの包みで、こうした「呼ぶだけの別名」が増えている。説明は読まれているが、関数名の付け方は変わっていない。
- judge が誤答とした 1 件（`cafe_shibuya_vs_shinjuku`）は、459 と 343 を求めて勝者を `"winner": "Shibuya"` と英語で返した。`judge_winner` は日本語の区名を探すので不一致になった。答えの中身は正しい。judge を直し（区名を日本語、区を除いた形、ローマ字のどれでも照合する。`bench/goals.py` の `WARD_ROMAJI`）、保存済みの記録を判定し直すと、この 1 件は正解になり、2 周目は 17 / 22 になる。ほかの周で DONE で終わった実行の判定は変わらない（1 周目の 22 Goal の周で、途中で止まった 1 件の最後の Observation の判定だけが変わる）。
- 1 周ずつで、揺らぎは測っていない。

次の候補（決めていない）: 名前に対象の名前（区名など）を入れた関数を、決定的な検査で作り直させる。既存の Skill を呼ぶだけの関数（本体が 1 行の呼び出し）は、保存せずに呼び出しとして扱う。
