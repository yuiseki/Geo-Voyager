# 複合 Goal の分解・repair・小さい Skill の再利用

2026-10-09 に実 Docker・ローカル llama.cpp・登録済みサービスで検証しました。記録した実行中に人間が Candidate code を修正する操作はありません。最初の `if :` のみ、repair 経路を必ず通すためのテスト用 fault injection です。その他の修正はすべて実 LLM の出力です。

## 1. コミット

- `bcadd10`: 実行失敗の構造化
- `834f703`: 最大2回の Candidate repair
- `545932d`: Attempt provenance
- `6165267`: Goal decomposition と前段 Observation の受け渡し
- 最終コミット: `feat: learn and reuse small skills through repaired goal execution`（この実測レポートを含む）

## 2. data model

```python
@dataclass(frozen=True)
class ExecutionFailure:
    message: str
    stdout: str
    stderr: str
    exit_code: int | None

@dataclass(frozen=True)
class ExecutionAttempt:
    code: str
    observations: list[Observation]
    failure: ExecutionFailure | None
```

`IntentExecution` は従来の observations / retrieved_skill_ids / selected_skill_id / selected_skill_critique / learned_skill_id / critique に加え、`failure` と `attempts: tuple[ExecutionAttempt, ...]` を保持します。`selected_skill_critique` は選択した既存 Skill、`critique` は最後の結果に対応します。失敗した実行には Critic を呼びません。

`Intent` は `previous_observations` を持ちます。前段だけを使う集計は `requires_context=True` で、実行時に前段 Observation が必須です。`GoalExecution` は実行した Intent、各 IntentExecution、最終 critique を保持します。

## 3. repair prompt

元の Intent・宣言済み Dataset/Service（実 JSON response envelope と binding value の API metadata を含む）・元 description/code・制限済み stdout/stderr・exit code・Primitive contract のみを渡します。Intent/サービス/分析操作を変更せず、失敗原因を修正した完全な Candidate を厳密な説明/コード形式で返すよう指示します。固定回答、秘密情報、追加API、修正の解説文を禁止します。前段結果は入力形だけを提示し、値は sandbox の `previous_observations` / `intent_text` から読みます。

## 4. repair 上限・実行境界

Candidate は初回＋repair 2回、最大3実行です。上限超過・Critic failure では UUID を生成せず保存しません。Docker infrastructure failure は例外のままです。sandbox 内 Python の syntax/runtime error は予約 exit code 73 の ExecutionFailure となり、stdout/stderr は各8 KiB（UTF-8 byte）に制限・redact されます。

## 5–6. Planner 出力と各 Intent の実行結果

> 東京23区で cuisine=burger の OSM 地物数が最も多い区を求める。全23区の件数と最多の区名・件数を示す。

分割内容は LLM 出力です。Python に burger 用の step list はありません。対象一覧→1対象ずつの23測定→ローカル最大選択の25 Intent になりました。

| step | Planner の調査項目（実際の出力） | Service | 結果 | selected / learned UUID | attempts | Generator呼出し |
|---:|---|---|---|---|---:|---:|
| 1 | 東京23区の名称と対応するOSM Relation IDの一覧取得（一覧の1番目から23番目まで） | yuisekin-geosparql | 23区・一意なrelation IDの一覧 | None / 9486734f-f0c8-4660-b986-327d44bfa337 | 2 | 1 |
| 2 | 一覧の1番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "世田谷区", "relation_id": "1759474", "count": 37} | None / d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | 1 | 1 |
| 3 | 一覧の2番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "中央区", "relation_id": "1758897", "count": 15} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 4 | 一覧の3番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "中野区", "relation_id": "1543056", "count": 16} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 5 | 一覧の4番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "北区", "relation_id": "1760038", "count": 14} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 6 | 一覧の5番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "千代田区", "relation_id": "1761742", "count": 35} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 7 | 一覧の6番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "台東区", "relation_id": "1758888", "count": 25} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 8 | 一覧の7番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "品川区", "relation_id": "3554304", "count": 23} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 9 | 一覧の8番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "墨田区", "relation_id": "1758891", "count": 18} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 10 | 一覧の9番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "大田区", "relation_id": "1758947", "count": 31} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 11 | 一覧の10番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "文京区", "relation_id": "1758878", "count": 16} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 12 | 一覧の11番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "新宿区", "relation_id": "1758858", "count": 46} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 13 | 一覧の12番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "杉並区", "relation_id": "1543055", "count": 20} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 14 | 一覧の13番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "板橋区", "relation_id": "1760078", "count": 29} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 15 | 一覧の14番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "江戸川区", "relation_id": "1761743", "count": 19} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 16 | 一覧の15番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "江東区", "relation_id": "3554015", "count": 28} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 17 | 一覧の16番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "渋谷区", "relation_id": "1759477", "count": 59} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 18 | 一覧の17番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "港区", "relation_id": "1761717", "count": 33} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 19 | 一覧の18番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "目黒区", "relation_id": "1758936", "count": 13} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 20 | 一覧の19番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "練馬区", "relation_id": "1760119", "count": 32} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 21 | 一覧の20番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "荒川区", "relation_id": "1760040", "count": 8} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 22 | 一覧の21番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "葛飾区", "relation_id": "1761718", "count": 17} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 23 | 一覧の22番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "豊島区", "relation_id": "1759506", "count": 27} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 24 | 一覧の23番目の区のOSM地物（cuisine=burger）の件数測定 | overpass | {"name": "足立区", "relation_id": "1760124", "count": 32} | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 / None | 1 | 0 |
| 25 | 全23区の測定結果から件数が最大の区の名称と件数の選択 | 前段のみ | {"name": "渋谷区", "relation_id": "1759477", "count": 59} | None / c022d065-ee3d-49c0-9fbd-0b074f2c9a0c | 1 | 1 |

