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
