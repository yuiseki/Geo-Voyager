from unittest.mock import Mock

import pytest

from geo_voyager.target_ref import TargetRef
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

VALID = '''説明:
行政区域から人口最小の区域を求める
---
コード:
```python
from geo_voyager.control_primitives import connect_duckdb, load_admin_units


def least_populous():
    """Find it."""
    return "result"
```'''


@pytest.mark.parametrize('reply', [VALID, VALID.replace('---\nコード:\n', '---\n\nコード:\n\n')])
def test_generator_passes_intent_and_primitive_contracts_and_parses_candidate(reply):
    client = Mock()
    client.generate.return_value = reply
    intent = Intent('東京都23区で人口が最も少ない区と人口を求める', ('yuiseki/jp-admin-2026-09',))
    candidate = SkillCandidateGenerator(client).generate(intent)
    assert candidate == SkillCandidate(
        code=('from geo_voyager.control_primitives import connect_duckdb, load_admin_units\n\n\n'
              'def least_populous():\n    \"\"\"Find it.\"\"\"\n    return "result"'),
        description='行政区域から人口最小の区域を求める',
    )
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    for text in (intent.text, intent.dataset_ids[0], 'connect_duckdb()',
                 'dataset_url(dataset_id)', 'load_admin_units(dataset_id, connection, area=None)',
                 'load_admin_units(dataset_id, connection, area="東京都23区")',
                 '外部URLを直接使わない', 'return で返す', 'dataset_id は実行環境から関数の引数として与えられる',
                 '再利用可能', 'load_stations(dataset_id, connection)',
                 'latitude', 'longitude', 'aggregate(expression)', 'avg(population)',
                 'fetchone()[0]',
                 'from geo_voyager.control_primitives import connect_duckdb, load_admin_units',
                 'pandas DataFrame ではない', 'order(expression)', 'fetchone()', 'dataset_id = ... という代入を書かない', '選択・集計の意味が分かるキー', 'トップレベルには import と', 'Primitive 名を変更・推測しない', 'with 行はこの形のまま使う', '1行目は必ず「説明:」だけ', '説明本文は2行目から', '計画:'):
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
    assert 'Return discovered keys/values' in prompt


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
    assert '説明本文は2行目から' in client.generate.call_args.args[0]


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


def test_service_candidate_emits_machine_readable_output_and_rejects_missing_required_fields():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('一覧を取得', service_ids=('yuisekin-geosparql',)))
    prompt = client.generate.call_args.args[0]
    assert '戻り値は JSON にできる値' in prompt
    assert 'N/A' in prompt and '必須' in prompt
    assert 'geo:osmRelation ではない' in prompt


def test_service_contract_prefers_simple_runtime_uri_and_resolves_the_target_by_name():
    client = Mock(); client.generate.return_value = VALID
    intent = Intent('港区の件数を測定', service_ids=('yuisekin-geosparql',), target=TargetRef('港区'),
                    previous_observations=(__import__('geo_voyager.observation', fromlist=['Observation']).Observation('[]'),))
    SkillCandidateGenerator(client).generate(intent)
    prompt = client.generate.call_args.args[0]
    assert 'intent_target' in prompt and '([0-9]+)番' not in prompt
    assert 'SPARQL の REPLACE' in prompt


def test_service_system_contract_resolves_the_named_target_at_runtime():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('港区の件数を測定', service_ids=('overpass',), target=TargetRef('港区')))
    system = client.generate.call_args.kwargs['system_prompt']
    assert 'intent_target' in system and 'ordinal' not in system
    assert 're.search' not in system and '([0-9]+)番' not in system


def test_overpass_contract_requires_existing_area_before_measuring():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('対象の地物件数を取得', service_ids=('overpass',)))
    prompt = client.generate.call_args.args[0]
    assert 'Every relation ID' in prompt and 'area exists' in prompt


def test_final_generation_instruction_distinguishes_parameter_from_fixed_scope():
    client = Mock(); client.generate.return_value = VALID
    from geo_voyager.observation import Observation
    SkillCandidateGenerator(client).generate(Intent('港区の件数を測定', service_ids=('overpass',), target=TargetRef('港区'),
                                                    previous_observations=(Observation('[]'),)))
    tail = client.generate.call_args.args[0].split('Intent:')[-1]
    assert '対象は実行時変数 intent_target' in tail and '実行時に指定された対象' in tail


def test_target_context_example_matches_by_name_and_never_by_position():
    from geo_voyager.observation import Observation
    client = Mock(); client.generate.return_value = VALID
    intent = Intent('港区の件数を測定', service_ids=('overpass',), target=TargetRef('港区'), previous_observations=(Observation('[]'),))
    SkillCandidateGenerator(client).generate(intent)
    prompt = client.generate.call_args.args[0]
    assert 't.get("name") == intent_target["name"]' in prompt
    assert 're.search' not in prompt and '添字' not in prompt.split('Intent:')[-1]


