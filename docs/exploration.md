# 自由な探索

22 Goal のベンチの正解は 19〜21 件で止まった（[adaptive_shared_library.md](adaptive_shared_library.md)）。
そこで、残りの 1〜2 件を追うのはやめ、決まった Goal を解く方式から、モデルが自分で問いを立てて世界を探索する方式に切り替えた。
Voyager の automatic curriculum に当たるものを足し、答えが出た問いを World Graph に積む（[architecture_vision.md](architecture_vision.md)）。

- `geo_voyager/curriculum.py`: 次に調べる Goal を 1 件だけ決める。読むものは、利用できるリソース、これまでの発見（新しいものから 20 件）、試した Goal とその結果（新しいものから 15 件）。study-geoai の実験などの到達目標は見せない。
- `geo_voyager/world_graph.py`: 答えが出た Goal を記録する（DONE で終わり、最後の Critic も成功）。答えと一緒に、成功した step の Intent と Observation、使ったリソース、最後の Critic の理由、判明した対象（名前と安定 ID）を残す。oracle の YuisekinGeoSPARQL には書き込まない。
- `bench/run_explore.py`: 提案、実行、記録を繰り返す。Skill library、World Graph、試した Goal の記録は Goal をまたいで引き継ぐ。同じ `--out` と `--library` を指定すれば、前回の続きから再開できる。

## 1 回目（2026-10-11、32 Goal）

コードは `c530ee5`。記録は [evidence/explore_1/](evidence/explore_1/)。`world.jsonl` が World Graph、`exploration.jsonl` が試した Goal の記録。

- 32 Goal のうち 26 で答えが出た。1 Goal は平均 4.5 分。
- 正しさ: 26 件の発見から一様ランダムに 6 件を抜き、自前の Overpass と YuisekinGeoSPARQL の値と照らした。6 件とも一致した。
- 問いの広がりは狭かった。
  - 1〜11 番: 区の日本語ラベルの文字数と、relation_id の最大値・合計。
  - 12〜32 番: 7 つの区の `railway=station` と `railway=subway` の件数と、その比較・合計。
  - 使ったリソースは YuisekinGeoSPARQL と Overpass だけ。Dataset 5 つ（人口、駅、WorldPop、都市計画など）と、Nominatim、Valhalla、taginfo は 1 度も使っていない。
- 世界について意味の無い問いが混じった。relation_id は識別子なので、その最大値や合計は何も教えない。`railway=subway` は地下鉄の線路の区間の数で、駅の数ではない。値は正しく測れているが、何を測っているかの吟味が無い。
- Curriculum の理由は、どれも直前の発見から一歩ずらすものだった（「3 文字を数えたので次は 2 文字」「足立区と葛飾区を比べたので次は合計」）。少しずつ進むようには書いたが、何を知ると世界の理解が増えるかは書いていない。

## 2 回目に入れた変更

- Curriculum に、リソースごとの発見の数と、まだ使っていないリソースの一覧を見せる。
- 問いは、世界について何かを教えるものにするよう書いた。識別子の最大値や合計は問いにしない。測る値が世界の何を表すかを考えて選ぶ。
- 直近の発見と同じ型の問い（同じ測り方で対象だけを変えたもの）を続けず、別の主題や測り方へ広げるよう書いた。
- 1 回目と比べられるように、2 回目は白紙の World Graph と Seed だけの Skill library から始める。
