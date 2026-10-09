# `対象:` の制限と Critic の変更後の focused E2E

2026-10-09。`対象:` を実体だけに制限した版と、Critic の 0・矛盾への指示を足した版で、2 つの Goal を各 1 回だけ流した（反復なし、大規模ベンチマークなし）。記録は [evidence/entity_target_e2e/](evidence/entity_target_e2e/)。

| Goal | 停止 | step | Planner の失敗 | 最終 Critic の失敗 | Goal の Critic | oracle と一致 |
|---|---|---|---|---|---|---|
| `tag_top3_cuisine` | done | 1 | 0 | 0 | 成功 | 一致 |
| `cafe_shibuya_vs_shinjuku` | max_steps | 8 | 0 | 1 | 失敗 | 不一致（oracle は 459 と 343） |

## `tag_top3_cuisine`

1 step で DONE、最終 Critic も成功し、oracle と一致した。`対象:` の誤用は出なかった（`対象:` を付けた step が無い）。前回の E2E（`adaptive_e2e`）にあった `飲食店タグの値上位3件` のような説明文の `対象:` は再発しなかった。1 回なので、再発しないとまでは言えない。

## `cafe_shibuya_vs_shinjuku`

- 対象の扱いは正しかった。`対象:` は `渋谷区` と `新宿区` の 2 つだけで、どちらも実体の名前だった。step 3 の `新宿区` の取得は、Critic が前段の渋谷区の ID と比べて誤って不一致と判定して失敗にし、step 4 で同じ Intent を出し直して通った。この誤判定は今回の変更とは別の挙動で、回復はできた。
- 失敗の原因は、件数の取得コードだった。step 2 で学習された Skill は `id_type == "relation"` で分岐して `+3600000000` を足す。実際の `intent_target["id_type"]` は `relation_id` なので分岐に入らず、area の ID が誤ったまま、渋谷区も新宿区も件数が 0 になった（コードは `evidence/entity_target_e2e/cafe_generated_skill_step2.txt`）。これは仮説で、area の ID を直した版を実行して確かめてはいない。
- step 5、6 で両区の件数 0 を Critic が通した。step 6 の後に DONE を返し、最終 Critic が「両区とも 0 と報告されているが、根拠や調査方法の説明がなく、矛盾や誤りの疑いが残る」と失敗にした（`final_critic_failure`、after_step 6）。これは今回足した Critic の指示が、最終 Critic の段で働いた例になる。一方、step 単位の Critic は 0 を通した。
- 回復はできなかった。step 7 と 8 は同じ Skill を再利用して同じ 0 を返し、8 step の上限で止まった。Planner の step 7 と 8 の Intent には、Overpass のクエリ文（`nwr["amenity"="cafe"](area:...)` など）が書かれていた。Planner の API 詳細の拒否（`api_details_in`）がこの書き方を検出していない。

## 結論と未解決

- `対象:` の制限は、この 2 本では、害を出さなかった。効果は 1 回ずつなので確かめたとは言えない。
- 失敗は、`対象:` の制限や Critic の変更の外にある。
  1. 生成コードが `intent_target["id_type"]` の実際の値（`relation_id`）と違う値で分岐する（Generator の契約）。
  2. step 単位の Critic が件数 0 を通す（プロンプトだけでは防げない。[critic_accepted_wrong.md](critic_accepted_wrong.md)）。
  3. Planner の Intent に Overpass のクエリ文が入る（`api_details_in` の検出漏れ）。
- 2 と 3 は前の結論と同じ範囲にある。1 は新しい。今回は直していない。

## 追記: Generator と Planner の欠陥を直したあとの再実行（1 回）

直したもの（LLM なしの決定的なテストで確かめた。単体テスト 775 件が通る）。

- Generator: Overpass の指示に、area の ID は `int(intent_target["id_value"])` に 3600000000 を足した値であり、`id_type` を固定の文字列と比べないことを書いた。生成されたコードが `id_type` を固定の文字列と比べていたら（`geo_voyager/id_type_literals.py`、AST で検出）、理由を添えて最大 2 回作り直させ、それでも残るなら `ValueError('Candidate compares id_type ...')` で拒否する。対象に ID があるときだけ検査する。
- Planner: Intent に Overpass QL（`[out:json]`、`nwr[`、`(area:...)`、`out count`）や SPARQL（`SELECT ?`、`WHERE {`）が書かれていたら、`api_details_in` が検出して拒否する。`area_id` という語や `gs:Ward` のような型名は拒否しない。

`cafe_shibuya_vs_shinjuku` を 1 回だけ流した（[evidence/entity_target_e2e2/](evidence/entity_target_e2e2/)）。

| 確認項目 | 結果 |
|---|---|
| 459 と 343 が得られたか | 得られた（step 4 が渋谷区 459、step 5 が新宿区 343。oracle と一致） |
| Planner が Overpass QL を Intent に書かなかったか | 書かなかった（5 step の Intent に QL なし） |
| DONE と最終 Critic の成功まで行ったか | 行った（done、5 step、最終 Critic の失敗 0、Planner の失敗 0） |
| 正しい relation ID から area ID への変換か | 最終的には正しい（件数が 0 でなく 459 と 343）。ただし下記のとおり、最初の生成は誤っていた |
| harness の oracle 判定 | 不一致（下記） |

- step 3 の生成コードは、`get_area_id(id_value, id_type)` の関数の引数として `id_type == 'relation'` と比べていた。`target_type = intent_target["id_type"]` を関数に渡す形で、このときの検査は、`intent_target["id_type"]` を直接比べる形しか見ていなかったため通した。実行は `ValueError: Unsupported id_type: relation_id` で失敗し、step 4 で同じ Intent を出し直して正しく通った。この関数の引数を追う形（値の受け渡しを 3 段まで）は、この実行のあとで検査に足した。足したあとの E2E は流していない。
- harness の oracle 判定が不一致だったのは、`judge_winner` が最終 Observation に勝者（渋谷区）が書かれていることを求めるのに、最終 step の出力が新宿区の 343 だけだったため。どちらが多いかを比べる step は無く、Planner は 2 つの件数を得た時点で DONE を返した。最終 Critic は「比較の結果（渋谷区が多い）が示されている」と成功にしたが、比較を出力した step は無い。最終 Critic が、履歴にある 2 つの数字から自分で比べた答えを、出力されたものとして扱った可能性がある（仮説。最終 Critic のプロンプトは確かめていない）。件数は正しいので、Goal の答えとしては材料が揃っているが、「どちらが多いか」を出力する step が欠けている。
- 前回の失敗（件数 0 が 4 回続き 8 step で停止）は、この 1 回では再現しなかった。1 回なので、直ったとまでは言えない。
