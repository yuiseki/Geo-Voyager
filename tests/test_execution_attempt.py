from unittest.mock import Mock
from uuid import uuid4

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.skill import Skill
from geo_voyager.skill_candidate import SkillCandidate


def test_attempts_keep_selected_failure_original_failure_and_repaired_success():
    retriever, selector, worker, generator, critic, library, repairer = [Mock() for _ in range(7)]
    skill = Skill(uuid4(), '既存', 'existing')
    retriever.retrieve.return_value = [skill]; selector.select.return_value = skill
    failure = ExecutionFailure('failed', '', 'error', 73)
    worker.execute_skill.return_value = failure
    worker.execute_candidate.side_effect = [failure, [Observation('answer')]]
    generator.generate.return_value = SkillCandidate('initial', '初回')
    repairer.repair.return_value = SkillCandidate('repaired', '修正')
    critic.check.return_value = Critique(True, 'answered')
    result = IntentExecutor(retriever, selector, worker, generator, critic, library, repairer).execute(
        Intent('調査', service_ids=('overpass',)))
    assert [attempt.code for attempt in result.attempts] == ['existing', 'initial', 'repaired']
    assert [attempt.failure for attempt in result.attempts] == [failure, failure, None]
    assert result.attempts[0].observations == []
    assert result.attempts[2].observations == result.observations
    assert result.selected_skill_id == skill.id and result.selected_skill_critique is None
    assert result.learned_skill_id is not None and result.critique.success