全 step の Critic が success。最終 Critic: {"success": true, "reason": "全23区のburger地物数と最多の渋谷区（59件）が示されているため。"}

## 7–8. 実際の失敗 code / stderr / repair 差分

### step 1, attempt 1

失敗したコード:

```python
if :
from geo_voyager.control_primitives import call_service
import json, re

query = """PREFIX gs: <https://yuiseki.net/geosparql/schema#>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?relation WHERE {
  ?ward a gs:Ward .
  ?ward rdfs:label ?label .
  FILTER(LANG(?label) = "ja")
  ?ward gs:osmRelation ?relation .
} ORDER BY ?label"""

resp = call_service(service_id="yuisekin-geosparql", path="/geo/sparql", params={"query": query})
data = json.loads(resp)
results = []
for row in data.get("results", {}).get("bindings", []):
    label = row["label"]["value"]
    rel_uri = row["relation"]["value"]
    relation_id = rel_uri.rsplit("/", 1)[-1]
    assert str(relation_id).isdigit(), f"Invalid relation ID: {relation_id}"
    results.append({"name": label, "relation_id": relation_id})

assert len(results) == 23, f"Expected 23 wards, got {len(results)}"
print(json.dumps(results, ensure_ascii=False))
```

stderr:

```text
Traceback (most recent call last):
  File "<stdin>", line 15, in <module>
  File "<candidate>", line 1
    if :
       ^
SyntaxError: invalid syntax
```

exit code: 73

実 LLM repair の差分:

```diff
--- before.py
+++ after.py
@@ -1 +0,0 @@
-if :
@@ -3 +2 @@
-import json, re
+import json
```

## 9. 学習された Skill

保存先は同じ一時 file-based Library です。リポジトリの初期6 Skill は変更していません。成功した最終 code のみを保存し、embedding cache→VectorStore.upsert 後に次の step の検索対象になっています。

### `9486734f-f0c8-4660-b986-327d44bfa337`

YuisekinGeoSPARQLサービスで東京23区の名称と対応するOSM Relation IDの一覧を取得し、relation_idが数値であることを検証して出力する。

```python
from geo_voyager.control_primitives import call_service
import json

query = """PREFIX gs: <https://yuiseki.net/geosparql/schema#>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?relation WHERE {
  ?ward a gs:Ward .
  ?ward rdfs:label ?label .
  FILTER(LANG(?label) = "ja")
  ?ward gs:osmRelation ?relation .
} ORDER BY ?label"""

resp = call_service(service_id="yuisekin-geosparql", path="/geo/sparql", params={"query": query})
data = json.loads(resp)
results = []
for row in data.get("results", {}).get("bindings", []):
    label = row["label"]["value"]
    rel_uri = row["relation"]["value"]
    relation_id = rel_uri.rsplit("/", 1)[-1]
    assert str(relation_id).isdigit(), f"Invalid relation ID: {relation_id}"
    results.append({"name": label, "relation_id": relation_id})

assert len(results) == 23, f"Expected 23 wards, got {len(results)}"
print(json.dumps(results, ensure_ascii=False))
```

### `d3c1dc7f-7415-4c0e-b521-2332b807f7c2`

前段一覧から実行時に指定された対象を選び、指定条件に一致する地物の件数を取得する。

