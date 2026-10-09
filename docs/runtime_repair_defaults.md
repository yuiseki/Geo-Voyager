# runtime repair が欠落値を既定値で隠さないようにする

2026-10-09 に、runtime repair（実行失敗の traceback に答える repair）が、必須の値の欠落を既定値で隠して「成功」にすることを防ぐ検査を足した。
変更したのは runtime repair だけである。semantic repair、Planner、Critic には触れていない。

## 防ぎたかった失敗

Taginfo の応答の項目が `count` なのに、コードが `item["count_all"]` を引いて `KeyError` になる。
repair が `item.get("count_all", 0)` に直すと、例外は消えて実行は通るが、使用数が全部 0 になる。実行の成功と答えの正しさは別なので、この直しは失敗を隠すだけである。

## 変更

- プロンプト: 必須フィールドの欠落は、実際の API や Observation の形を確かめて正しいキーに直すこと、既定値や握りつぶす except で隠さないこと、欠落は例外のまま残すこと、取り出しは `[]` か明示的な `assert` で行うことを指示した（system prompt にも一文）。
- 決定的な検査（`geo_voyager/default_fallback.py`）: repair 後のコードを AST で見る。
  - traceback の `KeyError: 'k'` にあるキー `k` について、新しく入った `.get(k, 既定値)` を拒否する。
  - 1 引数の `.get(k)` は、直後に `assert` か `raise` で明示的に確かめているときだけ許す。
  - 新しく入った、例外を握りつぶす handler を拒否する。
  - stderr に `KeyError` か `IndexError` がないときは何も見ない。元からある任意の `.get()`（例えば `.get("tags", {})`）は、キーが失敗に出たキーでなければ見ない。
- 拒否したら、拒否の理由を添えて最大 2 回まで生成し直す（`max_default_retries`）。それでも既定値が残るなら、直さずに元の Candidate を返す。失敗は失敗のまま見える。拒否の記録は `SkillCandidateRepairer.rejected_fallbacks` と、`bench/run_adaptive.py` の行の `rejected_fallbacks` にある。

## 検証

### 単体テスト

`tests/test_default_fallback.py`（32 件）と `tests/test_candidate_repair.py` の追加分。全体で 735 件が通る。依頼された 3 点を含む。

- `item["count_all"]` から `item.get("count_all", 0)` への直しは拒否される。
- 正しいキー `item["count"]` への直しは許される。
- 元からある任意の `.get()` は誤検出されない。

そのほか、1 引数の `.get` と明示的な確認、握りつぶす handler、生成し直しの回数、回数が尽きたときに元を返すこと、プロンプトの文面を確かめている。

### 保存済みの記録への適用（LLM なし）

保存済みの repair 581 組のうち、`KeyError` の repair は 96 件。検査が拒否したのは 3 件だった。最初に考えた規則（`.get` の既定値を全部拒否する）は `.get('tags', {})` などを誤って拒否したので、失敗に出たキーに限る規則に直した。3 件の中身を人が確かめた結果は、この文書には書いていない。

### 実 LLM の再生

保存した `count_all` の Candidate と stderr で、実 repairer と実 LLM を 6 回呼んだ（`python -m bench.replay_repair_fallback 6`）。

| プロンプト | 最初の応答が値を隠した | 最終コードが正しいキー | 最終コードに既定値 |
|---|---|---|---|
| 新（`d0fa1d4` の次の版） | 0 / 6 | 6 / 6 | 0 / 6 |
| 旧（`d0fa1d4`） | 0 / 6 | 6 / 6 | 0 / 6 |

旧プロンプトでも 6 回とも正しいキーに直したので、この再生は新旧の差を示せない。理由は確かめていないが、Taginfo の説明に「使用数のフィールドは count（count_all ではない）」と書いたことが、旧プロンプトでも効いている可能性がある。つまり、この再生で言えるのは「新しい版でも既定値は出なかった」までで、「新しい指示と検査が既定値を防いだ」とは言えない。
旧版には検査がないので、旧の行の「最初の応答が値を隠した」は、同じ検査関数を応答に当てて数えた値である。

### end-to-end（`tag_top3_cuisine` を 3 回）

3 回とも `done`、1 step、oracle と一致した。repair は 3 回とも起きなかった（初回のコードが通った）。したがって、検査は実行時に一度も発火していない。実際の run で検査が効くかどうかは、まだ観察していない。
記録は [evidence/runtime_repair_defaults/e2e_tag_top3_cuisine.jsonl](evidence/runtime_repair_defaults/e2e_tag_top3_cuisine.jsonl)。

## 分かっていないこと

- 検査が実際の run で発火したときの挙動（生成し直しで直るか、元を返すか）は、単体テストでしか確かめていない。
- 値の欠落を `.get(k)` や `try` 以外の形（例えば `or 0`、`if k in d else 0`）で隠す書き方は検出しない。
- 検査は `KeyError` と `IndexError` の失敗だけを対象にする。`count_all` の例のように、実行時に例外を起こさない別の誤り（空の配列が出るなど）は、semantic repair と Critic の領分である。

## 再現

```bash
.venv/bin/python -m pytest tests/test_default_fallback.py tests/test_candidate_repair.py
.venv/bin/python -m bench.replay_repair_fallback 6
```
