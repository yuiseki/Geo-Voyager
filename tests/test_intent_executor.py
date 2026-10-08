from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from geo_voyager.critique import Critique
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_candidate import SkillCandidate, promote


def setup_executor():
    components = [Mock() for _ in range(6)]
    return IntentExecutor(*components), components


@pytest.mark.parametrize('selected,existing_success,candidate_success', [
    (True, True, True),
    (True, False, True),
    (True, False, False),
    (False, False, True),
    (False, False, False),
])
def test_validation_and_learning_order(tmp_path, selected, existing_success, candidate_success):
    executor, (retriever, selector, worker, generator, critic, _) = setup_executor()
    library = SkillLibrary(tmp_path)
    executor.skill_library = Mock(wraps=library)
    intent = Intent('東京都23区の平均人口を求める', ('yuiseki/jp-admin-2026-09',))
    skills = [Skill(uuid4(), '人口合計', 'code'), Skill(uuid4(), '人口最大', 'code2')]
    retriever.retrieve.return_value = skills
    selector.select.return_value = skills[1] if selected else None
    existing = [Observation('既存結果')]
    generated = [Observation('平均人口')]
    worker.execute_skill.return_value = existing
    worker.execute_candidate.return_value = generated
    candidate = SkillCandidate('print("平均人口")', '平均人口を算出')
    generator.generate.return_value = candidate
    existing_critique = Critique(existing_success, '既存結果の適合性')
    candidate_critique = Critique(candidate_success, '生成結果の適合性')
    critic.check.side_effect = ([existing_critique, candidate_critique] if selected else [candidate_critique])
    events = Mock()
    for name, component in [('retriever', retriever), ('selector', selector), ('worker', worker),
                            ('generator', generator), ('critic', critic), ('library', executor.skill_library)]:
        events.attach_mock(component, name)
    with patch('geo_voyager.intent_executor.promote', wraps=promote) as promotion:
        events.attach_mock(promotion, 'promote')
        result = executor.execute(intent, k=4)
        assert result.retrieved_skill_ids == tuple(skill.id for skill in skills)
        assert result.selected_skill_id == (skills[1].id if selected else None)
        assert result.selected_skill_critique == (existing_critique if selected else None)
        expected_events = ['retriever.retrieve', 'selector.select']
        if selected:
            expected_events += ['worker.execute_skill', 'critic.check']
            worker.execute_skill.assert_called_once_with(intent, skills[1])
        if selected and existing_success:
            assert result.observations == existing
            assert result.critique == existing_critique
            assert result.learned_skill_id is None
            generator.generate.assert_not_called()
            worker.execute_candidate.assert_not_called()
            promotion.assert_not_called()
            executor.skill_library.add.assert_not_called()
            retriever.upsert.assert_not_called()
            assert library.all() == []
        else:
            expected_events += ['generator.generate', 'worker.execute_candidate', 'critic.check']
            generator.generate.assert_called_once_with(intent)
            worker.execute_candidate.assert_called_once_with(intent, candidate)
            assert result.observations == generated
            assert result.critique == candidate_critique
            if candidate_success:
                expected_events += ['promote', 'library.add', 'retriever.upsert']
                promotion.assert_called_once_with(candidate)
                executor.skill_library.add.assert_called_once()
                retriever.upsert.assert_called_once_with(executor.skill_library.add.call_args.args[0])
                saved = library.get(result.learned_skill_id)
                assert saved.code == candidate.code and saved.description == candidate.description
                assert library.all() == [saved]
            else:
                assert result.learned_skill_id is None
                promotion.assert_not_called()
                executor.skill_library.add.assert_not_called()
                retriever.upsert.assert_not_called()
                assert list(tmp_path.iterdir()) == []
        assert [call[0] for call in events.mock_calls] == expected_events
        assert critic.check.call_args.args == (intent, result.observations)


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
    result = IntentExecution([], (), None, None, Critique(False, "未実行"), None)
    with pytest.raises(FrozenInstanceError):
        result.learned_skill_id = uuid4()


def test_service_only_intent_uses_existing_validation_flow():
    executor, (retriever, selector, worker, generator, critic, library) = setup_executor()
    skill = Skill(uuid4(), '地名検索', 'code')
    retriever.retrieve.return_value = [skill]
    selector.select.return_value = skill
    observations = [Observation('位置とOSM object')]
    worker.execute_skill.return_value = observations
    critic.check.return_value = Critique(True, '要求に回答した')
    intent = Intent('地名を検索する', service_ids=('nominatim',))
    result = executor.execute(intent)
    assert result.observations == observations and result.critique.success
    generator.generate.assert_not_called()
    library.add.assert_not_called()
