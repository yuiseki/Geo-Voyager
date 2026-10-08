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
    assert sandbox.return_value.run.call_args.args[0] == f'dataset_id={dataset_id!r}\n{skill.code}'
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
