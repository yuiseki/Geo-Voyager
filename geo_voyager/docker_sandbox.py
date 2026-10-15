from dataclasses import dataclass
from pathlib import Path
import subprocess
from uuid import uuid4


@dataclass(frozen=True)
class SandboxProfile:
    """The resources and mounts of one sandbox run.

    The host has no swap, so memory is always capped and swap is given the same cap. data_dir is mounted
    read-only at /data; out_dir, which must be an empty directory, is the only writable mount, at /out.
    """
    memory: str
    cpus: str
    pids: str
    timeout: int
    tmpfs: str
    data_dir: str | None = None
    out_dir: str | None = None


# Relaxed for GeoAI-master-skills' small tasks (2026-10-14), now that the tables are read from a local mirror: the share of
# people within 1 km of a station, read from the 100 m grid of all Japan block by block (3.8 GB as float32), took 10 s
# and 176 MB in the worker; 128 MB could not hold it. Earlier, 30 s had failed right code reading through the Hub.
# 2 GB (2026-10-15): sum_population_grid over the 1,741 municipalities peaked at 1,154 MB beside the grid of 131 MB
# it keeps in /tmp, which counts against the limit.
DEFAULT_PROFILE = SandboxProfile(memory="2g", cpus="2", pids="128", timeout=180,
                                 tmpfs="/tmp:rw,noexec,nosuid,size=256m")
# For the analyses of study-geoai-algo-py (scikit-learn, LightGBM, OR-Tools, ...): it caps its heavy runs at 8G.
ANALYSIS_PROFILE = SandboxProfile(memory="8g", cpus="4", pids="512", timeout=600,
                                  tmpfs="/tmp:rw,noexec,nosuid,size=2g")


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-slim", network: str = "none",
                 profile: SandboxProfile = DEFAULT_PROFILE) -> None:
        self.image = image
        self.network = network
        self.profile = profile

    def _mounts(self) -> list[str]:
        mounts = []
        if self.profile.data_dir is not None:
            if not Path(self.profile.data_dir).is_dir():
                raise ValueError(f"The data directory does not exist: {self.profile.data_dir}")
            mounts += ["--mount", f"type=bind,source={self.profile.data_dir},target=/data,readonly"]
        if self.profile.out_dir is not None:
            out = Path(self.profile.out_dir)
            if not out.is_dir() or any(out.iterdir()):
                raise ValueError(f"The output directory must exist and be empty: {out}")
            mounts += ["--mount", f"type=bind,source={out},target=/out"]
        return mounts

    def run(self, code: str) -> str:
        if self.network != "none":
            inspected = subprocess.run(
                ["docker", "network", "inspect", "--format", "{{.Internal}}", self.network],
                check=True, capture_output=True, text=True, timeout=5,
            )
            if inspected.stdout.strip() != "true":
                raise ValueError("Sandbox requires an internal network")
        mounts = self._mounts()
        name = f"geo-voyager-sandbox-{uuid4().hex}"
        profile = self.profile
        command = [
            "docker", "run", "--rm", "--name", name, "--pull", "never", "-i",
            "--user", "65534:65534",
            "--read-only",
            "--tmpfs", profile.tmpfs,
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--memory", profile.memory,
            "--memory-swap", profile.memory,
            "--cpus", profile.cpus,
            "--pids-limit", profile.pids,
            "--network", self.network,
            *mounts,
            self.image, "python", "-I", "-B", "-",
        ]
        try:
            result = subprocess.run(
                command, input=code, text=True, capture_output=True,
                check=True, timeout=profile.timeout,
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
