from .docker_sandbox import DockerSandbox
from .intent import Intent
from .observation import Observation
from .skill import Skill
from .skill_candidate import SkillCandidate


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def _execute_code(self, intent: Intent, code: str) -> list[Observation]:
        if len(intent.dataset_ids) != 1:
            raise ValueError("Exactly one dataset_id is required")
        code = f"dataset_id={intent.dataset_ids[0]!r}\n" + code
        stdout = DockerSandbox(
            image="geo-voyager-worker:duckdb-1.5.6", network=self.network,
        ).run(code)
        return [Observation(stdout.strip())]

    def execute_skill(self, intent: Intent, skill: Skill) -> list[Observation]:
        return self._execute_code(intent, skill.code)

    def execute_candidate(self, intent: Intent, candidate: SkillCandidate) -> list[Observation]:
        return self._execute_code(intent, candidate.code)
