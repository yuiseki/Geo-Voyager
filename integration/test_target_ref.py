"""Focused, deterministic check of the stable-id-first target, in the real Docker sandbox through the real Worker.

No model and no service is involved. The code is the connection example the Generator shows for a target with an id,
so what runs here is the contract the Generator asks the model to follow.
"""
import json

import pytest

from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_history import GoalHistory, HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.critique import Critique
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.target_identity import discover_targets
from geo_voyager.target_ref import TargetRef
from geo_voyager.worker import Worker

BY_ID = '''import json
candidates = []
for text in previous_observations:
    value = json.loads(text)
    candidates += value if isinstance(value, list) else [value]
matches = [t for t in candidates if isinstance(t, dict) and str(t.get(intent_target["id_type"])) == intent_target["id_value"]]
assert matches, "no object has the target id"
target = matches[0]
print(json.dumps({"asked_as": intent_target["name"], "id": target[intent_target["id_type"]], "found_as": target["name"]}))'''

LOOK_UP = 'import json\nprint(json.dumps({"name": "港区, 東京都, 日本", "relation_id": 1761717}))'


def run(target, previous):
    intent = Intent('港区の件数を取得する', service_ids=('overpass',), target=target,
                    previous_observations=tuple(Observation(json.dumps(item, ensure_ascii=False)) for item in previous))
    return Worker('none').execute_candidate(intent, SkillCandidate(BY_ID, '対象の ID で前段の対象を見つける'))


def test_the_same_id_under_another_display_name_is_the_same_target():
    result = run(TargetRef('港区', 'relation_id', '1761717'), [{'name': '港区, 東京都, 日本', 'relation_id': 1761717}])
    assert not isinstance(result, ExecutionFailure), result
    assert json.loads(result[0].text) == {'asked_as': '港区', 'id': 1761717, 'found_as': '港区, 東京都, 日本'}


def test_the_same_name_with_another_id_is_refused_and_the_failure_says_what_is_missing():
    result = run(TargetRef('港区', 'relation_id', '1761717'), [{'name': '港区', 'relation_id': '3554304'}])
    assert isinstance(result, ExecutionFailure) and 'no object has the target id' in result.stderr


def test_a_list_of_targets_is_searched_by_id_in_any_order_and_under_any_names():
    listing = [{'name': '渋谷区', 'relation_id': '1759477'}, {'name': 'Minato City', 'relation_id': '1761717'}]
    for order in (listing, list(reversed(listing))):
        result = run(TargetRef('港区', 'relation_id', '1761717'), [order])
        assert json.loads(result[0].text)['found_as'] == 'Minato City'


def test_the_ref_a_first_step_found_is_the_one_the_next_step_uses():
    first = Worker('none').execute_candidate(Intent('港区を探す', service_ids=('nominatim',), target=TargetRef('港区')),
                                             SkillCandidate(LOOK_UP, '港区を探す'))
    assert not isinstance(first, ExecutionFailure), first
    history = GoalHistory()
    history.append(HistoryEntry.from_execution(
        1, Intent('港区を探す', service_ids=('nominatim',), target=TargetRef('港区')),
        IntentExecution(first, (), None, None, Critique(True, 'ok'), None), history))
    [found] = history.targets()
    assert found == TargetRef('港区, 東京都, 日本', 'relation_id', '1761717')
    # the next step is about that target, which the Planner may call by a shorter name
    next_intent = Intent('港区の件数を取得する', service_ids=('overpass',), target=TargetRef('港区', found.id_type, found.id_value),
                         previous_observations=history.observations())
    second = Worker('none').execute_candidate(next_intent, SkillCandidate(BY_ID, '対象の ID で前段の対象を見つける'))
    assert not isinstance(second, ExecutionFailure), second
    assert json.loads(second[0].text) == {'asked_as': '港区', 'id': 1761717, 'found_as': '港区, 東京都, 日本'}
