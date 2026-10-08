from unittest.mock import Mock

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

VALID = '''説明:
行政区域から人口最小の区域を求める
---
コード:
```python
from geo_voyager.control_primitives import connect_duckdb, load_admin_units
print("result")
```'''


@pytest.mark.parametrize('reply', [VALID, VALID.replace('---\nコード:\n', '---\n\nコード:\n\n')])
def test_generator_passes_intent_and_primitive_contracts_and_parses_candidate(reply):
    client = Mock()
    client.generate.return_value = reply
    intent = Intent('東京都23区で人口が最も少ない区と人口を求める', ('yuiseki/jp-admin-2026-09',))
    candidate = SkillCandidateGenerator(client).generate(intent)
    assert candidate == SkillCandidate(
        code='from geo_voyager.control_primitives import connect_duckdb, load_admin_units\nprint("result")',
        description='行政区域から人口最小の区域を求める',
    )
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    for text in (intent.text, intent.dataset_ids[0], 'connect_duckdb()',
                 'dataset_url(dataset_id)', 'load_admin_units(dataset_id, connection, area=None)',
                 'load_admin_units(dataset_id, connection, area="東京都23区")',
                 '外部URLを直接使わない', 'stdout', 'dataset_id は実行環境から与えられる',
                 '再利用可能', 'load_stations(dataset_id, connection)',
                 'latitude', 'longitude', 'aggregate(expression)', 'avg(population)',
                 'fetchone()[0]',
                 'from geo_voyager.control_primitives import connect_duckdb, load_admin_units',
                 'pandas DataFrame ではない', 'order(expression)', 'fetchone()', 'dataset_id = ... という代入を書かない', 'stdout に選択・集計の意味', 'トップレベル', 'Primitive 名を変更・推測しない', '接続部分の import と with 行は変更せず', '返答の1行目は必ず「説明:」', '説明本文を同じ行に書かない'):
        assert text in prompt
    assert "13101" not in prompt and "13123" not in prompt


@pytest.mark.parametrize('reply', [
    '', 'print("ok")', VALID.replace('説明:', '解説:', 1),
    VALID.replace('\n---\n', '\n', 1), VALID.replace('コード:', 'Python:', 1),
    VALID.replace('```python', '```json', 1), VALID + '\n追記',
    '説明:\n\n---\nコード:\n```python\nprint("ok")\n```',
    '説明:\n説明本文\n---\nコード:\n```python\n   \n```',
])
def test_generator_rejects_invalid_or_empty_sections(reply):
    client = Mock()
    client.generate.return_value = reply
    with pytest.raises(ValueError):
        SkillCandidateGenerator(client).generate(Intent('調査', ('yuiseki/jp-admin-2026-09',)))


def test_generator_advertises_station_primitive_for_station_intent():
    client = Mock()
    client.generate.return_value = VALID
    intent = Intent('駅データの緯度の平均を求める', ('yuiseki/ekidata-jp',))
    SkillCandidateGenerator(client).generate(intent)
    prompt = client.generate.call_args.args[0]
    assert intent.text in prompt and intent.dataset_ids[0] in prompt
    assert 'load_stations(dataset_id, connection)' in prompt
    assert 'name' in prompt and 'latitude' in prompt and 'longitude' in prompt


def test_generator_exposes_registered_services_and_generic_api_without_origin_urls():
    from geo_voyager.services import load_service_graph

    client = Mock()
    client.generate.return_value = VALID
    intent = Intent('登録サービスを調べる', service_ids=tuple(service.id for service in load_service_graph().all()))
    SkillCandidateGenerator(client).generate(intent)
    prompt = client.generate.call_args.args[0]
    for service in load_service_graph().all():
        assert service.id in prompt
        assert service.description in prompt
        assert service.protocol in prompt
        assert service.base_url not in prompt
    assert 'call_service(service_id, *, path="", params=None, body=None, content_type=None)' in prompt
    assert '接続部分の import と with 行は変更せず' not in prompt
    assert 'from geo_voyager.control_primitives import call_service' in prompt
    assert 'natural=volcano' not in prompt


def test_generator_exposes_discovery_api_contract_without_tag_answer():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('タグを探索する', service_ids=('taginfo', 'overpass')))
    prompt = client.generate.call_args.args[0]
    assert '/api/4/search/by_value' in prompt
    assert 'query' in prompt and 'data' in prompt and 'count_all' in prompt
    assert 'キー・値をコードに固定しない' in prompt
    assert 'natural=volcano' not in prompt


def test_generator_exposes_language_tagged_geosparql_labels():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('隣接する区域を調べる', service_ids=('yuisekin-geosparql',)))
    prompt = client.generate.call_args.args[0]
    assert 'STR(?label)' in prompt
    assert '言語タグなしの文字列とは一致しない' in prompt


