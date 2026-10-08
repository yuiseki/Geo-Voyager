import subprocess
from uuid import uuid4


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-slim") -> None:
        self.image = image

    def run(self, code: str) -> str:
        name = f"geo-voyager-sandbox-{uuid4().hex}"
        command = [
            "docker", "run", "--rm", "--name", name, "--pull", "never", "-i",
            "--user", "65534:65534",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--memory", "128m",
            "--cpus", "1",
            "--pids-limit", "128",
            "--network", "none",
            self.image, "python", "-I", "-B", "-",
        ]
        try:
            result = subprocess.run(
                command, input=code, text=True, capture_output=True,
                check=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    ["docker", "rm", "--force", name],
                    capture_output=True, check=False, timeout=5,
                )
            finally:
                raise
        return result.stdout
