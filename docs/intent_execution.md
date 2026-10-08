# IntentExecutor 実 integration 記録（2026-10-08）

実 embedding / gvt-llm / Docker sandbox / Fetch Gateway / 固定 revision Dataset を使った3経路の記録です。
初期6件を一時 filesystem Library にコピーし、リポジトリの初期 Library は変更していません。

## API

`IntentExecutor(retriever, selector, worker, generator, critic, skill_library).execute(intent, k=4)`
は frozen `IntentExecution` を返します。observations、retrieved_skill_ids（順位順）、selected_skill_id、
learned_skill_id、学習経路だけの critique を保持します。

`Worker.execute_skill(intent, skill)` は渡された Skill を実行し、保存しません。
`Worker.execute_candidate(intent, candidate, critic, skill_library)` は `(observations, critique, learned_skill)`
を返し、Critic 成功後だけ UUID 生成・保存します。失敗判定では learned_skill は None です。
Dataset ID は両 Worker 経路と Executor で1件のみを許可します。

## 実行結果

### 東京都23区で人口が最も多い区と人口を求める

retrieved_skill_ids（順序を保持）:

1. `e722f367-1ff1-4796-89a3-48cfd1dfcb68`
2. `f2d4785a-779a-4927-b75d-65d1e4852ab2`
3. `befbc141-baad-41bc-abdf-dc34311c3111`
4. `72c549dd-e449-4bef-97f1-e3a2eab27d64`

selected_skill_id: `72c549dd-e449-4bef-97f1-e3a2eab27d64`
learned_skill_id: `None`

Observation:

```text
東京都23区で人口が最も多い区は世田谷区で、人口は943664人である
```

既存 Skill を再利用し、Generator・Critic・保存は呼ばれていません。一時 Library は6件のままです。

### 駅データに収録されている最北端の駅を求める

retrieved_skill_ids（順序を保持）:

1. `fb0fb79f-10b3-424f-ae27-4d6292f474c4`
2. `ccd6a22b-d795-4359-a06a-f2ac214e6a28`
3. `e722f367-1ff1-4796-89a3-48cfd1dfcb68`
4. `f2d4785a-779a-4927-b75d-65d1e4852ab2`

selected_skill_id: `fb0fb79f-10b3-424f-ae27-4d6292f474c4`
learned_skill_id: `None`

Observation:

```text
駅データに収録されている最北端の駅は稚内駅で、緯度は45.416995、経度は141.676999である
```

既存 Skill を再利用し、Generator・Critic・保存は呼ばれていません。一時 Library は6件のままです。

### 東京都23区の平均人口を求める

retrieved_skill_ids（順序を保持）:

1. `befbc141-baad-41bc-abdf-dc34311c3111`
2. `e722f367-1ff1-4796-89a3-48cfd1dfcb68`
3. `f2d4785a-779a-4927-b75d-65d1e4852ab2`
4. `72c549dd-e449-4bef-97f1-e3a2eab27d64`

selected_skill_id: `None`
learned_skill_id: `4038ef3d-4721-4a91-905d-a1b8be10367d`

Observation:

```text
東京都23区の平均人口は 423185.9130434783 です。
```

Critic: success=True、理由: 東京都23区の平均人口という具体的な数値が観測結果として提示されているため、Intentの要求を満たしている。

保存 UUID: `4038ef3d-4721-4a91-905d-a1b8be10367d`
description: 東京都23区の平均人口を計算し、その値を出力します。

保存された code:

```python
from geo_voyager.control_primitives import connect_duckdb, load_admin_units, load_stations
with connect_duckdb() as connection:
    df = load_admin_units(dataset_id, connection, area="東京都23区")
    avg_df = df.aggregate("avg(population) AS average_population")
    average_population = avg_df.fetchone()[0]
    print(f"東京都23区の平均人口は {average_population} です。")
```

## 保存・実行経路の確認

- 平均人口の Selector は None を返し、Generator を1回呼びました。
- 生成コードは Primitive 経由で23区を読み、DuckDB relation.aggregate の avg(population) を計算しました。
- stdout の平均値は、別 sandbox で23件の人口を読み Python で合計 / 件数を計算した値と照合しました。期待する平均値をテストに埋め込んでいません。
- Critic 成功後だけ1件保存し、一時 Library は6→7件。初期 Library は同じ6件・同じ code/description のままです。
- 一時 Library: `/tmp/pytest-of-yuiseki/pytest-278/test_reuse_admin_and_station_t0/skill_library`。
- Worker は internal network のみ、Gateway は internal + external、host filesystem mount なし。Gateway の両 Dataset パスと HTTP Range 206 を確認。検証 container / network を削除。
- Critic 失敗時の非保存、既存 Skill 失敗時の非 fallback、候補順の保持、Dataset 0件・複数件の拒否は unit test で確認。
- runtime の retry / self-repair、similarity threshold、複数 Dataset、Vector DB、Planner 接続は追加していません。不正な LLM 出力や sandbox エラーは例外として伝播し、保存しません。
- [JSON の生記録](intent_execution.json)

## 再実行

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_intent_executor.py -q -s -W error
```

既存 unit / integration をまとめて実行すると同名テストファイルがあるため、importlib mode を使います。

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests integration --import-mode=importlib -q -W error
```
