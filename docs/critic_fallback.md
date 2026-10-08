# 既存 Skill の Critic 検証と1回の fallback

2026-10-08、実ローカル embedding / LLM / Docker / Gateway / 登録済み Dataset を使用しました。初期6 Skill を一時 Library にコピーし、リポジトリの Skill Library は変更していません。誤選択だけはテストで意図的に固定し、それ以降のコード実行・Critic・生成・保存は実実装です。

| Intent / 段階 | selected_skill_id | learned_skill_id | Critic | Observation |
|---|---|---|---|---|
| 東京都23区で人口が最も多い区と人口を求める | 72c549dd-e449-4bef-97f1-e3a2eab27d64 | None | True | 東京都23区で人口が最も多い区は世田谷区で、人口は943664人である |
| 駅データに収録されている最北端の駅を求める | fb0fb79f-10b3-424f-ae27-4d6292f474c4 | None | True | 駅データに収録されている最北端の駅は稚内駅で、緯度は45.416995、経度は141.676999である |
| initial_learning | None | 2e2d669f-cbfe-4aa9-8a37-f4e35a259806 | True | 東京都23区の平均人口は 423185.9130434783 人です。 |
| learned_skill_reuse | 2e2d669f-cbfe-4aa9-8a37-f4e35a259806 | None | True | 東京都23区の平均人口は 423185.9130434783 人です。 |
| learned_skill_reuse | 2e2d669f-cbfe-4aa9-8a37-f4e35a259806 | None | True | 東京都23区の平均人口は 423185.9130434783 人です。 |
| incorrect_selection_fallback | 72c549dd-e449-4bef-97f1-e3a2eab27d64 | 403cb8cf-48de-4651-b445-6cb13cff2ccf | True | 東京都23区の平均人口: 423185.9130434783 |

誤選択した人口最大 Skill の判定: 平均人口を求めるという要求に対し、最も人口が多い区の情報しか提供されていないため、必要な回答が不足している。

Candidate の判定: 東京都23区の平均人口として具体的な数値が報告されているため、要求された調査結果に答えている。

Library 件数は6→7→7→7→8。正常再利用では Generator・保存を呼ばず、再利用のたびに Critic を呼びました。Candidate の失敗時に promote / add が呼ばれずファイルが保存されないことは mock を使った unit test で確認しました。例外時の fallback はありません。

Worker の両 API は list[Observation] のみを返し、Critic / promote / SkillLibrary は IntentExecutor が担当します。fallback 後も最初の selected_skill_id を保持し、critique は最終 Candidate の結果です。

[全検索順位・判定理由・生成コード](critic_fallback.json)

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -s -W error \
  integration/test_intent_executor.py \
  --basetemp=/tmp/geo-critic-$(cat /proc/sys/kernel/random/uuid)
```

一時ディレクトリを保護するため、毎回新しい basetemp を指定してください。

## 判定の由来の保持

現在の IntentExecution は `selected_skill_critique: Critique | None` も保持します。正常再利用では `selected_skill_critique == critique`、fallback では既存 Skill の失敗判定と Candidate の最終判定を別々に保持します。候補なしでは `selected_skill_critique=None` です。上記 JSON はこのフィールド追加前の記録であり、既存 Skill の失敗はテスト側の `existing_critique` に記録していました。現在は Executor 自体が保持します。

フィールド追加後の実 integration も成功しました（unit 202件、対象 integration 1件）。平均人口 Intent に人口最大 Skill を誤選択した結果は `selected_skill_id=72c549dd-e449-4bef-97f1-e3a2eab27d64`、`selected_skill_critique.success=False`、`learned_skill_id=9a2af065-84e3-4ca7-8ff1-8706efc03fe7`、`critique.success=True`。Observation は平均人口423185.9130434783人でした。学習 Skill は一時 Library だけに保存しました。
