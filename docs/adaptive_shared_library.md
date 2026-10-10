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

## 検索の embedding の切り替えと、書き直しの指摘を足した 4 周目（2026-10-10）

3 周目の生成のプロンプトを読み直すと、地物を数える step で見せた Skill は、ほとんどが人口の Seed Skill だった。既にあった数える Skill は見せていなかった。`granite-embedding` は、「港区内の amenity=hospital の OSM 地物数」に対して人口の Skill を最上位に置いた（日本語の問い合わせと英語の説明文が混ざることが効いている、という仮説で、確かめていない）。

- 保存済みの各周の step で、その時点の Library に同じ働きの Skill があるとき、それが上位 4 件に入るかを両方のモデルで測った（`bench/retrieval_recall.py`、[evidence/adaptive_shared4/retrieval_recall_all_rounds.txt](evidence/adaptive_shared4/retrieval_recall_all_rounds.txt)）。数える Skill は、3 周目の記録で granite 4 / 10、embeddinggemma 9 / 10。relation ID の Skill は両方ほぼ全部。
- お嬢様の判断で、検索の embedding を常駐の `embeddinggemma`（NodePort 30194）に切り替えた（環境変数 `GEO_VOYAGER_EMBEDDING_BASE_URL=http://localhost:30194`、`GEO_VOYAGER_EMBEDDING_MODEL=embeddinggemma`）。
- 書き直しの指摘（`rewritten_skills`、`SkillCandidateGenerator._reuse_once`）: 生成コードが、見せた Skill のサービス呼び出し（サービスと API のパス）をすべて自分で書いていて、その Skill を呼んでいなければ、Skill の名前と呼び出しを示して 1 回だけ書き直させる。2 回目は受け入れる（見せた Skill に条件が書き込まれていて合わないこともあるため）。3 周目の生成 55 回に当てると 20 回が該当した。

4 周目（`200b43f`、[evidence/adaptive_shared4/](evidence/adaptive_shared4/)）:

| | 1 周目 | 2 周目 | 3 周目 | 4 周目 |
|---|---|---|---|---|
| 変えたこと | | ハーネスの説明 | 場所の名前、呼ぶだけの関数 | embeddinggemma、書き直しの指摘 |
| DONE で終わり、正解（今の judge） | 16 | 17 | 17 | 17 |
| 学習した Skill | 31 | 29 | 29 | 27 |
| Library の名前の数（Seed 6 を含む） | 35 | 35 | 34 | 31 |
| 保存済みの Skill を呼んだ回数 | 7 | 12 | 6 | 10 |
| うち、前の Goal で学習した Skill | 6 | 10 | 3 | 8 |
| 名前に区の名前を入れた Skill | 4 | 8 | 0 | 0 |

- 書き直しの指摘は 17 回出た。relation ID を調べる Skill は、`get_osm_relation_id` が 5 つの Goal で呼ばれた。relation ID の Skill は 4 個（前の周は 5〜7 個）。
- Seed の `count_station_records` と `northernmost_station` が呼ばれた。
- 数える Skill は、まだタグごとに別の関数（`count_amenity_cafe`、`count_amenity_hospital`、`count_tourism_hotel`、`count_cuisine_ramen` など）で、どれもタグを関数の中に書き込み、タグの引数を持たない。そのため、別のタグの Goal は呼べず、新しく書く。同じタグの別の区（`cafe_shibuya_vs_shinjuku` の新宿区）では `count_amenity_cafe` が呼ばれた。
- 正解の数は 4 周とも 16〜17 で変わらない。どれも 1 周ずつで、揺らぎは測っていない。

次の候補: Intent の条件（タグの key と value など）が、関数の引数の既定値ではなく、関数の本体に文字列として書き込まれていたら、作り直させる決定的な検査。これで数える Skill がタグの引数を持てば、別のタグの Goal から呼べるようになる見込み（確かめていない）。

## サービスの Seed Skill を与えた 5 周目（2026-10-10）

