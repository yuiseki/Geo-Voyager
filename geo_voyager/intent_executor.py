from dataclasses import replace
from .critic import Critic
from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
from .semantic_repairer import SemanticRepairer
from .skill_candidate_repairer import SkillCandidateRepairer
from .intent import Intent
from .intent_execution import IntentExecution
from .skill_candidate import SkillCandidate, drop_copied_skills, new_skill_code
from .skill_candidate_generator import SkillCandidateGenerator
from .skill_function import parse_skill
from .skill_library import SkillLibrary, linked_skills
from .skill_retriever import SkillRetriever
from .worker import Worker


class IntentExecutor:
    """One Intent: retrieve the closest Skills, generate code that may call them, run it, repair it, judge it,
    and save the new function as a Skill when the Critic accepts the run (as MineDojo/Voyager does)."""

    def __init__(
        self, retriever: SkillRetriever, worker: Worker, generator: SkillCandidateGenerator, critic: Critic,
        skill_library: SkillLibrary, repairer: SkillCandidateRepairer | None = None,
        semantic_repairer: SemanticRepairer | None = None,
    ) -> None:
        self.repairer = repairer if repairer is not None else SkillCandidateRepairer()
        # Off unless given: one more model call and one more run for every Critic rejection.
        self.semantic_repairer = semantic_repairer
        self.retriever = retriever
        self.worker = worker
        self.generator = generator
        self.critic = critic
        self.skill_library = skill_library

    def execute(self, intent: Intent, k: int = 4) -> IntentExecution:
        if len(intent.dataset_ids) > 1 or (not intent.dataset_ids and not intent.service_ids and not (intent.requires_context and intent.previous_observations)):
            raise ValueError('At most one dataset_id or registered service_ids are required')
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
                return IntentExecution([], retrieved, tuple(linked_skills(candidate.code, self.skill_library)), None,
                                       Critique(False, observations.message), failure=observations, attempts=tuple(attempts))
            candidate = self._without_copies(
                self.repairer.repair(intent, candidate, observations, history=tuple(candidate_attempts)))
        critique = self.critic.check(intent, observations)
        attempts[-1] = replace(attempts[-1], critique=critique)
        if not critique.success and self.semantic_repairer is not None:
            candidate, observations, critique = self._semantic_repair(
                intent, candidate, observations, critique, tuple(candidate_attempts), attempts)
        called = tuple(linked_skills(candidate.code, self.skill_library))
        learned, note = None, None
        code = new_skill_code(candidate.code, candidate.description) if critique.success else None
        if code is not None:
            try:
                version = self.skill_library.add(code)
                learned = f'{parse_skill(code).name}@v{version}'
            except ValueError as problem:
                note = f'not saved as a Skill: {problem}'
        return IntentExecution(observations, retrieved, called, learned, critique, attempts=tuple(attempts), note=note)

    def _semantic_repair(self, intent, candidate, observations, critique, history, attempts):
        """One repair after the Critic rejected a run that had succeeded. Never more than one.

        It is a separate route from the runtime repair: no traceback is involved. The repaired candidate
        is run and judged again. It replaces the original result only when the Critic accepts it, so a
        repair can not leave the Intent worse than it was.
        """
        proposal = self.semantic_repairer.repair(intent, candidate, observations, critique.reason, history=history)
        if proposal.status != 'proposed':
            attempts.append(ExecutionAttempt(proposal.candidate.code if proposal.candidate else candidate.code, [], None,
                                             route='semantic', trigger=critique.reason, executed=False, note=proposal.status))
            return candidate, observations, critique
        result = self.worker.execute_candidate(intent, proposal.candidate, self.skill_library)
        if isinstance(result, ExecutionFailure):
            attempts.append(ExecutionAttempt(proposal.candidate.code, [], result, route='semantic',
                                             trigger=critique.reason, note='execution failed'))
            return candidate, observations, critique
        repaired = self.critic.check(intent, result)
        attempts.append(ExecutionAttempt(proposal.candidate.code, result, None, route='semantic', critique=repaired,
                                         trigger=critique.reason, note='critic passed' if repaired.success else 'critic failed'))
        if repaired.success:
            return proposal.candidate, result, repaired
        return candidate, observations, critique

    def _without_copies(self, candidate: SkillCandidate) -> SkillCandidate:
        """A copied definition of a saved Skill becomes a call to the saved one (see drop_copied_skills)."""
        code = drop_copied_skills(candidate.code, self.skill_library)
        return candidate if code == candidate.code else replace(candidate, code=code)

    @staticmethod
    def _attempt(code: str, result: list | ExecutionFailure) -> ExecutionAttempt:
        if isinstance(result, ExecutionFailure):
            return ExecutionAttempt(code, [], result)
        return ExecutionAttempt(code, result, None)
