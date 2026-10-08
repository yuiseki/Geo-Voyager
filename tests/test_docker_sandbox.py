import subprocess
from unittest.mock import patch

import pytest

from geo_voyager.docker_sandbox import DockerSandbox


def test_sandbox_returns_stdout_with_required_constraints():
    code = 'print("hello from sandbox")'
    with patch("geo_voyager.docker_sandbox.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "hello from sandbox\n", "")

        assert DockerSandbox().run(code) == "hello from sandbox\n"

    run.assert_called_once()
    command = run.call_args.args[0]
    assert command[:2] == ["docker", "run"]
    for flag, value in {
        "--user": "65534:65534",
        "--tmpfs": "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop": "ALL",
        "--security-opt": "no-new-privileges",
        "--memory": "128m",
        "--cpus": "1",
        "--pids-limit": "32",
        "--network": "none",
        "--pull": "never",
    }.items():
        assert command[command.index(flag) + 1] == value
    assert "--read-only" in command
    assert "--rm" in command
    assert command[-5:] == ["python:3.12-slim", "python", "-I", "-B", "-"]
    assert not {"-v", "--volume", "--mount", "--privileged"}.intersection(command)
    assert run.call_args.kwargs == {
        "input": code, "text": True, "capture_output": True, "check": True, "timeout": 30,
    }


def test_sandbox_rejects_nonzero_exit():
    with patch("geo_voyager.docker_sandbox.subprocess.run") as run:
        run.side_effect = subprocess.CalledProcessError(1, ["docker", "run"], stderr="failed")
        with pytest.raises(subprocess.CalledProcessError):
            DockerSandbox().run("raise ValueError()")


def test_sandbox_rejects_timeout_and_removes_its_container():
    with patch("geo_voyager.docker_sandbox.subprocess.run") as run:
        run.side_effect = [subprocess.TimeoutExpired(["docker", "run"], 30), None]
        with pytest.raises(subprocess.TimeoutExpired):
            DockerSandbox().run("while True: pass")

    command = run.call_args_list[0].args[0]
    name = command[command.index("--name") + 1]
    assert run.call_args_list[1].args[0] == ["docker", "rm", "--force", name]