それまでの Seed は Dataset（人口、駅）を読む 6 つだけで、サービスを使う操作（relation ID を調べる、区域の地物を数える、タグの使用数、経路）は、モデルが空から書いていた。Voyager は、人が書いた引数つきの基本操作（`mineBlock(bot, name, count)` など）を最初から与えている。それに倣い、サービスの基本操作を引数つきの Seed Skill として 4 つ書いた（`657b3e2`）: `get_relation_id(intent_target)`、`count_tag_in_area(intent_target, key, value)`、`tag_usage_count(key, value)`、`route_summary(origin_lat, origin_lon, destination_lat, destination_lon, costing="auto")`。実サービスで oracle と一致することを確かめた（港区 1761717、渋谷区の amenity=cafe 459、cuisine=ramen 8,213、自動車 4.547 km、徒歩約 48.4 分。`integration/test_skill_linking.py`）。記録は [evidence/adaptive_shared5/](evidence/adaptive_shared5/)。

| | 4 周目 | 5 周目（サービスの Seed） |
|---|---|---|
| DONE で終わり、正解 | 17 / 22 | 16 / 22 |
| 学習した Skill | 27 | 24 |
| 保存済みの Skill を呼んだ回数 | 10 | 23 |
| うち Seed | 2 | 12 |
| うち、前の Goal で学習した Skill | 8 | 10 |

- 呼び出しは 2 倍以上に増えた。`get_relation_id`、`tag_usage_count`、`route_summary` の Seed が、それぞれの Goal で呼ばれた。経路の 2 本は、`route_summary` を呼ぶ関数を書いた。
- 新しく見えた問題: モデルが Seed と同じ名前の関数 `count_tag_in_area` を、別の中身で書き直した。保存は同じ名前の新しい版になり、Seed（版 1）の上に版 2（`key="amenity", value="cafe"` の既定値つき、`intent_target["id_value"]` が無いと動かない）と版 3（`key="cuisine", value="ramen"`）が積まれた。以後の Goal に見せられるのは版 3 になる。原因の見立て: 実行環境が呼ぶ関数は、実行時の値以外の引数に既定値が要る。Seed の `count_tag_in_area` は `key` と `value` に既定値が無いので、そのままでは呼ばれる関数になれない。モデルは、それを呼ぶ包みの関数を書く代わりに、同じ名前で既定値つきに書き直した。
- 数える関数は、`count_cafe_in_area(intent_target, key="amenity", value="cafe")` のように、条件を既定値つきの引数で受ける形になった。ただし中で Seed を呼ばず、自前で Overpass に問い合わせるものもある。
- `count_libraries_in_setaagaya` は、区名の綴りの誤りで場所の名前の検査をすり抜けた。
- 正解は 16 / 22 で、4 周目と同じ範囲。止まったのは `hotel_taito`（計画の失敗）と、以前から止まる GeoSPARQL、人口、最北の駅の Goal。

## モデルを Qwen3.8-27B に替えた 6 周目（2026-10-10）

llama.cpp のモデル（`gvt-llm`）が、Qwen3.6-35B-A3B（MoE、活性 3B）から Qwen3.8-27B（dense、Q4_K_S、`n_ctx` 8192）に替わった。コードは 5 周目と同じ（`a5c2c5b`）。モデルの効果だけを見る周。記録は [evidence/adaptive_q38_r6/](evidence/adaptive_q38_r6/)。

- 速さ: 生成は約 35 トークン/秒、プロンプトの読み込みは約 600 トークン/秒。Generator の 1 回は約 50 秒。1 周は 80 分（前のモデルは 30〜40 分）。
- コンテキストの超過（8192）による失敗は、ログに 0 件。

途中で見つかった環境の問題: データセット系の 4 Goal（人口 2、駅 2）は、データの取得が `502 Bad Gateway` で失敗した。gateway は起動時に Hugging Face の署名付き CDN URL を一度だけ解決して使っていた。その URL の有効期限は 1 時間で、80 分かかる周の終わりにあるデータセット系の Goal は、期限切れの URL を読みに行った（前のモデルの周は 1 時間以内に終わっていたので出なかった）。gateway を、Hub の `resolve/` のリダイレクトを毎回たどる形に直した（`5e37c51`。たどるのは https の Hub から https の Hub の配下への転送だけで、他のリダイレクトは今まで通り拒む）。直した gateway で `stations_count` を 1 回流し、正解で止まった。6 周目のデータセット系の 4 Goal は、この理由で測れていない。

