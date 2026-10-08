from .critic import Critic
from .critique import Critique
from .docker_sandbox import DockerSandbox
from .intent import Intent
from .observation import Observation
from .skill import SkillLibrary
from .skill_candidate import SkillCandidate, promote
from .skills import POPULATION_SKILL_ID


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def _execute_code(self, intent: Intent, code: str) -> list[Observation]:
        if intent.dataset_ids != ("yuiseki/jp-admin-2026-09",):
            raise ValueError("Only the administrative dataset is supported by this fixed analysis")
        code = f"dataset_id={intent.dataset_ids[0]!r}\n" + code
        stdout = DockerSandbox(
            image="geo-voyager-worker:duckdb-1.5.6", network=self.network,
        ).run(code)
        return [Observation(stdout.strip())]

    def execute(self, intent: Intent) -> list[Observation]:
        skill = SkillLibrary().get(POPULATION_SKILL_ID)
        return self._execute_code(intent, skill.code)

    def execute_candidate(
        self, intent: Intent, candidate: SkillCandidate,
        critic: Critic, skill_library: SkillLibrary,
    ) -> tuple[list[Observation], Critique]:
        observations = self._execute_code(intent, candidate.code)
        critique = critic.check(intent, observations)
        if critique.success:
            skill_library.add(promote(candidate))
        return observations, critique
