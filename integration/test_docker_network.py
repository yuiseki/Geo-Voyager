"""明示実行専用。通常の pytest (testpaths=tests) では実行しない。"""

import json
import subprocess

import pytest

from integration.network_topology import network_topology


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=30)


def request(container, target):
    code = (
        "import time\n"
        "from urllib.request import build_opener, ProxyHandler\n"
        "opener = build_opener(ProxyHandler({}))\n"
        "for attempt in range(20):\n"
        "    try:\n"
        f"        response = opener.open('http://{target}:8000/', timeout=1)\n"
        "        assert response.status == 200\n"
        "        print(response.status)\n"
        "        break\n"
        "    except OSError:\n"
        "        if attempt == 19: raise\n"
        "        time.sleep(0.1)\n"
    )
    return docker("exec", container, "python", "-c", code).strip()


@pytest.mark.parametrize("isolated", [False, True])
def test_three_container_network_isolation(isolated):
    with network_topology(isolated=isolated) as names:
        def inspect(role):
            return json.loads(docker("inspect", names[role]))[0]

        assert set(inspect("worker")["NetworkSettings"]["Networks"]) == {names["internal"]}
        assert set(inspect("gateway")["NetworkSettings"]["Networks"]) == {names["internal"], names["external"]}
        origin = inspect("origin")
        assert set(origin["NetworkSettings"]["Networks"]) == {names["external"]}
        internal = json.loads(docker("network", "inspect", names["internal"]))[0]
        assert internal["Internal"] and internal["Driver"] == "bridge"
        if isolated:
            assert internal["Options"]["com.docker.network.bridge.gateway_mode_ipv4"] == "isolated"

        assert request(names["worker"], names["gateway"]) == "200"
        assert request(names["gateway"], names["origin"]) == "200"
        origin_ip = origin["NetworkSettings"]["Networks"][names["external"]]["IPAddress"]
        code = (
            "from urllib.request import build_opener, ProxyHandler\n"
            "opener = build_opener(ProxyHandler({}))\n"
            f"for target in { [names['origin'], origin_ip]!r}:\n"
            "    try:\n"
            "        opener.open('http://' + target + ':8000/', timeout=2)\n"
            "    except OSError:\n"
            "        print(target + ': blocked')\n"
            "    else:\n"
            "        raise AssertionError('Worker reached Origin directly')\n"
        )
        blocked = docker("exec", names["worker"], "python", "-c", code)
        assert blocked.count(": blocked") == 2
        print(f"mode={'isolated' if isolated else 'default'}: Worker→Gateway=200, Gateway→Origin=200, Worker→Origin=blocked (DNS/IP)")

    for role in ("worker", "gateway", "origin"):
        assert names[role] not in docker("ps", "-a", "--format", "{{.Names}}")
    for role in ("internal", "external"):
        assert names[role] not in docker("network", "ls", "--format", "{{.Name}}")
