from bench.replay_critic import build_intent
from geo_voyager.target_ref import TargetRef


def test_a_recorded_intent_gives_back_its_target_from_either_form_of_the_record():
    base = {'text': 't', 'dataset_ids': [], 'service_ids': ['overpass'], 'previous_observations': [], 'requires_context': False}
    assert build_intent({**base, 'target_name': '港区'}).target == TargetRef('港区')                       # older runs: a name
    recorded = {'name': '港区', 'id_type': 'relation_id', 'id_value': '1761717'}
    assert build_intent({**base, 'target': recorded}).target == TargetRef('港区', 'relation_id', '1761717')
    assert build_intent({**base, 'target': None, 'target_name': None}).target is None