```python
from geo_voyager.control_primitives import call_service
import json, re
position = int(re.search(r"([0-9]+)番", intent_text).group(1)) - 1
target = json.loads(previous_observations[0])[position]
aid = int(target["relation_id"]) + 3600000000
verify = f"[out:json];area({aid});out ids;"
r1 = call_service("overpass", path="/api/interpreter", body=verify, content_type="text/plain")
d1 = json.loads(r1)
if not d1.get("elements"): raise ValueError("Missing area")
ql = f"[out:json][timeout:12];nwr[\"cuisine\"=\"burger\"](area:{aid});out count;"
r2 = call_service("overpass", path="/api/interpreter", body=ql, content_type="text/plain")
d2 = json.loads(r2)
count = int(d2["elements"][0]["tags"]["total"])
print(json.dumps({"name": target["name"], "relation_id": target["relation_id"], "count": count}))
```

### `c022d065-ee3d-49c0-9fbd-0b074f2c9a0c`

previous_observationsから各区の測定結果を解析し、件数が最大の区の名称と件数を選択して出力する。

```python
from geo_voyager.control_primitives import call_service
import json

decoded = [json.loads(text) for text in previous_observations]
assert len(decoded) == 24, "Expected 24 observations"
targets = decoded[0]
assert len(targets) == 23, "Expected 23 targets"

max_count = -1
max_name = None
max_rel_id = None

for i in range(1, 24):
    obs = decoded[i]
    name = obs["name"]
    rel_id = obs["relation_id"]
    count = obs["count"]
    if count > max_count:
        max_count = count
        max_name = name
        max_rel_id = rel_id

assert max_name is not None, "No valid observation found"

result = {"name": max_name, "relation_id": max_rel_id, "count": max_count}
print(json.dumps(result))
```

## 10. 後続 step の再利用証拠

| step | selected_skill_id | learned_skill_id | Generator呼出し | selected Skill Critic |
|---:|---|---|---:|---|
| 3 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 4 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 5 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 6 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 7 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 8 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 9 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 10 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 11 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 12 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 13 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 14 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 15 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 16 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 17 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 18 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 19 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 20 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 21 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 22 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 23 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |
| 24 | d3c1dc7f-7415-4c0e-b521-2332b807f7c2 | None | 0 | True |

再利用のコードは実行時の Intent から対象番号を取り、前段一覧を選択します。23区を回す巨大な Skill は保存していません。この実例の測定 Skill は任意の対象区に再利用できますが、タグ条件は今回の `cuisine=burger` です。

## 11. 最終23区集計

Overpass データ時点: `2025-09-14T23:59:55Z`。`nwr["cuisine"="burger"]` の完全一致です。店舗の実在総数ではなく、該当する OSM node/way/relation の地物数です。

| 区 | OSM relation ID | 地物数 |
|---|---:|---:|
| 渋谷区 | 1759477 | 59 |
| 新宿区 | 1758858 | 46 |
| 世田谷区 | 1759474 | 37 |
| 千代田区 | 1761742 | 35 |
| 港区 | 1761717 | 33 |
| 練馬区 | 1760119 | 32 |
| 足立区 | 1760124 | 32 |
| 大田区 | 1758947 | 31 |
| 板橋区 | 1760078 | 29 |
| 江東区 | 3554015 | 28 |
| 豊島区 | 1759506 | 27 |
| 台東区 | 1758888 | 25 |
| 品川区 | 3554304 | 23 |
| 杉並区 | 1543055 | 20 |
| 江戸川区 | 1761743 | 19 |
| 墨田区 | 1758891 | 18 |
| 葛飾区 | 1761718 | 17 |
| 中野区 | 1543056 | 16 |
| 文京区 | 1758878 | 16 |
| 中央区 | 1758897 | 15 |
| 北区 | 1760038 | 14 |
| 目黒区 | 1758936 | 13 |
| 荒川区 | 1760040 | 8 |

最多は **渋谷区 59地物**。23区すべてについて、Goal完了後に独立した新規の per-area request と照合して一致しました。この照合スクリプトは LLM prompt や Skill Library に渡していません。

一括の set/prefetch を使った照合クエリと独立クエリで差が観測されたため、同じ area 条件の独立リクエストで検証しています。差の内部原因は断定していません。

## 12. テスト

unit 360件、integration 25件（既存23件＋burger E2E＋前段と現在回答の混同を拒否するCritic実テスト）に成功しました。通常の unit test は2.68秒、burger E2E は175.45秒です。すべて `-W error` で検証しています。通常 pytest の unit は HTTP/Docker/LLM を mock し、実サービス通信は integration に分離しています。Docker の作成リソースは context manager の finally で削除します。

実 E2E artifact: `/tmp/geo-burger-goal-v19-f09e1719-47b9-4278-a302-0b6f6cdbf60f/test_burger_goal_repairs_learn0`。各 LLM prompt/response、step report、goal_report.json、verified_counts.json、保存済み Skill を保持しています。
