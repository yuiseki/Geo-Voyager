# 登録地理サービスの学習・再利用検証

2026-10-08〜09。既存ローカル `gvt-llm` と `granite-embedding`、実 Docker Gateway、実サービスを使用しました。

独自 User-Agent: `Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)`。

## 実行結果

| ケース | 初回 learned / 2回目 selected UUID | 結果 |
| --- | --- | --- |
| taginfo_overpass | `197995cd-bbf8-45de-b9fc-745daf17f179` | Taginfo から natural=volcano を発見し、日本の relation 境界内の OSM 地物179件を取得。名前がある地物の名称を出力。 |
| nominatim | `83421c83-3030-416f-86ea-9bb3ec4df89d` | 上野駅: 緯度35.7140413、経度139.7771164、OSM way 85395094。 |
| geosparql | `7abbab9d-a91c-42b7-89dd-a711543625de` | 台東区と接する区: 中央区、千代田区、墨田区、文京区、荒川区。 |

各ケースは同じ一時 Library で 0→1→1 件。初回 selected=None / learned=UUID、
2回目 retrieved=(UUID,) / selected=UUID / learned=None。Critic は初回・再利用とも success。
Generator 呼び出し1回、保存1回、Critic 呼び出し2回を実装への spy で確認しました。
リポジトリの初期6 Skill は変更していません。

## ServiceGraph

| id | protocol | 登録 base_url |
| --- | --- | --- |
| overpass | overpass | https://overpass.yuiseki.net |
| nominatim | nominatim | https://nominatim.yuiseki.net |
| valhalla | valhalla | https://valhalla.yuiseki.net |
| taginfo | taginfo | https://taginfo.yuiseki.net |
| yuisekin-geosparql | sparql | http://geosparql:3030 |

GeoSPARQL は sibling repository の pinned graph を読み込んだテスト用 Fuseki originです。

## Gateway 境界

- `GET/POST /services/{service_id}/{path}?query`。登録 origin と protocol ごとの read-only API path だけを解決します。
- 任意 URL、wildcard、URL override、path traversal、mutation HTTP method、SPARQL update media type を拒否します。
- redirect は追跡せず、Location も転送しません。HTTP timeout 15秒、request body 64KiB、response 4MiB。
- Worker は isolated internal network のみ。Gateway は Worker internal + external + GeoSPARQL 専用 internal。
- GeoSPARQL origin は専用 internal のみで、SPARQL SERVICE を無効化。4公開originと GeoSPARQL の Worker直接TCP接続が失敗します。
- Worker/Gateway は host filesystem / Docker socket の mount なし。read-only data mount は GeoSPARQL origin のみです。
- 作成した container / network は finally で削除します。

```python
call_service(service_id, *, path="", params=None, body=None, content_type=None) -> str
```

`body=None` は GET、それ以外は POST。Primitive は query の地理的意味を持ちません。
Dataset と Service は同じ Intent で利用できます（Dataset は現在最大1件）。

## 生成された Skill

### taginfo_overpass

UUID: `197995cd-bbf8-45de-b9fc-745daf17f179`

Intent: OSMで火山をどう表現するかTaginfoで調べ、返答のkeyとvalueを両方使って日本の国境内の火山をOverpassで取得する。発見したタグと取得した火山の名前を回答する。

description.txt:

Taginfoサービスで火山に関連するタグを探索し、最も使用頻度の高いkey/valueペアを取得して、Overpass APIで日本の国境内にあるそのタグを持つ火山を検索し、結果として発見したタグと火山の名前を出力する。

code.py:

```python
from geo_voyager.control_primitives import call_service
import json

taginfo_resp = call_service('taginfo', path='/api/4/search/by_value', params={'query': 'volcano', 'rp': '5', 'sortname': 'count_all', 'sortorder': 'desc'})
taginfo_data = json.loads(taginfo_resp)
if not taginfo_data.get('data'):
    raise Exception("No taginfo results")
best_tag = taginfo_data['data'][0]
key = best_tag['key']
value = best_tag['value']
print(f"Discovered tag: {key}={value}")

nominatim_resp = call_service('nominatim', path='/search', params={'q': 'Japan', 'format': 'jsonv2', 'limit': '1'})
nominatim_data = json.loads(nominatim_resp)
if not nominatim_data:
    raise Exception("No nominatim result for Japan")
japan_osm_id = nominatim_data[0]['osm_id']
japan_osm_type = nominatim_data[0]['osm_type']
if japan_osm_type == 'relation':
    area_id = int(japan_osm_id) + 3600000000
else:
    raise Exception("Japan is not a relation")

ql = f"[out:json]; nwr[{key}=\"{value}\"](area:{area_id}); out;"
overpass_resp = call_service('overpass', path='/api/interpreter', body=ql, content_type='text/plain')
overpass_data = json.loads(overpass_resp)
elements = overpass_data.get('elements', [])
print(f"Found {len(elements)} volcanoes.")
for el in elements:
    if 'tags' and 'name' in el.get('tags', {}):
        print(el['tags']['name'])
```

初回 Critic: Taginfoでnatural=volcanoを特定し、Overpassで日本の火山を取得した結果、タグと火山名が回答されているため。

再利用 Critic: Taginfoでnatural=volcanoを特定し、Overpassで日本の火山を取得した結果、発見したタグと火山名が回答されているため。

### nominatim

UUID: `83421c83-3030-416f-86ea-9bb3ec4df89d`