def test_a_target_without_prior_observations_still_reads_its_name_at_runtime():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('港区の ID を取得', service_ids=('yuisekin-geosparql',), target=TargetRef('港区')))
    prompt = client.generate.call_args.args[0]
    assert 'intent_target["name"]' in prompt and 'previous_observations' not in prompt.split('Intent:')[-1]


def test_positive_service_contracts_distinguish_area_filter_and_external_relation():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('境界から件数を調べる', service_ids=('overpass','yuisekin-geosparql')))
    prompt = client.generate.call_args.args[0]
    assert 'nwr["<key>"="<value>"](area:<area_id>);out count;' in prompt
    assert '?ward gs:osmRelation ?relation' in prompt and 'isdigit()' in prompt


def test_standalone_service_generation_does_not_mention_a_target():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('地名から位置を調べる', service_ids=('nominatim',)))
    assert 'intent_target' not in client.generate.call_args.args[0]


def test_prior_tag_context_without_a_target_does_not_ask_for_target_resolution():
    from geo_voyager.observation import Observation
    client = Mock(); client.generate.return_value = VALID
    intent = Intent('対象集合を取得する', service_ids=('yuisekin-geosparql',), previous_observations=(Observation('{"key":"example"}'),))
    SkillCandidateGenerator(client).generate(intent)
    assert 'intent_target' not in client.generate.call_args.args[0]


def test_local_aggregation_reads_all_outputs_and_requires_metric_fields():
    from geo_voyager.observation import Observation
    client = Mock(); client.generate.return_value = VALID
    intent = Intent('前段測定の最大値を求める', requires_context=True, previous_observations=(Observation('[{"name":"対象"}]'), Observation('{"name":"対象","count":2}')))
    SkillCandidateGenerator(client).generate(intent)
    prompt = client.generate.call_args.args[0]
    assert 'decoded = [json.loads(text) for text in previous_observations]' in prompt
    assert '0 で代用しない' in prompt


def test_service_metadata_exposes_actual_json_response_envelopes():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(Intent('API結果を調べる', service_ids=('taginfo','yuisekin-geosparql')))
    prompt = client.generate.call_args.args[0]
    assert 'payload["data"]' in prompt
    assert 'payload["results"]["bindings"]' in prompt
    assert 'row["<variable>"]["value"]' in prompt


def _reply(code):
    return f'説明:\n実行時に指定された対象の件数を取得する\n---\nコード:\n```python\n{code}\n```'


GUESSED = ('def area_of(intent_target):\n    \"\"\"The Overpass area of a target.\"\"\"\n    if intent_target["id_type"] == "relation":\n'
           '        return int(intent_target["id_value"]) + 3600000000\n    return None')
PLAIN = 'def area_of(intent_target):\n    \"\"\"The Overpass area of a target.\"\"\"\n    return int(intent_target["id_value"]) + 3600000000'
RESOLVED = Intent('渋谷区の amenity=cafe の地物数を求める', service_ids=('overpass',), target=TargetRef('渋谷区', 'relation_id', '1759477'))


def test_the_overpass_prompt_says_how_the_area_id_is_made_from_the_target_id():
    client = Mock(); client.generate.return_value = _reply(PLAIN)
    SkillCandidateGenerator(client).generate(RESOLVED)
    prompt = client.generate.call_args.args[0]
    assert '3600000000' in prompt and 'intent_target["id_value"]' in prompt and 'id_type を固定の文字列と比べない' in prompt


def test_code_that_compares_the_id_type_with_a_fixed_string_is_generated_again():
    client = Mock(); client.generate.side_effect = [_reply(GUESSED), _reply(PLAIN)]
    candidate = SkillCandidateGenerator(client).generate(RESOLVED)
    assert candidate.code == PLAIN and client.generate.call_count == 2
    assert "id_type == 'relation'" in client.generate.call_args_list[1].args[0] or 'id_type' in client.generate.call_args_list[1].args[0]


def test_code_that_keeps_comparing_the_id_type_is_refused_not_passed_on():
    client = Mock(); client.generate.return_value = _reply(GUESSED)
    with pytest.raises(ValueError, match='Candidate.*id_type'):
        SkillCandidateGenerator(client).generate(RESOLVED)
    assert client.generate.call_count == 3          # the first reply and two more


def test_an_intent_without_a_resolved_target_is_not_checked():
    client = Mock(); client.generate.return_value = _reply(GUESSED)
    SkillCandidateGenerator(client).generate(Intent('渋谷区の件数を求める', service_ids=('overpass',), target=TargetRef('渋谷区')))
    assert client.generate.call_count == 1