| | 5 周目（前のモデル） | 6 周目（Qwen3.8-27B） |
|---|---|---|
| DONE で終わり、正解 | 16 / 22 | 17 / 22 |
| データセット系を除く 18 Goal で正解 | 15 / 18 | 17 / 18 |
| 学習した Skill | 24 | 23 |
| 保存済みの Skill を呼んだ回数 | 23 | 50 |
| うち Seed | 12 | 31 |
| うち、前の Goal で学習した Skill | 10 | 14 |
| Seed の版が増えた（同じ名前で書き直された）数 | 2 | 0 |

- 以前から止まっていた GeoSPARQL の 3 Goal が、すべて正解になった。
- Seed の `count_tag_in_area` は、書き直されずに 10 回呼ばれた。`get_relation_id` は 13 回、`route_summary` は 7 回。
- 合成をモデルが書いた: `count_tag_in_area_for_target` は、学習した `check_area_exists_for_target` と Seed の `count_tag_in_area` を呼ぶ。
- タグごとの数える関数は `count_amenity_library_in_area` の 1 個だけになった（5 周目までは Goal ごとにあった）。
- 残った書き直し: モデルが学習した Skill を、同じ名前で劣化させて書き直した例が 1 つある。`count_tag_in_area_with_area_check` の版 1 は `(intent_target, key="amenity", value="cafe")` を受け取るが、版 2 は `previous_observations[0]` を読み、`tourism=hotel` を中に書き込んだ。
- データセット系以外で止まったのは `cafe_shibuya_vs_shinjuku` だけ。両区の件数（459、343）までは得たが、比べる step（対象なし）のコードが、渡されない `intent_target` で前段の Observation を絞り込もうとして None で落ちた（3 回）。この形の失敗は 1〜5 周目には無かった。渡されない実行時の値を読む関数を拒む決定的な検査を足した（`1d374bc`。1〜6 周目に保存された Skill 163 個に当てると 2 個が該当し、どちらも本当の誤り）。7 周目には入っていない。

見立て（1 周だけの観測で、揺らぎは測っていない）: dense の 27B は、見せた Skill を呼んで合成する力が前のモデルより強い。5 周目に見えた Seed の書き直しは、主にモデルの性質だった可能性が高い。

## Seed の保護と、同じ名前の書き直しの指摘を足した 7 周目（2026-10-10）

コードは `eebf71a`（Seed の保護、同じ名前の書き直しの指摘）に、gateway の修正 `5e37c51` を足したもの。記録は [evidence/adaptive_q38_r7/](evidence/adaptive_q38_r7/)。

- Seed の保護: Library の Seed（`seed` の印のある名前）は版を増やさない。同じ名前の別の中身は保存しない。
- 同じ名前の書き直しの指摘: 見せた Skill と同じ名前の関数を別の中身で書いたら、「別の名前の関数を書き、その中から呼ぶ」と 1 回だけ書き直させる。

| | 6 周目 | 7 周目 |
|---|---|---|
| DONE で終わり、正解 | 17 / 22 | 21 / 22 |
| データセット系を除く 18 Goal で正解 | 17 / 18 | 17 / 18 |
| データセット系の 4 Goal で正解 | 測れていない（502） | 4 / 4 |
| 1 周の時間 | 80 分 | 57 分 |
| 学習した Skill | 23 | 25 |
| 保存済みの Skill を呼んだ回数 | 50 | 44 |
| うち Seed | 31 | 28 |
| うち、前の Goal で学習した Skill | 14 | 16 |
| 版が 2 以上になった名前 | 2（モデルが学習した Skill） | 0 |

- 正解の増え方（17 から 21）は、ほぼ全部が gateway の修正による。データセット系を除く 18 Goal では、6 周目と同じ 17 / 18。Seed の保護と同じ名前の指摘が正解に効いたかは、この比較では見えない。
- 同じ名前の指摘は 4 回出た（`get_ward_label_and_relation_id` に 3 回、`verify_area_and_count_osm_features` に 1 回）。Library の 35 個の名前は、どれも版 1 のまま。
- 人口と駅の 4 Goal は、2〜3 step で正解した。1〜5 周目に止まっていたのは、少なくとも一部がデータの取得の問題だった可能性がある（確かめていない。1〜5 周目のログに 502 は無い）。
- 止まったのは `cafe_shibuya_vs_shinjuku`（6 周目と同じ Goal、別の理由）。Planner が step の出力のキー名を `cafe_count` と指定した。モデルは保存済みの `count_tag_in_area` を呼び、決まりどおり `{"name", "relation_id", "tag": "amenity=cafe", "count": 343}` を出した。step の Critic は、キー名が `count` で `cafe_count` でないことだけを理由に、両区の step を失敗とした。失敗した step の Observation は後の step に渡らないので、比べる step は件数を見つけられず、5 回とも落ちた。Planner の指定と、Generator に教えている出力の決まりとが食い違っている。