def test_generator_exposes_overpass_syntax_contract_without_specific_query():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('OSM を検索する', service_ids=('overpass',)))
    prompt = client.generate.call_args.args[0]
    assert '比較は = であり == ではない' in prompt
    assert 'area_filter = (area:<area_id>)' in prompt


def test_service_only_generator_does_not_require_dataset_execution_contract():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('タグを調べる', service_ids=('taginfo',)))
    prompt = client.generate.call_args.args[0]
    assert 'dataset_id は実行環境から与えられる' not in prompt
    assert 'params を urlencode しない' in prompt


def test_generator_exposes_geographic_service_coordinate_contracts():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地理的範囲を検索する', service_ids=('overpass', 'nominatim')))
    prompt = client.generate.call_args.args[0]
    assert 'boundingbox は south,north,west,east' in prompt
    assert 'bbox は south,west,north,east' in prompt


def test_service_calls_require_explicit_registered_endpoint_path_in_prompt():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('サービスを調べる', service_ids=('taginfo',)))
    prompt = client.generate.call_args.args[0]
    assert 'Every call_service call must explicitly supply path' in prompt


def test_generator_distinguishes_bounding_box_from_country_boundary():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('国内の地物を検索する', service_ids=('overpass', 'nominatim')))
    prompt = client.generate.call_args.args[0]
    assert 'boundingbox は国境ではない' in prompt
    assert '3600000000' in prompt


def test_service_generator_requires_explicit_primitive_import_and_discovery_output():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('タグを調べる', service_ids=('taginfo',)))
    prompt = client.generate.call_args.args[0]
    assert 'call_service is not a global' in prompt
    assert 'Print discovered keys/values' in prompt


def test_service_candidate_generation_uses_low_temperature_sampling():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('サービスを調べる', service_ids=('taginfo',)))
    kwargs = client.generate.call_args.kwargs
    assert kwargs['temperature'] == 0.2 and kwargs['enable_thinking'] is True
    assert kwargs['system_prompt'].startswith('You are a precise Python programmer')


def test_service_generation_focuses_on_intent_service_ids_and_exact_header():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('pinned graph の隣接関係を調べる', service_ids=('yuisekin-geosparql',)))
    system = client.generate.call_args.kwargs['system_prompt']
    assert 'Use only the Service ids declared by the Intent' in system
    assert 'First line must be exactly 説明:' in system


def test_service_prompt_contains_only_declared_service_metadata():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('pinned graph の topology を調べる', service_ids=('yuisekin-geosparql',)))
    prompt = client.generate.call_args.args[0]
    assert 'id: yuisekin-geosparql' in prompt
    assert 'id: overpass' not in prompt and 'id: nominatim' not in prompt


def test_service_generator_shows_multiline_layout_and_explicit_sparql_prefix_contract():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('pinned graph を問い合わせる', service_ids=('yuisekin-geosparql',)))
    assert '説明:\n' in client.generate.call_args.kwargs['system_prompt']
    assert '各クエリで PREFIX を明示する' in client.generate.call_args.args[0]


def test_geosparql_contract_requires_resource_identity_discovery():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地理オブジェクトの隣接関係を調べる', service_ids=('yuisekin-geosparql',)))
    assert '個体URIを推測しない' in client.generate.call_args.args[0]


def test_service_output_contract_forbids_inline_description():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地理オブジェクトを調べる', service_ids=('yuisekin-geosparql',)))
    assert '説明本文を同じ行に書かない' in client.generate.call_args.args[0]


def test_overpass_contract_requires_json_output_directive():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('タグを使って調査する', service_ids=('overpass',)))
    assert 'JSON を受け取るには QL の先頭に [out:json]; が必須' in client.generate.call_args.args[0]


def test_service_candidate_generation_is_bounded_per_request():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地名を取得する', service_ids=('nominatim',)))
    kwargs = client.generate.call_args.kwargs
    assert kwargs['max_tokens'] == 3072 and kwargs['reasoning_budget_tokens'] == 1024


def test_service_description_preserves_scope_for_later_selection():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('台東区に接する区名を調べる', service_ids=('yuisekin-geosparql',)))
    assert 'description に対象・使用サービス・出力内容を含める' in client.generate.call_args.args[0]


def test_service_generation_prefills_only_the_description_label():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地名を取得する', service_ids=('nominatim',)))
    assert client.generate.call_args.kwargs['assistant_prefix'] == '説明:\n'


def test_overpass_area_identity_contract_requires_integer_addition():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('国境内で調べる', service_ids=('overpass',)))
    prompt = client.generate.call_args.args[0]
    assert 'int(osm_id) + 3600000000' in prompt
    assert '文字列連結や乗算ではない' in prompt


def test_geosparql_label_contract_requires_binding_before_filtering():
    client = Mock()
    client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('名前から区域を調べる', service_ids=('yuisekin-geosparql',)))
    assert 'rdfs:label のトリプルでラベル変数を束縛してから FILTER' in client.generate.call_args.args[0]
