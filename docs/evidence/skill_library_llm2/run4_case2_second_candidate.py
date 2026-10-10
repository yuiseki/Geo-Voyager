from geo_voyager.control_primitives import call_service
import json

def query_adjacent_wards(target_label: str) -> list[dict]:
    q1 = """
    PREFIX gs: <https://yuiseki.net/geosparql/schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?uri ?relation
    WHERE {
      ?uri a gs:Ward .
      ?uri rdfs:label ?label .
      FILTER(LANG(?label) = "ja" && STR(?label) = "台東区")
      ?uri gs:osmRelation ?relation .
    }
    LIMIT 1
    """
    res1 = call_service("yuisekin-geosparql", path="/geo/sparql", body=q1, content_type="application/sparql-query")
    data1 = json.loads(res1)
    bindings1 = data1["results"]["bindings"]
    assert len(bindings1) == 1, "Target ward not found"
    target_uri = bindings1[0]["uri"]["value"]
    target_rel = bindings1[0]["relation"]["value"]
    target_rel_id = target_rel.rsplit("/", 1)[-1]
    assert str(target_rel_id).isdigit(), f"Target relation ID is not a digit: {target_rel_id}"
    
    q2 = f"""
    PREFIX gs: <https://yuiseki.net/geosparql/schema#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?label ?relation
    WHERE {{
      <{target_uri}> geo:sfTouches ?adj .
      ?adj a gs:Ward .
      ?adj rdfs:label ?label .
      FILTER(LANG(?label) = "ja")
      ?adj gs:osmRelation ?relation .
    }}
    ORDER BY ?label
    """
    res2 = call_service("yuisekin-geosparql", path="/geo/sparql", body=q2, content_type="application/sparql-query")
    data2 = json.loads(res2)
    bindings2 = data2["results"]["bindings"]
    assert len(bindings2) > 0, "No adjacent wards found"
    
    results = []
    for b in bindings2:
        label = b["label"]["value"]
        rel = b["relation"]["value"]
        rel_id = rel.rsplit("/", 1)[-1]
        assert str(rel_id).isdigit(), f"Relation ID {rel} is not a digit"
        results.append({"name": label, "relation_id": int(rel_id)})
    return results

print(json.dumps(query_adjacent_wards("台東区"), ensure_ascii=False))