## 7 周目と同じ設定の 8 周目（揺らぎを見る、2026-10-11）

コードは 7 周目と同じ（`5e37c51` の worktree から実行）。記録は [evidence/adaptive_q38_r8/](evidence/adaptive_q38_r8/)。

| | 7 周目 | 8 周目（同じ設定） |
|---|---|---|
| DONE で終わり、正解 | 21 / 22 | 21 / 22 |
| DONE で終わったが誤答 | 0 | 1（`ward_pop_total`） |
| 途中で停止 | 1（`cafe_shibuya_vs_shinjuku`） | 0 |
| 1 周の時間 | 57 分 | 58 分 |
| 学習した Skill | 25 | 27 |
| 保存済みの Skill を呼んだ回数 | 44 | 50 |
| うち Seed | 28 | 31 |
| うち、前の Goal で学習した Skill | 16 | 18 |
| 版が 2 以上になった名前 | 0 | 0 |

- 正解の数は同じ 21 だが、外れた Goal は違う。7 周目に止まった `cafe_shibuya_vs_shinjuku` は 8 周目に正解し、7 周目に正解した `ward_pop_total` は 8 周目に誤答した。1 周ごとに、どの Goal が外れるかが動く。
- `ward_pop_total` の誤答: Planner は人口の step に Dataset `yuiseki/jp-admin-2026-09` を指定したが、生成されたコードは Dataset を読まず、Overpass で各区の OSM の `population` タグを集めた（API のパスを変数に入れていたので、書き直しの検査はこの呼び出しを見なかった）。合計 9,557,918 は oracle の 9,733,276 と違う。Critic は合計が出力されていることを見て受け入れた。
- 呼び出しの多さ（44〜50 回、Seed 28〜31 回）と、版の上書きが無いことは、6〜8 周目で安定している。

## 9 周目に入れた変更（2026-10-11）

6〜8 周目で見えた失敗に、それぞれ決定的な検査か規則を足した。

- 渡されない実行時の値を読む関数を拒む（`1d374bc`、6 周目の `cafe_shibuya_vs_shinjuku`）。
- Intent が宣言していないサービスを呼ぶ関数を拒む（`478ce13`、8 周目の `ward_pop_total`）。API のパスが変数でも、サービスの id で見る。1〜8 周目に保存された Skill 215 個に当てると 4 個が該当した。この誤答 1 つと、前段の出力を集計するだけの step で、サービスをもう一度呼んでいたもの 3 つ。
- Planner（step ごとの経路だけ）に、測定の出力のキーは件数なら `count`、条件なら `tag` にし、`cafe_count` のように条件をキー名に入れないよう書いた（`62477a7`、7 周目の `cafe_shibuya_vs_shinjuku`）。最初に全体を計画する経路のプロンプトは golden で固定しているので変えていない。
- step の Critic に（`07fc407`）、Intent が書いたキー名ではなく、値と対象と条件で判定するよう書いた。過去 7 周の記録で、出力はあったのに却下された step 44 個を判定し直した（`bench/replay_rejected_steps.py`、[evidence/critic_key_names/](evidence/critic_key_names/)）。例を挙げない言い方（規則 1）では 44 個のうち 13 個が成功に変わった。しかし `cafe_count` の例は直らなかった。例を名指しした言い方（規則 2、採用）では 17 個が成功に変わり、どれも oracle と一致する正しい値だった。誤った出力は、規則 2 でも却下のままだった。例えば ramen を求められて cafe を数えたもの、世田谷区のはずが京都の結果だったもの、人口がすべて null のものがある。規則を足さないで判定し直しても、44 個のうち 2 個が成功に変わる。Critic の判定はもともと揺れる。