LOCAL = Intent('渋谷区と新宿区の件数を比べ、どちらが多いかを示す', service_ids=('overpass',), requires_context=True,
               previous_observations=(Observation('{"name": "渋谷区", "count": 459}'), Observation('{"name": "新宿区", "count": 343}')))
DEFAULTED = ('import json\n\n\ndef first_count(previous_observations):\n    \"\"\"Count of the first.\"\"\"\n'
             '    d = [json.loads(t) for t in previous_observations]\n    return d[0].get("count", 0)')
BY_NAME = ('import json\n\n\ndef count_of(previous_observations, name="渋谷区"):\n    \"\"\"Count of the named object.\"\"\"\n'
           '    d = [json.loads(t) for t in previous_observations]\n    m = [o for o in d if o["name"] == name]\n    assert m\n'
           '    return m[0]["count"]')


def test_the_local_aggregation_prompt_forbids_picking_by_position_and_defaulting():
    client = Mock(); client.generate.return_value = _reply(BY_NAME)
    SkillCandidateGenerator(client).generate(LOCAL)
    prompt = client.generate.call_args.args[0]
    assert '番号や位置で選ばない' in prompt and '名前と ID で選ぶ' in prompt


def test_local_aggregation_code_with_a_defaulted_measurement_or_a_position_is_generated_again():
    client = Mock(); client.generate.side_effect = [_reply(DEFAULTED), _reply(BY_NAME)]
    candidate = SkillCandidateGenerator(client).generate(LOCAL)
    assert candidate.code == BY_NAME and client.generate.call_count == 2
    note = client.generate.call_args_list[1].args[0]
    assert "d[0]" in note and "get('count', 0)" in note


def test_local_aggregation_code_that_keeps_breaking_the_contract_is_refused():
    client = Mock(); client.generate.return_value = _reply(DEFAULTED)
    with pytest.raises(ValueError, match='Candidate.*local aggregation'):
        SkillCandidateGenerator(client).generate(LOCAL)
    assert client.generate.call_count == 3


def test_a_step_that_is_not_a_local_aggregation_is_not_checked_for_it():
    client = Mock(); client.generate.return_value = _reply(DEFAULTED)
    SkillCandidateGenerator(client).generate(Intent('件数を求める', service_ids=('overpass',),
                                                    previous_observations=(Observation('{"count": 459}'),)))
    assert client.generate.call_count == 1


def test_one_earlier_observation_may_be_read_as_previous_observations_0():
    one = Intent('前段の件数を整形する', service_ids=('overpass',), requires_context=True,
                 previous_observations=(Observation('{"name": "渋谷区", "count": 459}'),))
    client = Mock(); client.generate.return_value = _reply('import json\n\n\ndef count_of(previous_observations):\n    \"\"\"Count.\"\"\"\n    return json.loads(previous_observations[0])["count"]')
    SkillCandidateGenerator(client).generate(one)
    assert client.generate.call_count == 1


# ---- the harness is explained first: the life of a function, how values reach it, and an example

def _prompt_for(intent, skills=()):
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(intent, skills)
    return client.generate.call_args.args[0]


def test_the_prompt_opens_with_how_the_environment_works():
    prompt = _prompt_for(RESOLVED)
    head = prompt[:prompt.index('利用可能な登録済み Service')]
    assert head.startswith('この環境の仕組み')
    for part in ('Skill として保存', '後の別の Intent', '引数を変えて呼', '既定値', 'この Intent では intent_target だけ', '関数名や関数の中に書き込まない'):
        assert part in head, part


def test_the_environment_says_which_runtime_values_this_intent_has():
    assert 'この Intent では intent_target だけ' in _prompt_for(RESOLVED)
    assert 'この Intent では dataset_id だけ' in _prompt_for(Intent('人口が最も多い区', ('yuiseki/jp-admin-2026-09',)))
    assert '値を何も渡さない' in _prompt_for(Intent('cuisine の値を並べる', service_ids=('taginfo',)))


def test_the_saved_skills_come_after_the_explanation_and_before_the_services():
    from geo_voyager.skill_function import parse_skill
    skill = parse_skill('def count_tag_in_area(intent_target, key="amenity", value="cafe"):\n    """Count."""\n    return 1')
    prompt = _prompt_for(RESOLVED, [skill])
    assert prompt.index('この環境の仕組み') < prompt.index('# Skill: count_tag_in_area') < prompt.index('利用可能な登録済み Service')


def test_tag_discovery_does_not_forbid_writing_the_condition_the_intent_gives_as_a_default():
    prompt = _prompt_for(Intent('cuisine キーの値を並べる', service_ids=('taginfo',)))
    assert 'Intent が条件を明示しているときは、その値を引数の既定値に書いてよい' in prompt


