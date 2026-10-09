from dataclasses import replace
import subprocess

from .docker_sandbox import DockerSandbox
from .execution_failure import ExecutionFailure, GENERATED_ERROR_EXIT, candidate_lines, sandbox_program
from .intent import Intent
from .observation import Observation
from .skill import Skill
from .skill_candidate import SkillCandidate
from .services import load_service_graph


def injected_lines(intent: Intent) -> str:
    """The runtime variables the Worker defines in front of the generated code, one per line."""
    lines = ''
    if intent.dataset_ids:
        lines += f"dataset_id={intent.dataset_ids[0]!r}\n"
    if intent.target is not None:
        lines += f"intent_target={intent.target.to_dict()!r}\n"
    if intent.previous_observations:
        lines += f"previous_observations={[obs.text for obs in intent.previous_observations]!r}\nintent_text={intent.text!r}\n"
    return lines


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def _execute_code(self, intent: Intent, code: str) -> list[Observation] | ExecutionFailure:
        if len(intent.dataset_ids) > 1 or (not intent.dataset_ids and not intent.service_ids and not (intent.requires_context and intent.previous_observations)):
            raise ValueError("At most one dataset_id or registered service_ids are required")
        for service_id in intent.service_ids:
            load_service_graph().get(service_id)
        prefix = injected_lines(intent)
        code = prefix + code
        try:
            stdout = DockerSandbox(
                image="geo-voyager-worker:duckdb-1.5.6", network=self.network,
            ).run(sandbox_program(code))
        except subprocess.TimeoutExpired as error:
            # Code that does too much (a request per item, a query over too wide an area) is a failure of that
            # code: the repair and the Planner can read it and change the approach. It does not end the Goal.
            return ExecutionFailure('Generated Python execution timed out', '',
                                    f'TimeoutError: the sandbox stopped the code after {error.timeout:g} s', None)
        except subprocess.CalledProcessError as error:
            if error.returncode != GENERATED_ERROR_EXIT:
                raise
            failure = ExecutionFailure.from_process(error)
            return replace(failure, stderr=candidate_lines(failure.stderr, prefix.count('\n')))
        return [Observation(stdout.strip())] if stdout.strip() else []

    def execute_skill(self, intent: Intent, skill: Skill) -> list[Observation] | ExecutionFailure:
        return self._execute_code(intent, skill.code)

    def execute_candidate(self, intent: Intent, candidate: SkillCandidate) -> list[Observation] | ExecutionFailure:
        return self._execute_code(intent, candidate.code)
