from dataclasses import replace
import json
import subprocess

from .docker_sandbox import DockerSandbox
from .execution_failure import ExecutionFailure, GENERATED_ERROR_EXIT, bounded_output, candidate_lines, sandbox_program
from .intent import Intent, execution_refusal
from .observation import Observation
from .contracts.output import output_problem
from .skill_candidate import SkillCandidate, entry_program
from .skill_library import SkillLibrary, link
from .services import load_service_graph


def _parsed(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def injected_lines(intent: Intent) -> str:
    """The runtime variables the Worker defines in front of the generated code, one per line."""
    lines = ''
    if len(intent.dataset_ids) == 1:          # with several, a primitive knows the one it reads
        lines += f"dataset_id={intent.dataset_ids[0]!r}\n"
    if intent.target is not None:
        lines += f"intent_target={intent.target.to_dict()!r}\n"
    if intent.previous_observations:
        lines += f"previous_observations={[obs.text for obs in intent.previous_observations]!r}\nintent_text={intent.text!r}\n"
    if intent.inputs:
        # The inputs by name, parsed: the code reads results["ward_stations"], not a position in a list of texts.
        lines += f"results={dict(zip(intent.inputs, (_parsed(obs.text) for obs in intent.previous_observations)))!r}\n"
    return lines


# 128 + SIGKILL: the kernel's out-of-memory killer, at the container's memory limit.
KILLED_EXIT = 137


class Worker:
    def __init__(self, network: str) -> None:
        self.network = network

    def _execute_code(self, intent: Intent, code: str, library: SkillLibrary | None = None) -> list[Observation] | ExecutionFailure:
        refusal = execution_refusal(intent)
        if refusal:
            raise ValueError(refusal)
        for service_id in intent.service_ids:
            load_service_graph().get(service_id)
        # The Skills the code calls are defined in front of it (geo_voyager.skill_library.link). Like the runtime
        # variables, they shift the line numbers, so the failure is numbered by the code as it was written.
        linked = link(code, library) if library is not None else code
        prefix = injected_lines(intent) + linked[:len(linked) - len(code)]
        code = prefix + code
        sandbox = DockerSandbox(image="geo-voyager-worker:duckdb-1.5.6-rasterio-1.5.1", network=self.network)
        try:
            stdout = sandbox.run(sandbox_program(code))
        except subprocess.TimeoutExpired as error:
            # Code that does too much (a request per item, a query over too wide an area) is a failure of that
            # code: the repair and the Planner can read it and change the approach. It does not end the Goal.
            return ExecutionFailure('Generated Python execution timed out', '',
                                    f'TimeoutError: the sandbox stopped the code after {error.timeout:g} s', None)
        except subprocess.CalledProcessError as error:
            if error.returncode == KILLED_EXIT:
                # The container is given a memory limit, and the kernel kills code that goes over it (SIGKILL). Like
                # a timeout, it is a failure of the code: reading less (a smaller area, in blocks) can fix it.
                return ExecutionFailure('Generated Python execution was killed', bounded_output(error.stdout),
                                        f'MemoryError: the sandbox killed the code (exit {KILLED_EXIT}): it used more '
                                        f'than its {sandbox.profile.memory} of memory. 一度に読む量を減らす（範囲や列で絞る、塊ごとに読んで足す）',
                                        KILLED_EXIT)
            if error.returncode != GENERATED_ERROR_EXIT:
                raise
            failure = ExecutionFailure.from_process(error)
            return replace(failure, stderr=candidate_lines(failure.stderr, prefix.count('\n')))
        problem = output_problem(stdout.strip())
        if problem:
            return ExecutionFailure('Generated Python output breaks the output contract', stdout, problem, None)
        return [Observation(stdout.strip())] if stdout.strip() else []

    def execute_candidate(self, intent: Intent, candidate: SkillCandidate,
                          library: SkillLibrary | None = None) -> list[Observation] | ExecutionFailure:
        # The model writes functions; the call of the main one is added here (see entry_program).
        return self._execute_code(intent, entry_program(candidate.code, candidate.entry), library)
