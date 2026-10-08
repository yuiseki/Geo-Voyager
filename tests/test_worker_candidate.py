from unittest.mock import patch

import pytest

from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.worker import Worker


def test_candidate_execution_returns_observations_only():
    intent = Intent('調査', ('admin',))
    candidate = SkillCandidate('print("結果")', '調査コード')
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = '結果\n'
        assert Worker('internal').execute_candidate(intent, candidate) == [Observation('結果')]
        assert sandbox.return_value.run.call_args.args[0] == "dataset_id='admin'\n" + candidate.code


def test_candidate_execution_error_propagates():
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = RuntimeError('execution failed')
        with pytest.raises(RuntimeError):
            Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('code', '説明'))
