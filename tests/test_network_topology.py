import subprocess
from unittest.mock import patch

import pytest

from integration.network_topology import network_topology


@pytest.mark.parametrize("isolated", [False, True])
def test_topology_uses_only_the_required_network_connections(isolated):
    with patch("integration.network_topology.subprocess.run") as run:
        with network_topology(isolated=isolated) as names:
            commands = [entry.args[0] for entry in run.call_args_list]

    internal = next(command for command in commands if command[-1] == names["internal"])
    assert internal[:3] == ["docker", "network", "create"]
    assert "--internal" in internal
    assert internal[internal.index("--driver") + 1] == "bridge"
    assert ("com.docker.network.bridge.gateway_mode_ipv4=isolated" in internal) == isolated
    for role, network in (("worker", "internal"), ("gateway", "internal"), ("origin", "external")):
        command = next(command for command in commands if "--name" in command and names[role] in command)
        assert command[command.index("--network") + 1] == names[network]
        assert command[command.index("--pull") + 1] == "never"
        assert command[command.index("--pids-limit") + 1] == ("128" if role == "worker" else "32")
        assert not {"-p", "--publish", "-v", "--volume", "--mount"}.intersection(command)
    connections = [command for command in commands if command[:3] == ["docker", "network", "connect"]]
    assert connections == [["docker", "network", "connect", names["external"], names["gateway"]]]
    cleanup = [entry.args[0] for entry in run.call_args_list[len(commands):]]
    assert cleanup == [
        ["docker", "rm", "--force", names["worker"], names["gateway"], names["origin"]],
        ["docker", "network", "rm", names["internal"], names["external"]],
    ]


def test_topology_cleans_up_after_setup_failure():
    with patch("integration.network_topology.subprocess.run") as run:
        run.side_effect = [None, subprocess.CalledProcessError(1, ["docker"]), None, None]
        with pytest.raises(subprocess.CalledProcessError):
            with network_topology():
                pytest.fail("Setup must fail")

    assert run.call_args_list[-2].args[0][:3] == ["docker", "rm", "--force"]
    assert run.call_args_list[-1].args[0][:3] == ["docker", "network", "rm"]


def test_topology_can_run_test_gateway_and_origin_code_without_mounts():
    with patch("integration.network_topology.subprocess.run") as run:
        with network_topology(gateway_code="gateway code", origin_code="origin code") as names:
            commands = [entry.args[0] for entry in run.call_args_list]

    for role in ("gateway", "origin"):
        command = next(command for command in commands if "--name" in command and names[role] in command)
        assert command[-2:] == ["-c", f"{role} code"]
        assert command[command.index("--network-alias") + 1] == role
        assert not {"-v", "--volume", "--mount"}.intersection(command)


def test_topology_uses_worker_image_and_can_omit_the_test_origin():
    with patch("integration.network_topology.subprocess.run") as run:
        with network_topology(worker_image="geo-voyager-worker:duckdb-1.5.6", include_origin=False) as names:
            commands = [entry.args[0] for entry in run.call_args_list]
    starts = [command for command in commands if command[:2] == ["docker", "run"]]
    assert len(starts) == 2
    worker = next(command for command in starts if names["worker"] in command)
    assert "geo-voyager-worker:duckdb-1.5.6" in worker
    assert worker[worker.index("--network") + 1] == names["internal"]
