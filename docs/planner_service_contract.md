# Planner にサービスの説明を全文見せ、API の詳細を Intent に書かせない（続き: Taginfo の契約と出力キー）

2026-10-09 に、保存済みの `tag_top3_cuisine` の trace 4 本（失敗 3 本と成功 1 本）を読み、そこで見つかった原因のうち 2 つを直した。追加の LLM 実行は、直したあとの確認 1 本だけ。

## trace から分かったこと

対象の 4 本は、[observation_driven_recovery.md](observation_driven_recovery.md) の自然な実行のうち、`tag_top3_cuisine` の 4 本である（evidence の `natural_1` と `natural_2`）。

| 実行 | 停止 | step 数 | 各 step で得られたもの |
|---|---|---|---|
| F1 | repeated_intent | 5 | 空の配列が 2 回、HTTP 412（件数過多）、タグの名前や fixme の値の一覧が 2 回 |
| F2 | repeated_intent | 5 | HTTP 412 が 2 回、空の配列が 2 回、`No cuisine values found` が 1 回 |
| F3 | max_steps | 8 | 空の配列、HTTP 404 が 3 回、HTTP 412 が 2 回、別のキーの値の一覧が 2 回 |
| S（成功） | done | 1 | `pizza`、`burger`、`coffee_shop`（正解） |

- 失敗の 3 本では、`cuisine` の値の一覧が、1 度も得られていない。「済んでいる」ものは何もなく、Planner が足りない内容を取り違えたのではなく、取り方を知らなかった。
- Planner が見るサービスの説明は、各サービスの最初の 2 文だけだった（全体で約 3,200 文字のうち約 400 文字）。Taginfo では `search/by_value` しか見えず、正しい `/api/4/key/values` は 7 文目にあり、Generator にしか見えなかった。
- 1 回目の失敗の後、Planner は Intent の文面にエンドポイントを書き始め、実在しないパス（`/api/4/search/by_key`、`/api/4/keys/cuisine/values` など）を、F1 で 5 回中 4 回、F2 で 4 回中 4 回、F3 で 7 回中 7 回書いた。Generator はそれをそのままコードに書いた。成功の 1 本は、エンドポイントを書いていない。
- 同じ Intent が続いたのは、プロンプトの差が失敗 1 件ぶんで、その内容も前と同じだったため（temperature 0）。「同じ Intent を繰り返さない」というルールは守られなかった。
- step の Critic は原因ではない。この 4 本の 11 回の判定は、すべて正しかった（正解 3 値を含む出力を成功にしたのが 2 回、含まない出力を棄却したのが 9 回）。
- 履歴の表現は副次的な問題。失敗の理由と Observation は読めるが、「何を呼んだか」は出ない。
- 明示的な GoalProgress は、この記録からは必要と言えない。

## 変更

1. `Planner.next` が、サービスの説明を全文見せる。`Planner._resource_text` に `full` を足した。最初に全体を計画する経路（`plan_goal`）のプロンプトは、変更していない（保存したプロンプトとの一致を、テストが保つ）。プロンプトは、履歴が空のとき 5,913 文字で、約 2,900 文字増えた。
2. Intent の調査項目に、API のパスやパラメータが書かれていたら、`Planner.next` が決定的に拒否する（`geo_voyager/intent_text.py` の `api_details_in`）。拒否は `PlannerFailure` として履歴に残り、理由に、書かれたパスやパラメータが入る。Planner は、それを見て「何を調べるか」だけに書き直せる。プロンプトにも、「Service の説明は何ができるかを知るためのもので、API のパスやパラメータは書かない。呼び方は実行側が決める。書くと拒否される」と足した。

検出するのは、パス（`/api/4/key/values`、`/search`、URL）、実在するエンドポイントの末尾（`key/values`、`search/by_value`）、サービスが取るパラメータ（`limit`、`sort`、`order`、`sortname`、`sortorder`、`rp`、`page`、`query`、`q`、`format`、`data`、`offset`、`sort_count`）の `名前=値`、`params=`、`path=`、`call_service`。OSM のタグ指定（`amenity=cafe` や `cuisine=sushi`）は、データなので拒否しない。この検査は、`Planner.next` だけに適用する。

### 保存済みの Intent での確認（LLM は使っていない）

- Goal の文面（22 本）: 検出 0 件。
- step-by-step 経路の、`tag_top3_cuisine` 以外の Intent 44 件: 誤検出 0 件。
- 同じ経路の `tag_top3_cuisine` の Intent 24 件のうち、検出された 15 件は、すべてエンドポイントを書いたもの（実在しないパスが大半）。残りの 9 件には、エンドポイントの記述がない。
- 全体を最初に計画する旧経路が書いた Intent 431 件のうち 11 件が検出された。すべて Taginfo か Nominatim のエンドポイントを書いたもの。

## 確認の実行（`tag_top3_cuisine` を 1 本）

結果は、`planner_failure` で停止し、DONE には到達しなかった（記録は `evidence/planner_service_contract/`）。この実行は、後述の検査の修正より前のコードで行った。

