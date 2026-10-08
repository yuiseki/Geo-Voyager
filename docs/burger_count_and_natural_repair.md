# burger 件数差と自然発生 repair の検証

新機能・プロンプト・実行制御は変更せず、既存の実行記録と実サービスを検証した。

## 63件と59件

前回 `fixed_analysis.py` は Taginfo で取得した値をセミコロン区切りのトークンとして検索していた。
今回の Goal は `cuisine=burger` の完全一致を要求していた。

```overpass
[out:json][timeout:12];nwr["cuisine"~"(^|;)burger(;|$)"](area:3601759477);out tags;
```

```overpass
[out:json][timeout:12];nwr["cuisine"="burger"](area:3601759477);out tags;
```

Worker → Service Gateway → 登録済み Overpass で上記を再取得した結果は、それぞれ63件・59件。
両方の `timestamp_osm_base` と `timestamp_areas_base` は `2025-09-14T23:59:55Z`。
area は同じ渋谷区 relation 1759477 に対応する3601759477、対象はいずれも node / way / relation。
`(type, id)` で比較すると完全一致の59地物すべてがトークン一致に含まれ、重複IDはなかった。
差は以下の4 node のみだった。

| OSM node ID | name | cuisine |
|---|---|---|
| 5072661386 | Whoopi Goldburger | burger;chinese |
| 11532870568 | Buttermilk Channel | american;dessert;breakfast;pancake;sandwich;burger |
| 11847062940 | MOM'S TOUCH | burger;fried_chicken |
| 13075151101 | Pepple Hiroo Terrace | american;burger;mexican |

前回は23区を一括取得後に区別に集計、今回は区ごとの直接検索という実行形の差もある。
しかし渋谷区を直接検索する上記二つだけで63/59を再現し、差分地物4件を特定できた。
この件数差は境界変更・スナップショット更新・重複排除によるものではなく、タグ一致条件の違いで説明できる。

地物ID集合・クエリ・差分タグは [count_difference.json](evidence/burger_verification/count_difference.json) に保存した。

## 人工的な失敗なしの repair

以前の burger 実行 v13 の最終集計ステップには、人工注入と無関係な自然発生失敗が残っていた。
初期候補は実LLM応答 `llm_53_response.txt` に含まれ、保存された `generated_3.py` と失敗attemptのコードが完全一致する。
元コードのSHA-256は `3c34c6e5f666f3956e78050ca12a73b1efba583ec42d34eb6b08f2ca84576514`。
元の v13 全体では最初のステップに人工注入があったが、この最終集計コードには注入・人手修正はない。
元の v13 pytest 自体は別の一括照合クエリの不一致で失敗しており、全体テスト成功の証拠としては扱わない。

今回、この自然生成候補と当時の入力をそのまま使い、ネットワークなしの実Dockerで独立に2回検証した。
Generator は保存済み候補を返す fake にして、Repairer と Critic は現在の実ローカルLLMを使った。
新しい無作為生成ではなく、出典の確認できる自然生成失敗例の再現検証である。

入力は区一覧1件と各区の測定結果23件、合計24 Observation。
モデルが生成した元コードは次のように全件数を23と仮定していた。

```python
observations = [json.loads(obs) for obs in previous_observations]
assert len(observations) == 23, "Expected 23 observations"
```

実行時のstderr:

```text
Traceback (most recent call last):
  File "<stdin>", line 15, in <module>
  File "<candidate>", line 7, in <module>
AssertionError: Expected 23 observations
```

### 独立検証1：失敗

元コード失敗 → repair1で件数を24に変更 → 一覧に `.get()` を呼び `AttributeError` → repair2で23件前提に戻る → 上限到達。
Critique は failure、learned UUID は `None`、Skill保存なし。
[全attempt](evidence/burger_verification/replay_1.json) を保存した。

### 独立検証2：成功

元コード失敗 → repair1で先頭の一覧を除外 → 実行成功 → Critic success → 一時Libraryへ1件保存。
人間はコードを変更していない。最大repair回数2は変更していない。

修正された箇所:

```python
if len(observations) > 0 and isinstance(observations[0], list):
    observations = observations[1:]
assert len(observations) == 23, f"Expected 23 observations, got {len(observations)}"
```

Observation は `{"name": "渋谷区", "count": 59}`。
Critic 理由は「渋谷区が59件で最も多く、Observationで名称と件数が特定されているため。」。
保存UUIDは `cc0a1ce2-9f4f-416f-99b3-55521f80dc5b`。保存コードが最終attemptと一致し、Libraryは0→1件になった。
リポジトリの初期Skill Libraryは変更していない。

[元LLM応答](evidence/burger_verification/original_llm_response.txt)・[入力](evidence/burger_verification/intent.json)・
[元コード](evidence/burger_verification/original.py)・[修正コード](evidence/burger_verification/repaired.py)・
[差分](evidence/burger_verification/repair.diff)・[成功attempt記録](evidence/burger_verification/replay_2.json) を保存した。

自然生成コード失敗→LLM修正→実行成功→Critic成功→保存の実例は確認できた。
ただし独立検証1は失敗しているため、常に修正成功することや十分な安定性は証明していない。

## 確認結果

- 既存unit test: **360 passed**（2.72秒、warningsをerrorとして実行）。
- 実通信確認: 同じ渋谷区への2種類のクエリで63/59と差分4地物を確認。
- 自然生成コードの再実行: 独立2回、1回失敗・1回成功。各回のrepair上限は2。
- 検証用Dockerコンテナ・networkは終了時に削除。実装・初期Skill・既存環境設定は変更なし。