Intent: 上野駅の位置（緯度・経度）とOSM objectの種類・IDを取得する

description.txt:

nominatim サービスの /search エンドポイントを使用して上野駅の緯度・経度および OSM 物体の種別と ID を取得し、結果を出力する。

code.py:

```python
from geo_voyager.control_primitives import call_service
import json

resp = call_service("nominatim", path="/search", params={"q": "上野駅", "format": "jsonv2", "limit": "1"})
data = json.loads(resp)
if not data:
    raise Exception("No results found")
item = data[0]
print(f"緯度: {item['lat']}")
print(f"経度: {item['lon']}")
print(f"OSM種別: {item['osm_type']}")
print(f"OSM ID: {item['osm_id']}")
```

初回 Critic: 上野駅の緯度・経度とOSM objectの種類・IDがすべて出力されているため。

再利用 Critic: 上野駅の緯度・経度とOSM objectの種類・IDがすべて出力されているため。

### geosparql

UUID: `7abbab9d-a91c-42b7-89dd-a711543625de`

Intent: YuisekinGeoSPARQLのpinned graphで台東区に境界が接する区の日本語名を求める。

description.txt:

YuisekinGeoSPARQLで台東区の日本語名を取得し、geo:sfTouches関係を用いて境界が接する区の日本語名を出力する。

code.py:

```python
from geo_voyager.control_primitives import call_service
import json

# 1. 台東区のURIを取得
query1 = """
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX gs: <https://yuiseki.net/geosparql/schema#>

SELECT ?feature ?label WHERE {
  ?feature a gs:Ward .
  ?feature rdfs:label ?label .
  FILTER(?label = "台東区"@ja)
}
"""
res1 = call_service("yuisekin-geosparql", path="/geo/sparql", params={"query": query1})
data1 = json.loads(res1)
if not data1.get('results', {}).get('bindings'):
    raise Exception("台東区が見つかりません")
tokusyo_uri = data1['results']['bindings'][0]['feature']['value']

# 2. 境界が接する区を取得
query2 = f"""
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX gs: <https://yuiseki.net/geosparql/schema#>

SELECT ?adjacent ?adj_label WHERE {{
  <{tokusyo_uri}> geo:sfTouches ?adjacent .
  ?adjacent rdfs:label ?adj_label .
  FILTER(LANG(?adj_label) = "ja")
}}
"""
res2 = call_service("yuisekin-geosparql", path="/geo/sparql", params={"query": query2})
data2 = json.loads(res2)
bindings = data2.get('results', {}).get('bindings', [])
if not bindings:
    raise Exception("境界が接する区が見つかりません")

for b in bindings:
    print(b['adj_label']['value'])
```

初回 Critic: 台東区に境界が接する区の日本語名が5つ列挙されており、Intentの要求を満たしているため。

再利用 Critic: 台東区に境界が接する区の日本語名が5つ列挙されており、Intentの要求を満たしている。

## pinned graph の由来

| TTL | Dataset revision | SHA-256 |
| --- | --- | --- |
| tokyo23.ttl | `yuiseki/osm-tokyo23-src-2026-08@e60e017f6a77fa81014b11ca953ae0b2b177edaf` | `c6cfe6d2d68d0513e81317f40769d6df9eca2f84947c25f5e3cde1b52e289d4c` |
| tokyo23-poi.ttl | `yuiseki/osm-tokyo23-src-2026-08@e60e017f6a77fa81014b11ca953ae0b2b177edaf` | `3ea1dc9e8506ff19fb93e79beea8f5c806e699663846384b101fad245103fe5a` |
| ne-admin0.ttl | `yuiseki/ne-admin0-10m@d1d37a11992230933819fdb3f363dc919bb547a5` | `597fdd90c230c03f918f019cea0e8938872c387be5decdd536c396d6ef9ceb12` |
| ne-admin1.ttl | `yuiseki/ne-admin0-10m@d1d37a11992230933819fdb3f363dc919bb547a5` | `ba4ed3a41539664e2824976b21dddf0118908db7625961d8fecd817757231f4d` |

manifest の4ファイルを SHA-256 検証してから Fuseki に読み込みました。既存 repository は変更していません。

## テストと生成設定

- unit: 305 passed（通常 pytest、実 HTTP / Docker / LLM は mock）。
- 新規 service-learning integration: 4 passed in 90.73s。
- Worker image build / offline DuckDB extension LOAD + service isolation: 2 passed。
- 既存 integration: 17 passed in 309.61s。新規4件と合わせ、全21件成功（2バッチ実行）。

Service-only generation は温度0.2、推論有効、推論予算1024、出力上限3072。
先頭の `説明:（改行）` のみ assistant prefill し、本文・コードは自由生成です。
JSON Schema / grammar / response_format は指定していません。Critic / Selector は温度0です。
既存 Dataset generation の設定は変更していません。モデルや k8s resource の変更はありません。

開発中は不正なQL/SPARQL、形式違反、誤った国境のbbox利用、Criticの誤判定、
無制限生成によるLLM context overflowを観測しました。
API/schema metadata・生成指示・リクエスト上限を修正して再検証しています。
不正形式・実行失敗・Critic failure は保存しません。実行時の retry / self-repair は追加していません。
成功した3ケースは最終設定でまとめて通過しました。自由生成の毎回の成功を保証する検証ではありません。

再実行コマンドと環境設定は [README](../README.md#explicit-service-learning-integration) を参照してください。
生成設定の API は [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
と [reasoning budget 実装](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp) に基づきます。
