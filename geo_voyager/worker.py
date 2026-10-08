from .docker_sandbox import DockerSandbox
from .intent import Intent
from .observation import Observation


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def execute(self, intent: Intent) -> list[Observation]:
        if intent.dataset_ids != ("yuiseki/jp-admin-2026-09",):
            raise ValueError("Only the administrative dataset is supported by this fixed analysis")
        code = (
            'import sys\nsys.path.insert(0, "/opt/geo_voyager")\n'
            'from most_populous_ward import main\n'
            f'main({intent.dataset_ids[0]!r})\n'
        )
        stdout = DockerSandbox(
            image="geo-voyager-worker:duckdb-1.5.6", network=self.network,
        ).run(code)
        return [Observation(stdout.strip())]
