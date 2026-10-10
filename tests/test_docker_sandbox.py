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
        "--pids-limit": "128",
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


def test_sandbox_can_use_prebuilt_worker_image():
    with patch("geo_voyager.docker_sandbox.subprocess.run") as run:
        run.return_value.stdout = "duckdb extensions ok\n"
        assert DockerSandbox(image="geo-voyager-worker:duckdb-1.5.6").run("fixed code") == "duckdb extensions ok\n"
    assert "geo-voyager-worker:duckdb-1.5.6" in run.call_args.args[0]


def test_sandbox_allows_only_an_internal_network():
    with patch('geo_voyager.docker_sandbox.subprocess.run') as run:
        run.return_value.stdout = 'true\n'
        DockerSandbox(network='test-internal').run('fixed code')
    inspect, execution = [call.args[0] for call in run.call_args_list]
    assert inspect == ['docker', 'network', 'inspect', '--format', '{{.Internal}}', 'test-internal']
    assert execution[execution.index('--network') + 1] == 'test-internal'


def test_sandbox_rejects_external_network():
    with patch('geo_voyager.docker_sandbox.subprocess.run') as run:
        run.return_value.stdout = 'false\n'
        with pytest.raises(ValueError, match='internal'):
            DockerSandbox(network='external').run('fixed code')
    assert run.call_count == 1


# ---- the analysis profile: more memory, CPU and time, data read-only, one writable output directory

def _analysis_command(tmp_path, **overrides):
    from geo_voyager.docker_sandbox import ANALYSIS_PROFILE
    from dataclasses import replace
    data, out = tmp_path / 'data', tmp_path / 'out'
    data.mkdir(); out.mkdir()
    profile = replace(ANALYSIS_PROFILE, data_dir=str(data), out_dir=str(out), **overrides)
    with patch("geo_voyager.docker_sandbox.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "{}\n", "")
        DockerSandbox(image="geo-voyager-analysis:test", profile=profile).run('print("{}")')
    return run.call_args.args[0], run.call_args.kwargs, data, out


def test_the_analysis_profile_has_8g_without_swap_4_cpus_600_s_and_no_network(tmp_path):
    command, kwargs, _, _ = _analysis_command(tmp_path)
    for flag, value in {"--memory": "8g", "--memory-swap": "8g", "--cpus": "4", "--pids-limit": "512",
                        "--network": "none", "--user": "65534:65534", "--cap-drop": "ALL"}.items():
        assert command[command.index(flag) + 1] == value
    assert "--read-only" in command and "--privileged" not in command
    assert "/tmp:rw,noexec,nosuid,size=2g" in command
    assert kwargs["timeout"] == 600


def test_data_is_mounted_read_only_and_only_the_output_directory_is_writable(tmp_path):
    command, _, data, out = _analysis_command(tmp_path)
    mounts = [command[i + 1] for i, flag in enumerate(command) if flag == "--mount"]
    assert mounts == [f"type=bind,source={data},target=/data,readonly", f"type=bind,source={out},target=/out"]
    assert "-v" not in command and "--volume" not in command


def test_an_output_directory_that_is_not_empty_is_refused(tmp_path):
    from geo_voyager.docker_sandbox import ANALYSIS_PROFILE
    from dataclasses import replace
    out = tmp_path / 'out'; out.mkdir(); (out / 'old.png').write_text('x')
    with pytest.raises(ValueError, match='empty'):
        DockerSandbox(profile=replace(ANALYSIS_PROFILE, data_dir=str(tmp_path), out_dir=str(out))).run('pass')


def test_a_missing_data_directory_is_refused(tmp_path):
    from geo_voyager.docker_sandbox import ANALYSIS_PROFILE
    from dataclasses import replace
    with pytest.raises(ValueError, match='data'):
        DockerSandbox(profile=replace(ANALYSIS_PROFILE, data_dir=str(tmp_path / 'nothing'))).run('pass')


def test_the_default_profile_is_unchanged():
    from geo_voyager.docker_sandbox import DEFAULT_PROFILE
    assert (DEFAULT_PROFILE.memory, DEFAULT_PROFILE.cpus, DEFAULT_PROFILE.timeout, DEFAULT_PROFILE.tmpfs) == \
        ("128m", "1", 30, "/tmp:rw,noexec,nosuid,size=16m")
    assert DEFAULT_PROFILE.data_dir is None and DEFAULT_PROFILE.out_dir is None
