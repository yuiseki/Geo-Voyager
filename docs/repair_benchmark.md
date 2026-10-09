# repair の自然失敗ベンチマーク

2026-10-09 に、未知 Goal を実 LLM・実 Docker・登録済みサービスで実行し、repair の成功率と失敗の種類を測った。
人間は Candidate のコードを一切修正していない。fault injection も使っていない。

## 測り方

- Goal は 6 本。いずれも東京の特定の区で、OSM のタグに一致する地物数を求める（cafe、ramen、hospital、hotel、library、cafe と restaurant の比較）。
- 正解は Goal ごとに独立した oracle で取った。oracle は別の sandbox で登録済み Overpass に直接問い合わせて件数を得る。Planner、Generator、Repairer、Critic には渡していない。
- 区の relation ID は、推測せず自前 Nominatim で確認した（最初に書いた港区と台東区の ID は誤りだった）。
- Goal ごと・周回ごとに空の Skill Library で始める。最初の実装は周回間で Library を共有していて、2 周目が Skill の再利用になってしまった。この周は破棄し、周回ごとのディレクトリに直して取り直した。
- 失敗の種類は、traceback の最後の例外行で分類する（`geo_voyager/repair_stats.py`）。種類は syntax、api_syntax（HTTP 400 など）、api_transient（429、5xx、timeout）、data_shape、empty_result、assertion、other。
- success@k は、Candidate の連鎖（初回と repair 最大 2 回）のうち、k 回目までに例外なく実行できた割合。実行が通ることと答えが正しいことは別に数える。

再現:

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
  .venv/bin/python -m bench.run_goals --out ~/tmp/geo-voyager-bench/run --repeat 3
.venv/bin/python -m bench.report ~/tmp/geo-voyager-bench/run/results.jsonl
```

生の記録は [evidence/repair_benchmark/](evidence/repair_benchmark/) にある。

## ベースライン（repair は直前の失敗だけを見る）

コミット `7782db7`（1 周目）と `9dc38d3`（2、3 周目）。6 Goal を 3 周、合計 18 実行。

| 指標 | 値 |
|---|---|
| Goal の正解 | 8 / 18 |
| Critic が成功とした Goal | 8 |
| Critic が成功としたが oracle と不一致 | 0 |
| oracle を取れなかった実行 | 1 |
| Intent 数 | 36 |
| success@0 | 63.9% |
| success@1 | 75.0% |
| success@2 | 75.0% |
| 振動（同じコードに戻った連鎖） | 9 |

失敗した試行は合計 31 件で、内訳は data_shape 18、api_syntax 7、api_transient 3、empty_result 2、other 1。

repair が尽きた連鎖は 9 件あり、9 件とも同じエラーを 3 回繰り返し、同じコードに戻っていた。2 回目の repair で救えた連鎖は 0 件。原因は次の 3 種類だった。

- `KeyError: 0` が 3 件。Planner が「一覧の 1 番目」と書いたが、前段の Observation は区 1 件の dict で、コードは list として添字を引いた。
- `JSONDecodeError` が 3 件。検証クエリに `[out:json]` がなく、Overpass が XML を返した。エラーには応答の中身が出ない。
- Overpass の HTTP 400 が 3 件。`rel["name":"..."]` のような不正な Overpass QL。

別の失敗の型も見つかった。港区の Goal で、ステップ 1 が 23 区の一覧全体を返し、ステップ 2 のコードが先頭行（世田谷区）を港区として使った。実行は成功し、答えだけが誤る。最終の Critic は不一致を検出して失敗にしたが、repair は実行失敗にしか働かないので、そこで止まった。

## repair に失敗行と試行履歴を渡す（v1）

コミット `bf14985`。Repairer に、失敗した行の抜粋（失敗した行に印を付ける）と、これまでの各試行のエラーおよびコードが変わったかどうかを渡す。

### 失敗しきった連鎖の再生（制御実験）

ベースラインで失敗しきった 9 連鎖について、同じ初期コード、同じ前段 Observation、同じ sandbox で repair だけを変えて 3 回ずつ再生した。

| 変種 | 実行が通った | うち正解 | 実行は通ったが誤答 | コードが一度も変わらない |
|---|---|---|---|---|
| v0（従来） | 0 / 27 | 0 | 0 | 9 |
| v1（失敗行と履歴） | 9 / 27 | 5 | 4 | 1 |
| v2（v1 に、無変更コードの再サンプリングを足したもの） | 9 / 27 | 6 | 3 | 0 |

この連鎖は、従来の repair が失敗したものだけを集めている。v0 が 0 件なのは選び方による当然の結果で、v1 の改善率としては読めない。v1 と v2 に差があるとは言えない（同じ 9 件）。

### 全体のやり直し

v1 を入れて、同じ 6 Goal を 3 周（18 実行）。

| 指標 | ベースライン | v1 |
|---|---|---|
| Goal の正解 | 8 / 18 | 3 / 18 |
| success@0 | 63.9% | 55.9% |
| success@1 | 75.0% | 67.6% |
| success@2 | 75.0% | 76.5% |
| 振動 | 9 | 7 |

Goal 単位は 18 件と少なく、LLM の揺らぎも大きい。8 / 18 と 3 / 18 の差が v1 の悪化によるのか揺らぎなのかは、この数では判別できない。少なくとも v1 が全体の正解率を上げた証拠はない。

v1 の実行で正解にならなかった 15 件を見ると、repair が働く手前の誤りが多い。

- ステップ 1 が一覧の先頭行（世田谷区）を求める区として返す。実行は成功するので repair は働かない。3 件（ramen、cafe、hospital）。
- Planner が Goal によって 1 ステップから 4 ステップまで異なる計画を出す。同じ Goal でステップ数がばらつく。
- ステップ 2 で `rel["name":"..."]` の構文エラーなど、同じ失敗が残る。

## 分かっていないこと

- v1 は「失敗行の抜粋」と「試行履歴」の 2 つを同時に入れた。どちらが効いたか、あるいは効いていないかは切り分けていない。
- v2 の再サンプリングは、この 9 連鎖では v1 と差が出なかった。
- 失敗した連鎖を再生した結果だけでは、一般の Goal での repair 成功率は分からない。
- Goal が似た 6 本に偏っている。Taginfo、Valhalla、GeoSPARQL を使う Goal は測っていない。

## 次の論点

- 実行は成功したが Critic が失敗とした場合に、Critic の理由を repair に渡して修正を試みるか。
- 同じ Goal でも計画が揺れる問題（Planner）をどう測るか。
- 前段 Observation が dict 1 件のときに、list として添字を引かないよう、型の説明をどう強めるか。

失敗の種類を、Goal を広げて測った続きは [failure_categories.md](failure_categories.md) にある。