- Planner の応答 1 回目: `調査項目:` が中国語の字（`调查项目:`）になり、形式の誤りで拒否された（回復の処理は働いた）。この応答には、サービスの説明を全文見たことで書けた、実在するエンドポイント `/api/4/key/values` と `sortname=count_all, rp=3` が入っていた。API の詳細を書く傾向は、説明を全文見せても残る。
- 応答 2 回目以降: パスは書かなくなったが、タグのキーを指すつもりの `key="cuisine"` を書き、これを検査が「API のパラメータ」と判定して拒否した。誤検出である。同じ文面が続き、同じ理由の反復で止まった。
- step 1（Goal を言い換えただけの Intent。パスも `対象:` もない）: 正しいエンドポイントが選ばれ、正しい上位 3 値が得られたが、件数が全部 `0` で、Critic が棄却した。

### 検査の修正

誤検出を受けて、`key` を API パラメータの一覧から外した。`key="cuisine"` は、Taginfo のパラメータ名でもあるが、OSM のタグのキーの書き方でもある。保存済みの 15 件は、すべて別のパスやパラメータで、引き続き検出される。この修正のあとの E2E は、実行していない。

## 見つかった別の問題と、その後の修正

確認の実行で、次の 3 つが見つかった。最初の 2 つは、続けて直した（次の節）。

- 件数が `0` になった原因は、Generator が `key/values` の応答のフィールドを `count_all` と書いたこと（実際は `count`）。Taginfo の説明に、`key/values` の応答のフィールドが書かれていなかった。
- Generator の「安定キー `name`、`relation_id`、`count` を使う」という一般的な指示のせいで、出力のキーが意味と合わない（`{"name": "cuisine_values", "relation_id": "cuisine", ...}`）。このキー名が、`discover_targets` に「対象」と誤解される恐れがある。
- `KeyError` を、runtime repair が `i.get("count_all", 0)` に直し、エラーを既定値 `0` で隠した。これは、まだ直していない。
- `対象:` を、ID を持つ実体だけに限る処理も、まだ入れていない。

## Taginfo の契約と出力キーの修正

### Taginfo の契約

`/api/4/key/values` の契約を、サービスの説明（`geo_voyager/services.py`）に足した。内容は、自前の Taginfo を直接呼んで確かめた事実だけである。

| 確かめた事実 | 結果 |
|---|---|
| `key` だけ、または `key` と `rp` だけ | どちらも HTTP 412（`number of results too large, use paging`）。`page` と `rp` の両方が必要 |
| `key`、`page=1`、`rp=3`、`sortname=count`、`sortorder=desc` | 200。上位 3 件が `pizza` 132565、`burger` 110797、`coffee_shop` 101080 |
| 応答の形 | 最上位が `url`、`data_until`、`page`、`rp`、`total`、`data`。`data` の各要素が `value`、`count`、`fraction`、`in_wiki`、`description`、`desclang`、`descdir` |
| 使用数のフィールド | `count`（`count_all` ではない）。`search/by_value` の要素は `key`、`value`、`count_all` |
| `sortname` | `count`、`value`、`in_wiki` は 200。`fraction`、`description`、未知の名前は HTTP 500 |

この契約が事実であり続けることを、実サービスに対する integration テスト（`integration/test_taginfo_contract.py`、3 件）が確かめる。Taginfo に届かなければ skip する。

### 出力キーの契約

Generator のプロンプトから、固定のキー指示を外した。

- 「`name`、`relation_id`、`count` を使う」を外し、「キーは、その値が何かを表す意味のある名前にする（例: `value`、`count`、`distance_km`）。固定のスキーマはない」「件数やタグのキーを `relation_id` の下に入れない」とした。
- `name` と `relation_id` 等の ID で出力するのは、出力が対象（区域・地物など、安定した ID を持つ実体）の一覧や、その対象についての測定のときだけにした。対象でないもの（タグの値、件数のランキング、距離など）は、意味に沿ったキー（例: `{"value": "pizza", "count": 132565}`）で出力する。
- `対象:` を持つ Intent では、出力に対象の `name` と ID を含めるよう足した。

これで、タグの値のような出力が、`discover_targets` に「対象」と誤解されなくなる（`name` と ID の両方を持たない出力は、対象として拾われない）。

### 修正後の確認（`tag_top3_cuisine` を 1 本）

結果は、`done`（2 step）、Goal の Critic も成功で、oracle と一致した（記録は `evidence/planner_service_contract/after_contract_fix/`）。

- 2 つの Intent のどちらにも、API のパスやパラメータはなく、`対象:` も付かなかった。
- 生成コードは、契約どおり `/api/4/key/values` に `page`、`rp`、`sortname=count`、`sortorder=desc` を付け、フィールドは `count` を使った。
- 出力のキーは、`{"value": "pizza", "count": 132565}` と意味に沿っていた。`relation_id` の流用はなかった。
- step 1 は、コードの内包表記がキーを上書きして、最後の 1 件だけを出力した（`{"value": "coffee_shop", "count": 101080}`）。Critic が「1 つの値のみ」と正しく棄却し、Planner が再計画して、step 2 で成功した。

1 本だけの実行なので、効果の大きさは言えない。以前の自然な 4 本では、この Goal が成功したのは 1 本だった。

## テスト

- 単体テスト: 693 件が通る。
- focused integration（`test_taginfo_contract`、`test_target_ref`、`test_critic_llm`、`test_service_primitive`、`test_execution_failure`、`test_fetch_gateway`、`test_service_learning`、`test_adaptive_goal`）: 19 件のうち 18 件が通る。落ちた 1 件は `test_service_learning` の `geosparql` で、以前から揺らぐテストである。出力キーの変更の前のコミットで 5 回流すと 1 回しか通らず、現在のコードでは 4 回中 1 回で、頻度は同じだった。変更による悪化の証拠はない。
