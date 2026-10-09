from geo_voyager.execution_failure import sandbox_program
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
        assert sandbox.return_value.run.call_args.args[0] == sandbox_program("dataset_id='admin'\n" + candidate.code)


def test_candidate_execution_error_propagates():
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = RuntimeError('execution failed')
        with pytest.raises(RuntimeError):
            Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('code', '説明'))


def test_successful_code_without_output_returns_no_observations():
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = ''
        assert Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('pass', '説明')) == []


def test_a_candidate_that_runs_too_long_is_a_failure_of_that_candidate_not_of_the_run():
    import subprocess
    from geo_voyager.execution_failure import ExecutionFailure
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = subprocess.TimeoutExpired(['docker', 'run'], 30)
        result = Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('while True: pass', '説明'))
    assert isinstance(result, ExecutionFailure) and result.exit_code is None
    assert 'TimeoutError' in result.stderr and '30' in result.stderr
