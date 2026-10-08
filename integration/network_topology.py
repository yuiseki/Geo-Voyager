"""Docker ネットワーク分離検証だけのテスト用構成。"""

from contextlib import contextmanager
import subprocess
from uuid import uuid4


@contextmanager
def network_topology(isolated=False):
    prefix = f"geo-voyager-nettest-{uuid4().hex}"
    names = {role: f"{prefix}-{role}" for role in ("internal", "external", "worker", "gateway", "origin")}
    try:
        internal = ["docker", "network", "create", "--driver", "bridge", "--internal"]
        if isolated:
            internal += ["--opt", "com.docker.network.bridge.gateway_mode_ipv4=isolated"]
        subprocess.run([*internal, names["internal"]], check=True, capture_output=True, timeout=30)
        subprocess.run(
            ["docker", "network", "create", "--driver", "bridge", names["external"]],
            check=True, capture_output=True, timeout=30,
        )
        for role, network in (("worker", "internal"), ("gateway", "internal"), ("origin", "external")):
            command = [
                "docker", "run", "--detach", "--name", names[role], "--pull", "never",
                "--network", names[network], "--user", "65534:65534", "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--memory", "128m",
                "--cpus", "1", "--pids-limit", "32", "python:3.12-slim", "python",
            ]
            if role == "worker":
                command += ["-c", "import time; time.sleep(120)"]
            else:
                command += ["-m", "http.server", "8000", "--bind", "0.0.0.0", "--directory", "/tmp"]
            subprocess.run(command, check=True, capture_output=True, timeout=30)
        subprocess.run(
            ["docker", "network", "connect", names["external"], names["gateway"]],
            check=True, capture_output=True, timeout=30,
        )
        yield names
    finally:
        try:
            subprocess.run(
                ["docker", "rm", "--force", names["worker"], names["gateway"], names["origin"]],
                check=False, capture_output=True, timeout=30,
            )
        finally:
            subprocess.run(
                ["docker", "network", "rm", names["internal"], names["external"]],
                check=False, capture_output=True, timeout=30,
            )
