import subprocess

from .docker_sandbox import DockerSandbox
from .execution_failure import ExecutionFailure, GENERATED_ERROR_EXIT, sandbox_program
from .intent import Intent
from .observation import Observation
from .skill import Skill
from .skill_candidate import SkillCandidate
from .services import load_service_graph


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def _execute_code(self, intent: Intent, code: str) -> list[Observation] | ExecutionFailure:
        if len(intent.dataset_ids) > 1 or (not intent.dataset_ids and not intent.service_ids):
            raise ValueError("At most one dataset_id or registered service_ids are required")
        for service_id in intent.service_ids:
            load_service_graph().get(service_id)
        if intent.previous_observations:
            code = f"previous_observations={[obs.text for obs in intent.previous_observations]!r}\nintent_text={intent.text!r}\n" + code
        if intent.dataset_ids:
            code = f"dataset_id={intent.dataset_ids[0]!r}\n" + code
        try:
            stdout = DockerSandbox(
                image="geo-voyager-worker:duckdb-1.5.6", network=self.network,
            ).run(sandbox_program(code))
        except subprocess.CalledProcessError as error:
            if error.returncode != GENERATED_ERROR_EXIT:
                raise
            return ExecutionFailure.from_process(error)
        return [Observation(stdout.strip())]

    def execute_skill(self, intent: Intent, skill: Skill) -> list[Observation] | ExecutionFailure:
        return self._execute_code(intent, skill.code)

    def execute_candidate(self, intent: Intent, candidate: SkillCandidate) -> list[Observation] | ExecutionFailure:
        return self._execute_code(intent, candidate.code)
