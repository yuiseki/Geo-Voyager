from geo_voyager.observation import Observation
from geo_voyager.observation_context import describe_observations


def test_context_describes_runtime_shape_without_embedding_answers():
    result = describe_observations((Observation('[{"name":"秘密の対象", "relation_id":"1234567"}]'),))
    assert 'name' in result and 'relation_id' in result and 'list' in result
    assert '秘密の対象' not in result and '1234567' not in result


def test_non_json_context_is_identified_as_text():
    assert 'str' in describe_observations((Observation('answer is private'),))


def test_shape_does_not_invent_index_fields_inside_runtime_rows():
    result = describe_observations((Observation('[{"name":"対象"}]'),))
    assert 'json.loads(previous_observations[0])' in result
    assert '"index"' not in result
