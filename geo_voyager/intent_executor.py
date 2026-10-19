from dataclasses import replace
from .critic import Critic
from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
from .skill_candidate_repairer import SkillCandidateRepairer
from .intent import Intent, execution_refusal
from .intent_execution import IntentExecution
from .skill_candidate import SkillCandidate, drop_copied_skills, entry_program, main_function_name, new_skill_code, only_calls_a_saved_skill
from .skill_candidate_generator import SkillCandidateGenerator
from .skill_function import parse_skill
from .skill_library import SkillLibrary, link, linked_skills
from .skill_retriever import SkillRetriever
from .worker import Worker


class IntentExecutor:
    """One Intent: retrieve the closest Skills, generate code that may call them, run it, repair it, judge it,
    and save the new function as a Skill when the Critic accepts the run (as MineDojo/Voyager does)."""

    def __init__(
        self, retriever: SkillRetriever, worker: Worker, generator: SkillCandidateGenerator, critic: Critic,
        skill_library: SkillLibrary, repairer: SkillCandidateRepairer | None = None,
    ) -> None:
        self.repairer = repairer if repairer is not None else SkillCandidateRepairer()
        self.retriever = retriever
        self.worker = worker
        self.generator = generator
        self.critic = critic
        self.skill_library = skill_library

    def execute(self, intent: Intent, k: int = 4) -> IntentExecution:
        refusal = execution_refusal(intent)
        if refusal:
            raise ValueError(refusal)
        skills = self.retriever.retrieve(intent.text, k)
        retrieved = tuple(f'{skill.name}@v{self.skill_library.versions(skill.name)[-1]}' for skill in skills)
        candidate = self._without_copies(self.generator.generate(intent, skills))
        attempts, candidate_attempts = [], []
        for repair_count in range(3):
            observations = self.worker.execute_candidate(intent, candidate, self.skill_library)
            attempts.append(self._attempt(candidate.code, observations))
            candidate_attempts.append(attempts[-1])
            if not isinstance(observations, ExecutionFailure):
                break
            if repair_count == 2:
                return IntentExecution([], retrieved, tuple(linked_skills(entry_program(candidate.code, candidate.entry), self.skill_library)), None,
                                       Critique(False, observations.message), failure=observations, attempts=tuple(attempts))
            candidate = self._without_copies(
                self.repairer.repair(intent, candidate, observations, history=tuple(candidate_attempts)))
        # The saved Skills the code calls are shown in front of it: code that only called one was failed three times
        # for not showing how it measured (explore 35).
        critique = self.critic.check(intent, observations, code=link(candidate.code, self.skill_library))
        attempts[-1] = replace(attempts[-1], critique=critique)
        called = tuple(linked_skills(entry_program(candidate.code, candidate.entry), self.skill_library))
        learned, note = None, None
        code = new_skill_code(candidate.code, candidate.description) if critique.success else None
        wrapped = only_calls_a_saved_skill(code, self.skill_library) if code is not None else None
        if wrapped is not None:
            note, code = f'not saved as a Skill: it only calls the saved Skill {wrapped}', None
        if code is not None:
            try:
                version = self.skill_library.add(code)
                learned = f'{parse_skill(code).name}@v{version}'
            except ValueError as problem:
                note = f'not saved as a Skill: {problem}'
        return IntentExecution(observations, retrieved, called, learned, critique, attempts=tuple(attempts), note=note)

    def _without_copies(self, candidate: SkillCandidate) -> SkillCandidate:
        """A copied definition of a saved Skill becomes a call to the saved one (see drop_copied_skills). When the
        copy was the main function, the saved Skill of that name becomes the entry."""
        code = drop_copied_skills(candidate.code, self.skill_library)
        if code == candidate.code:
            return candidate
        main = main_function_name(candidate.code)
        entry = main if main is not None and main_function_name(code) != main else candidate.entry
        return replace(candidate, code=code, entry=entry)

    @staticmethod
    def _attempt(code: str, result: list | ExecutionFailure) -> ExecutionAttempt:
        if isinstance(result, ExecutionFailure):
            return ExecutionAttempt(code, [], result)
        return ExecutionAttempt(code, result, None)
