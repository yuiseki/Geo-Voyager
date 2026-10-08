from dataclasses import FrozenInstanceError
from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.critique import Critique
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.skill import Skill
from geo_voyager.skill_candidate import SkillCandidate


def setup_executor():
    components = [Mock() for _ in range(6)]
    return IntentExecutor(*components), components


@pytest.mark.parametrize('text,dataset_id', [
    ('東京都23区で人口が最も多い区と人口を求める', 'yuiseki/jp-admin-2026-09'),
    ('駅データに収録されている最北端の駅を求める', 'yuiseki/ekidata-jp'),
])
def test_known_skill_is_reused_in_order_without_generator_or_save(text, dataset_id):
    executor, (retriever, selector, worker, generator, critic, library) = setup_executor()
    intent = Intent(text, (dataset_id,))
    skills = [Skill(uuid4(), '候補1', 'code1'), Skill(uuid4(), '候補2', 'code2')]
    retriever.retrieve.return_value = skills
    selector.select.return_value = skills[1]
    observations = [Observation('結果')]
    worker.execute_skill.return_value = observations
    events = Mock()
    for name, component in [('retriever', retriever), ('selector', selector), ('worker', worker)]:
        events.attach_mock(component, name)
    result = executor.execute(intent, k=4)
    assert isinstance(result, IntentExecution)
    assert result.observations == observations
    assert result.retrieved_skill_ids == tuple(skill.id for skill in skills)
    assert result.selected_skill_id == skills[1].id
    assert result.learned_skill_id is None
    assert result.critique is None
    assert [call[0] for call in events.mock_calls] == ['retriever.retrieve', 'selector.select', 'worker.execute_skill']
    retriever.retrieve.assert_called_once_with(intent, 4)
    selector.select.assert_called_once_with(intent, skills)
    worker.execute_skill.assert_called_once_with(intent, skills[1])
    worker.execute_candidate.assert_not_called()
    generator.generate.assert_not_called()
    critic.check.assert_not_called()
    library.add.assert_not_called()


@pytest.mark.parametrize('success', [True, False])
def test_unknown_skill_is_generated_and_returns_only_learned_uuid_on_success(success):
    executor, (retriever, selector, worker, generator, critic, library) = setup_executor()
    intent = Intent('東京都23区の平均人口を求める', ('yuiseki/jp-admin-2026-09',))
    retrieved = [Skill(uuid4(), '人口合計', 'code')]
    retriever.retrieve.return_value = retrieved
    selector.select.return_value = None
    candidate = SkillCandidate('print("平均人口")', '平均人口を算出')
    generator.generate.return_value = candidate
    critique = Critique(success, '結果の適合性')
    learned = Skill(uuid4(), candidate.description, candidate.code) if success else None
    observations = [Observation('平均人口の結果')]
    worker.execute_candidate.return_value = observations, critique, learned
    events = Mock()
    for name, component in [('retriever', retriever), ('selector', selector), ('generator', generator), ('worker', worker)]:
        events.attach_mock(component, name)
    result = executor.execute(intent, k=2)
    assert result.observations == observations
    assert result.retrieved_skill_ids == (retrieved[0].id,)
    assert result.selected_skill_id is None
    assert result.learned_skill_id == (learned.id if learned else None)
    assert result.critique == critique
    assert [call[0] for call in events.mock_calls] == ['retriever.retrieve', 'selector.select', 'generator.generate', 'worker.execute_candidate']
    generator.generate.assert_called_once_with(intent)
    worker.execute_candidate.assert_called_once_with(intent, candidate, critic, library)
    worker.execute_skill.assert_not_called()
    # Worker owns promotion and saving; Executor must not save a second time.
    library.add.assert_not_called()


@pytest.mark.parametrize('dataset_ids', [(), ('admin', 'stations')])
def test_unsupported_dataset_count_fails_before_retrieval(dataset_ids):
    executor, components = setup_executor()
    intent = Intent('調査', ('initial',))
    intent.dataset_ids = dataset_ids
    with pytest.raises(ValueError, match='dataset'):
        executor.execute(intent)
    for component in components:
        assert component.mock_calls == []


def test_existing_skill_execution_error_does_not_fall_back():
    executor, (retriever, selector, worker, generator, critic, library) = setup_executor()
    skill = Skill(uuid4(), '既存', 'code')
    retriever.retrieve.return_value = [skill]
    selector.select.return_value = skill
    worker.execute_skill.side_effect = RuntimeError('execution failed')
    with pytest.raises(RuntimeError):
        executor.execute(Intent('調査', ('admin',)))
    generator.generate.assert_not_called()
    worker.execute_candidate.assert_not_called()
    library.add.assert_not_called()


def test_intent_execution_is_frozen():
    result = IntentExecution([], (), None, None)
    with pytest.raises(FrozenInstanceError):
        result.learned_skill_id = uuid4()
