import subprocess
from unittest.mock import patch

import pytest

from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.worker import Worker


@pytest.mark.parametrize('error', ['SyntaxError: invalid syntax', 'RuntimeError: failed'])
def test_generated_errors_are_bounded_failures(error):
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = subprocess.CalledProcessError(
            73, ['docker', 'run'], output='x' * 20000, stderr=error)
        result = Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('bad', '説明'))
    assert isinstance(result, ExecutionFailure)
    assert result.exit_code == 73 and error in result.stderr
    assert len(result.stdout) <= 8192


@pytest.mark.parametrize('code', [1, 125, 126, 127, 137])
def test_infrastructure_failure_propagates(code):
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = subprocess.CalledProcessError(code, ['docker', 'run'], stderr='daemon failed')
        with pytest.raises(subprocess.CalledProcessError):
            Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('bad', '説明'))


def test_failure_redacts_secret_and_environment_dump():
    failure = ExecutionFailure.from_process(subprocess.CalledProcessError(
        73, [], output="TOKEN=private\nenviron({'HOME': '/x'})\nanswer", stderr='password: private'))
    assert 'private' not in failure.stdout + failure.stderr
    assert "'/x'" not in failure.stdout
    assert 'answer' in failure.stdout
