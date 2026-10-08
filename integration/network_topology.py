"""Docker ネットワーク分離検証だけのテスト用構成。"""

from contextlib import contextmanager
import subprocess
from uuid import uuid4


@contextmanager
def network_topology(isolated=False, gateway_code=None, origin_code=None, worker_image="python:3.12-slim", include_origin=True):
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
        roles = [("worker", "internal"), ("gateway", "internal")]
        if include_origin:
            roles.append(("origin", "external"))
        for role, network in roles:
            command = [
                "docker", "run", "--detach", "--name", names[role], "--pull", "never",
                "--network", names[network], "--network-alias", role, "--user", "65534:65534", "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--memory", "128m",
                "--cpus", "1", "--pids-limit", "128" if role == "worker" else "32", worker_image if role == "worker" else "python:3.12-slim", "python",
            ]
            custom_code = gateway_code if role == "gateway" else origin_code if role == "origin" else None
            if custom_code is not None:
                command += ["-c", custom_code]
            elif role == "worker":
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
                ["docker", "rm", "--force", names["worker"], names["gateway"], *([names["origin"]] if include_origin else [])],
                check=False, capture_output=True, timeout=30,
            )
        finally:
            subprocess.run(
                ["docker", "network", "rm", names["internal"], names["external"]],
                check=False, capture_output=True, timeout=30,
            )
