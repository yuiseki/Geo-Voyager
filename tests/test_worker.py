from geo_voyager.execution_failure import sandbox_program
from unittest.mock import patch
from uuid import uuid4

import pytest

from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill import Skill
from geo_voyager.worker import Worker


@pytest.mark.parametrize('dataset_id', ['yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp'])
def test_worker_executes_supplied_skill_and_injects_single_dataset_without_saving(dataset_id):
    intent = Intent('調査結果を求める', (dataset_id,))
    skill = Skill(uuid4(), '調査', 'print("skill result")')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = 'skill result\n'
        observations = Worker(network='test-internal').execute_skill(intent, skill)
    sandbox.assert_called_once_with(image='geo-voyager-worker:duckdb-1.5.6', network='test-internal')
    assert sandbox.return_value.run.call_args.args[0] == sandbox_program(f'dataset_id={dataset_id!r}\n{skill.code}')
    assert observations == [Observation('skill result')]
    import geo_voyager.worker as module
    for name in ('Critic', 'Critique', 'SkillLibrary', 'promote'):
        assert not hasattr(module, name)


@pytest.mark.parametrize('dataset_ids', [(), ('admin', 'stations')])
@pytest.mark.parametrize('candidate', [False, True])
def test_worker_rejects_zero_or_multiple_datasets_before_docker(dataset_ids, candidate):
    from unittest.mock import Mock
    from geo_voyager.skill_candidate import SkillCandidate
    intent = Intent('調査', ('initial',))
    intent.dataset_ids = dataset_ids
    critic, library = Mock(), Mock()
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        with pytest.raises(ValueError, match='dataset'):
            worker = Worker(network='test-internal')
            if candidate:
                worker.execute_candidate(intent, SkillCandidate('print(1)', '調査'))
            else:
                worker.execute_skill(intent, Skill(uuid4(), '調査', 'print(1)'))
    sandbox.assert_not_called()
    critic.check.assert_not_called()
    library.add.assert_not_called()


def test_worker_executes_service_only_code_without_injecting_dummy_dataset():
    intent = Intent('地名を検索する', service_ids=('nominatim',))
    skill = Skill(uuid4(), '地名検索', 'print("place")')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = 'place'
        assert Worker('internal').execute_skill(intent, skill) == [Observation('place')]
        assert sandbox.return_value.run.call_args.args[0] == sandbox_program(skill.code)


def test_worker_passes_prior_observations_and_current_intent_as_data():
    intent = Intent('対象を数える', service_ids=('overpass',), previous_observations=(Observation('{"target": 1}'),))
    skill = Skill(uuid4(), '測定', 'print(previous_observations)')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = 'answer'
        Worker('internal').execute_skill(intent, skill)
    code = sandbox.return_value.run.call_args.args[0]
    assert 'previous_observations=' in code and 'intent_text=' in code


def test_local_execution_requires_actual_prior_observations():
    from geo_voyager.skill_candidate import SkillCandidate
    intent = Intent('前段を集計', requires_context=True)
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        with pytest.raises(ValueError):
            Worker('internal').execute_candidate(intent, SkillCandidate('print(1)', '集計'))
        sandbox.assert_not_called()
        intent.previous_observations = (Observation('1'),)
        sandbox.return_value.run.return_value = 'result'
        assert Worker('internal').execute_candidate(intent, SkillCandidate('print(1)', '集計')) == [Observation('result')]


def test_worker_passes_the_target_identity_as_data_even_without_prior_observations():
    intent = Intent('港区の件数', service_ids=('overpass',), target_name='港区')
    skill = Skill(uuid4(), '測定', 'print(intent_target)')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = 'answer'
        Worker('internal').execute_skill(intent, skill)
    code = sandbox.return_value.run.call_args.args[0]
    assert "intent_target={'name': '港区'}" in code


def test_worker_defines_no_target_when_the_intent_names_none():
    intent = Intent('件数', service_ids=('overpass',))
    skill = Skill(uuid4(), '測定', 'print(1)')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = '1'
        Worker('internal').execute_skill(intent, skill)
    assert 'intent_target' not in sandbox.return_value.run.call_args.args[0]