def test_a_function_named_after_the_place_is_generated_again():
    named = 'def count_hotels_in_taito(intent_target, key="tourism", value="hotel"):\n    """Count."""\n    return 1'
    plain = 'def count_tag_in_area(intent_target, key="tourism", value="hotel"):\n    """Count."""\n    return 1'
    client = Mock(); client.generate.side_effect = [_reply(named), _reply(plain)]
    intent = Intent('台東区の tourism=hotel の地物数', service_ids=('overpass',), target=TargetRef('台東区', 'relation_id', '1758888'))
    assert SkillCandidateGenerator(client).generate(intent).code == plain
    assert 'taito' in client.generate.call_args_list[1].args[0]


# ---- a shown Skill that does the same service calls is pointed out once (Voyager: do not reinvent it)

LOOKUP_SKILL = ('from geo_voyager.control_primitives import call_service\n\n\n'
                'def get_relation_id(intent_target):\n    """Look the target up in Nominatim."""\n'
                '    return call_service("nominatim", path="/search", params={"q": intent_target["name"]})')
REWRITE = ('from geo_voyager.control_primitives import call_service\n\n\n'
           'def get_osm_relation_id_for_target(intent_target):\n    """Look the target up."""\n'
           '    return call_service("nominatim", path="/search", params={"q": intent_target["name"], "limit": "1"})')
REUSE = 'def lookup_target(intent_target):\n    """Look the target up."""\n    return get_relation_id(intent_target)'
NAME_ONLY = Intent('渋谷区の relation ID', service_ids=('nominatim',), target=TargetRef('渋谷区'))


def test_a_rewrite_of_a_shown_skill_is_pointed_out_and_written_again_once():
    from geo_voyager.skill_function import parse_skill
    client = Mock(); client.generate.side_effect = [_reply(REWRITE), _reply(REUSE)]
    candidate = SkillCandidateGenerator(client).generate(NAME_ONLY, [parse_skill(LOOKUP_SKILL)])
    assert candidate.code == REUSE and client.generate.call_count == 2
    note = client.generate.call_args_list[1].args[0]
    assert 'get_relation_id' in note and 'nominatim /search' in note


def test_a_second_rewrite_is_accepted_rather_than_refused():
    from geo_voyager.skill_function import parse_skill
    client = Mock(); client.generate.side_effect = [_reply(REWRITE), _reply(REWRITE)]
    candidate = SkillCandidateGenerator(client).generate(NAME_ONLY, [parse_skill(LOOKUP_SKILL)])
    assert candidate.code == REWRITE and client.generate.call_count == 2


def test_code_that_uses_other_services_than_the_shown_skill_is_not_pointed_out():
    from geo_voyager.skill_function import parse_skill
    other = ('def count(intent_target):\n    """Count."""\n'
             '    return call_service("overpass", path="/api/interpreter", body="x")')
    client = Mock(); client.generate.return_value = _reply(other)
    SkillCandidateGenerator(client).generate(NAME_ONLY, [parse_skill(LOOKUP_SKILL)])
    assert client.generate.call_count == 1


def test_a_function_with_the_name_of_a_shown_skill_but_another_body_is_asked_to_take_another_name():
    from geo_voyager.skill_function import parse_skill
    seed = parse_skill('def count_tag_in_area(intent_target, key, value):\n    """Count."""\n    return 1')
    redefined = 'def count_tag_in_area(intent_target, key="amenity", value="cafe"):\n    """Count cafes."""\n    return 2'
    wrapper = ('def count_cafes(intent_target, key="amenity", value="cafe"):\n    """Count cafes."""\n'
               '    return count_tag_in_area(intent_target, key, value)')
    client = Mock(); client.generate.side_effect = [_reply(redefined), _reply(wrapper)]
    assert SkillCandidateGenerator(client).generate(RESOLVED, [seed]).code == wrapper
    assert '別の名前' in client.generate.call_args_list[1].args[0]


def test_contract_refuses_a_local_function_that_reads_the_target_it_is_not_given():
    from geo_voyager.skill_candidate_generator import contract_problems

    observation = Observation('{"name": "渋谷区", "relation_id": "1759477", "count": 459}')
    intent = Intent('前段の件数を比べて多い区を返す', previous_observations=(observation,), requires_context=True)
    code = ('import json\n\n'
            'def compare_counts(intent_target, previous_observations, intent_text):\n'
            '    """比べる。"""\n'
            '    rows = [json.loads(text) for text in previous_observations]\n'
            '    return [r for r in rows if r.get(intent_target["id_type"])]\n')
    problems = contract_problems(intent, code)
    assert any('intent_target' in found and 'None' in note for found, note in problems)
