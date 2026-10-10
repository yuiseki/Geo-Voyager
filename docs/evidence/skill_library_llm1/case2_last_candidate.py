from geo_voyager.control_primitives import call_service
import json

def query_touching_wards(target_label: str, service_id: str) -> None:
    """
    指定された区の名前(target_label)でgs:Wardを検索し、
    その区(gs:osmRelation)と境界が接する(gs:sfTouches)他の区の
    日本語名とosmRelation IDを取得してJSONとして出力する。
    """
    # 1. 対象区の relation ID 取得
    query1 = f"""
    PREFIX gs: <https://yuiseki.net/geosparql/schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label ?relation WHERE {{
        ?ward a gs:Ward .
        ?ward rdfs:label ?label .
        FILTER(LANG(?label) = "ja")
        FILTER(STR(?label) = "{target_label}")
        ?ward gs:osmRelation ?relation .
    }}
    """
    res1 = call_service(service_id, path="/geo/sparql", body=query1, content_type="application/sparql-query")
    data1 = json.loads(res1)
    bindings1 = data1["results"]["bindings"]
    if not bindings1:
        raise ValueError("Target ward not found")
    
    target_relation = bindings1[0]["relation"]["value"]
    # relation ID は URI の末尾の数値
    target_id = target_relation.rsplit("/", 1)[-1]
    assert str(target_id).isdigit(), f"Invalid relation ID: {target_id}"

    # 2. 境界が接する区の検索
    # ?other が対象区に接し、?other の relation が ?rel に束縛される
    query2 = f"""
    PREFIX gs: <https://yuiseki.net/geosparql/schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?other_label ?rel WHERE {{
        ?target a gs:Ward .
        ?target gs:osmRelation <{target_relation}> .
        ?other a gs:Ward .
        ?other rdfs:label ?other_label .
        FILTER(LANG(?other_label) = "ja")
        ?other geo:sfTouches ?target .
        ?other gs:osmRelation ?rel .
    }}
    ORDER BY ?other_label
    """
    res2 = call_service(service_id, path="/geo/sparql", body=query2, content_type="application/sparql-query")
    data2 = json.loads(res2)
    bindings2 = data2["results"]["bindings"]
    
    if not bindings2:
        raise ValueError("No touching wards found")

    results = []
    for b in bindings2:
        other_label = b["other_label"]["value"]
        rel_uri = b["rel"]["value"]
        rel_id = rel_uri.rsplit("/", 1)[-1]
        assert str(rel_id).isdigit(), f"Invalid relation ID: {rel_id}"
        results.append({"name": other_label, "relation_id": int(rel_id)})

    print(json.dumps(results, ensure_ascii=False))

# Intent 実行
# 対象は「台東区」
query_touching_wards("台東区", "yuisekin-geosparql")