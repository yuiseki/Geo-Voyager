from unittest.mock import Mock, patch

import pytest

from geo_voyager.critique import Critique
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate import SkillCandidate, promote
from geo_voyager.worker import Worker


@pytest.mark.parametrize('success', [True, False])
def test_candidate_is_promoted_and_saved_only_after_critic_success(tmp_path, success):
    candidate = SkillCandidate(code='print("世田谷区、943664人")', description='人口最大の区と人口を取得')
    intent = Intent('東京都23区で人口が最も多い区と人口を求める', ('yuiseki/jp-admin-2026-09',))
    critic = Mock()
    critique = Critique(success=success, reason='回答の有無')
    critic.check.return_value = critique
    library = SkillLibrary(tmp_path)
    library_spy = Mock(wraps=library)
    events = []
    critic.check.side_effect = lambda *args: events.append('critic') or critique
    library_spy.add.side_effect = lambda skill: events.append('save') or library.add(skill)

    def promote_after_check(value):
        events.append('promote')
        return promote(value)
    with patch('geo_voyager.worker.DockerSandbox') as sandbox, \
         patch('geo_voyager.worker.promote', wraps=promote) as promotion:
        promotion.side_effect = promote_after_check
        sandbox.return_value.run.side_effect = lambda code: events.append('execution') or '世田谷区、943664人\n'
        observations, result = Worker(network='test-internal').execute_candidate(
            intent, candidate, critic, library_spy,
        )
        assert candidate.code in sandbox.return_value.run.call_args.args[0]
        assert observations == [Observation('世田谷区、943664人')]
        assert result == critique
        assert events == (['execution', 'critic', 'promote', 'save'] if success else ['execution', 'critic'])
        critic.check.assert_called_once_with(intent, observations)
        if success:
            promotion.assert_called_once_with(candidate)
            library_spy.add.assert_called_once()
            saved = library_spy.add.call_args.args[0]
            assert library.get(saved.id) == saved
            assert saved.code == candidate.code and saved.description == candidate.description
            assert library.all() == [saved]
        else:
            promotion.assert_not_called()
            library_spy.add.assert_not_called()
            assert list(tmp_path.iterdir()) == []


def test_execution_failure_does_not_call_critic_or_save():
    candidate = SkillCandidate(code='raise ValueError("failure")', description='失敗するコード')
    intent = Intent('人口最大の区', ('yuiseki/jp-admin-2026-09',))
    critic, library = Mock(), Mock()
    with patch('geo_voyager.worker.DockerSandbox') as sandbox, \
         patch('geo_voyager.worker.promote') as promotion:
        sandbox.return_value.run.side_effect = RuntimeError('execution failed')
        with pytest.raises(RuntimeError):
            Worker(network='test-internal').execute_candidate(intent, candidate, critic, library)
        promotion.assert_not_called()
    critic.check.assert_not_called()
    library.add.assert_not_called()
