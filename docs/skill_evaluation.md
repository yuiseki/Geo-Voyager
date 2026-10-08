# Skill Retriever / Selector 評価（2026-10-08）

既存2件と追加4件の description を embedding し、Intent.text との cosine similarity で top-4 を取得。
同じ候補を Selector に渡しました。Worker / Generator への検索・選択の接続は追加していません。

- embedding: `http://10.105.167.163:8080/v1/embeddings`、`granite-embedding`（granite-embedding-97m-multilingual-r2）。
- Selector / Critic: 既存 `gvt-llm`、`http://10.108.45.102:8080/v1/chat/completions`。
- recall@4: 6/6、Selector 正解: 6/6。この6例の結果であり、一般的な精度保証ではありません。
- [全 UUID・順位・cosine 値・選択結果の JSON](skill_evaluation.json)

## Skill 一覧

| 分析 | UUID | description |
|---|---|---|
| 人口最大 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | 行政区域の集合から人口が最も多い区域と人口を求める |
| 人口最小 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 東京都23区の人口データを対象に、人口で昇順ソートし、最も人口が少ない区の名前と人口を取得します。 |
| 人口合計 | `befbc141-baad-41bc-abdf-dc34311c3111` | 東京都23区の行政区域を対象に、人口を合計して総人口を求める。 |
| 人口上位5区 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 東京都23区の行政区域を人口降順に並べ、人口が多い上位5区の名前と人口を求める。 |
| 全国駅数 | `ccd6a22b-d795-4359-a06a-f2ac214e6a28` | 全国の駅データに収録されている全レコードの件数を集計する。営業状態による絞り込みや同一駅の重複排除は行わない。 |
| 最北端駅 | `fb0fb79f-10b3-424f-ae27-4d6292f474c4` | 全国の駅データに収録されている駅を緯度降順に並べ、最北端の駅名・緯度・経度を求める。営業状態による絞り込みは行わない。 |

## 4件の実 Docker / Gateway / Dataset 実行結果

答えはコードやテストの期待値に埋め込まず、固定 revision の実データから得ました。各結果で Critic.success=True を確認しました。

| Skill | stdout の結果 | Critic |
|---|---|---|
| 人口合計 | 9,733,276人 | 成功 |
| 人口上位5区 | 世田谷区 943,664人、練馬区 752,608人、大田区 748,081人、江戸川区 697,932人、足立区 695,043人 | 成功 |
| 全国駅数 | 10,962件（全レコード、営業状態で絞らず、同一駅の重複排除なし） | 成功 |
| 最北端駅 | 稚内駅、緯度45.416995・経度141.676999 | 成功 |

人口は Dataset Card に記載された2020年国勢調査の値です。駅数は物理的に異なる駅の総数ではなく、収録された路線別レコード数です。

## データ・Primitive

- 行政区域: `yuiseki/jp-admin-2026-09` の既存固定 revision `e6c87b1d7095c17422147962185071a986e13135`、`municipalities.parquet`。
- 駅: [固定 revision の Dataset Card](https://huggingface.co/datasets/yuiseki/ekidata-jp/blob/a33321099406b47338be0d03a4887059473fde0c/README.md)。
- [駅実ファイル](https://huggingface.co/datasets/yuiseki/ekidata-jp/blob/a33321099406b47338be0d03a4887059473fde0c/parquet/2026-10-05/station.2026-07-31.parquet)。
- `load_stations(dataset_id, connection)` は `station_name AS name, lat AS latitude, lon AS longitude` の relation を返すだけで、集計・並べ替え・フィルタは Skill が行います。
- DatasetGraph の `data_url` に固定 revision の駅ファイルを登録。Gateway は登録済み URL を解決し、GET / HEAD / Range を処理します。
- 実験用 resolver は既存の署名付き配信先検証を駅ファイルにも適用。Gateway の redirect 自動追跡・任意 URL API は追加していません。
- Worker sandbox は internal-only、Gateway は internal + external。mount なし、既存 sandbox 制約を維持。テストで作った container / network は削除。

## 6 Intent の評価

下記の UUID は Skill 一覧と対応します。各順位の cosine 値は Retriever が実際に使ったベクトルから計算しました。

### 東京都23区で人口が最も多い区と人口を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.954261 |
| 2 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 0.951463 |
| 3 | `befbc141-baad-41bc-abdf-dc34311c3111` | 0.947392 |
| 4 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | 0.873333 |

正解 top-4 入り: はい。Selector: `72c549dd-e449-4bef-97f1-e3a2eab27d64`。判定: 正解。

### 東京都23区で人口が最も少ない区と人口を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.954269 |
| 2 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 0.937927 |
| 3 | `befbc141-baad-41bc-abdf-dc34311c3111` | 0.934802 |
| 4 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | 0.865793 |

正解 top-4 入り: はい。Selector: `e722f367-1ff1-4796-89a3-48cfd1dfcb68`。判定: 正解。

### 東京都23区の人口合計を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `befbc141-baad-41bc-abdf-dc34311c3111` | 0.974665 |
| 2 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.942340 |
| 3 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 0.933311 |
| 4 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | 0.842443 |

正解 top-4 入り: はい。Selector: `befbc141-baad-41bc-abdf-dc34311c3111`。判定: 正解。

### 東京都23区で人口が多い上位5区を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 0.968381 |
| 2 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.933094 |
| 3 | `befbc141-baad-41bc-abdf-dc34311c3111` | 0.915158 |
| 4 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | 0.857211 |

正解 top-4 入り: はい。Selector: `f2d4785a-779a-4927-b75d-65d1e4852ab2`。判定: 正解。

### 駅データに収録されている駅の総数を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `ccd6a22b-d795-4359-a06a-f2ac214e6a28` | 0.910162 |
| 2 | `fb0fb79f-10b3-424f-ae27-4d6292f474c4` | 0.871328 |
| 3 | `befbc141-baad-41bc-abdf-dc34311c3111` | 0.841799 |
| 4 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.818755 |

正解 top-4 入り: はい。Selector: `ccd6a22b-d795-4359-a06a-f2ac214e6a28`。判定: 正解。

### 駅データに収録されている最北端の駅を求める

| 順位 | Skill UUID | cosine similarity |
|---|---|---|
| 1 | `fb0fb79f-10b3-424f-ae27-4d6292f474c4` | 0.932733 |
| 2 | `ccd6a22b-d795-4359-a06a-f2ac214e6a28` | 0.839102 |
| 3 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | 0.829286 |
| 4 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | 0.807295 |

正解 top-4 入り: はい。Selector: `fb0fb79f-10b3-424f-ae27-4d6292f474c4`。判定: 正解。

## 再実行

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -W error
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_worker_image.py -q -s -W error
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_initial_analysis_skills.py -q -s -W error
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_skill_retrieval_evaluation.py -q -s -W error
```
