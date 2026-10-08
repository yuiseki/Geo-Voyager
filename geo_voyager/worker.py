from .docker_sandbox import DockerSandbox
from .intent import Intent
from .observation import Observation


class Worker:
    def execute(self, intent: Intent) -> list[Observation]:
        stdout = DockerSandbox().run('print("hello from sandbox")')
        return [Observation(stdout.strip())]
