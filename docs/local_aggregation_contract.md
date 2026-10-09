# ローカル集計のコードの契約

2026-10-10。前段の Observation だけを使うローカル集計（`Intent.requires_context`）の生成コードに、2 つの契約を決定的に検査する仕組みを足した。きっかけは `cafe_shibuya_vs_shinjuku` の E2E（[entity_target_e2e.md](entity_target_e2e.md)）で、比較コードが次の 2 つを書いたこと。

- `shibuya.get('count', 0)`: 件数を持たない object（ID を調べた step の出力）に当たり、欠落が 0 になって「同数」と答えた。
- `decoded[2]`、`decoded[3]`: Observation を並びの位置で選んだ。

## 契約

`geo_voyager/local_aggregation_contract.py`（AST）が次を見つける。

| 違反 | 例 | 備考 |
|---|---|---|
| 測定値の欠落を数値や None の既定値で代用 | `o.get("count", 0)`、`o.get("count", None)` | 空文字列（表示名）、空の list・dict は見ない。キーが 1 つの `.get(k)` も見ない |
| Observation を位置で選ぶ | `previous_observations[0]`、`decoded[2]`、`rows[-1]` | `previous_observations` から作った名前（list 内包表記、`list(map(...))`）も追う。`if` で絞った内包表記の結果（`matches[0]`）は位置とは見ない。前段の Observation がちょうど 1 件のときは位置を見ない（選ぶ余地が無く、Generator にもそう示している） |

- Generator: ローカル集計の Intent で、検査に引っかかったコードは、理由を添えて最大 2 回作り直させる。それでも残るなら `ValueError('Candidate breaks the code contract: ...')` で拒否する（失敗が見える）。`id_type` の検査と同じ仕組みで、両方を 1 つの作り直しの文面にまとめる。プロンプトにも、番号や位置で選ばないこと、名前と ID で選ぶことを書いた。
- runtime repair: repair 後のコードに同じ検査をかける。残るなら作り直させ、それでも残るなら元のコードを返す（`rejected_fallbacks` に記録）。
- 単体テスト 812 件が通る。違反の形、許す形（絞った内包表記、キーのみの `.get`、空文字列の既定値、1 件のときの `[0]`）、Generator と repair の作り直しと拒否と、検査しない Intent を確かめている。

## 保存済みのコードに当てた結果（LLM なし）

保存された `goal_report.json` から、ローカル集計の Intent（`requires_context`）の試行コード 83 件（重複を除く。前段の件数は 1 件が 45、2 件が 28、3 件が 10）に当てた。21 件（25%）が検出された。

- 位置で選んだもの: `tag_ramen_vs_sushi`（前段 2 件で `previous_observations[0]`、`[1]` や `obs[0]`、`obs[1]`）、`ward_pop_total`、`library_setagaya` など。
- 欠落を既定値で代用したもの: `counts.get('cuisine=ramen', 0)`、`counts.get('cafe', 0)`、`x.get('count', 0)`、`route.get('summary', {}).get('length', 0)` など。
- 検出されたコードの中には、位置が偶然正しく、Critic が通して正解になった実行が含まれる。検査は、正しさではなく、書き方の契約を見ている。

## 分かっていないこと

- 検査に引っかかったとき、実 LLM が 2 回の作り直しで契約を守れるか。守れないと、これまで通っていた約 4 分の 1 のローカル集計が `ValueError` で失敗になる（失敗した step は Planner に見え、別の Intent で回復できるが、測っていない）。LLM を回した確認はしていない。
- 位置の検査は、1 件のときに許している。前段が 2 件以上でも `previous_observations` を変数に束ね直した形（`a, b = decoded` など）は検出しない。
- Planner が履歴の件数を Intent の文面に書き写す問題は、この変更では扱っていない。
