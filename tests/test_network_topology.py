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
