"""The Generator does not ask for one fixed output schema. Keys say what the value is. name and relation_id are for targets."""
from unittest.mock import Mock

from geo_voyager.intent import Intent
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.target_ref import TargetRef

VALID = '説明:\nS\n---\nコード:\n```python\nprint(1)\n```'


def prompt_for(intent):
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(intent)
    return client.generate.call_args.args[0]


def test_there_is_no_blanket_instruction_to_use_name_relation_id_and_count_as_keys():
    prompt = prompt_for(Intent('cuisine キーの値を使用数の多い順に並べ、上位3つを求める', service_ids=('taginfo',)))
    assert 'Use stable keys such as name, relation_id, count' not in prompt
    assert '列名は意味の分かる安定したキーを使う' not in prompt


def test_keys_are_to_say_what_the_value_is_and_a_value_is_not_to_sit_under_another_meaning():
    prompt = prompt_for(Intent('cuisine キーの値を使用数の多い順に並べ、上位3つを求める', service_ids=('taginfo',)))
    assert 'Name each key for what its value is' in prompt and 'Never put a value under a key that means something else' in prompt
    assert 'キーは、その値が何かを表す' in prompt and '固定のスキーマはない' in prompt
    assert '{"value": "pizza", "count": 132565}' in prompt


def test_name_and_id_keys_are_asked_for_only_when_the_output_is_about_targets():
    prompt = prompt_for(Intent('東京23区の一覧を取得する', service_ids=('yuisekin-geosparql',)))
    assert '出力が対象（区域・地物など、安定した ID を持つ実体）の一覧や、その対象についての測定なら' in prompt
    assert 'name と relation_id 等の ID で出力し' in prompt
    assert '対象でないもの（タグの値、件数のランキング、距離など）は、name や relation_id のキーを使わず' in prompt


def test_an_intent_about_a_target_is_told_to_put_the_targets_name_and_id_in_the_output():
    with_target = prompt_for(Intent('港区の件数を取得する', service_ids=('overpass',), target=TargetRef('港区', 'relation_id', '1761717')))
    without = prompt_for(Intent('cuisine キーの値を並べる', service_ids=('taginfo',)))
    assert 'この Intent は対象についての Intent なので、出力に対象の name と ID を含める' in with_target
    assert 'この Intent は対象についての Intent' not in without


def test_the_geosparql_id_check_is_still_there_for_that_service():
    prompt = prompt_for(Intent('区の ID を取得する', service_ids=('yuisekin-geosparql',)))
    assert 'str(relation_id).isdigit()' in prompt


def test_a_dataset_intent_has_no_fixed_schema_either():
    prompt = prompt_for(Intent('東京23区の人口の合計を求める', dataset_ids=('yuiseki/jp-admin-2026-09',)))
    assert 'stable keys such as name, relation_id' not in prompt
