import subprocess

import pytest

from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.execution_failure import ExecutionFailure, sandbox_program


@pytest.mark.parametrize('code,diagnostic', [('if :', 'SyntaxError'), ('raise ValueError("broken")', 'ValueError: broken')])
def test_generated_python_failure_in_real_container(code, diagnostic):
    with pytest.raises(subprocess.CalledProcessError) as caught:
        DockerSandbox(image='geo-voyager-worker:duckdb-1.5.6').run(sandbox_program(code))
    assert caught.value.returncode == 73
    assert diagnostic in ExecutionFailure.from_process(caught.value).stderr
