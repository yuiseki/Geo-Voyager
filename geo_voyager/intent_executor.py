from dataclasses import replace
from .critic import Critic
from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
from .semantic_repairer import SemanticRepairer
from .skill_candidate_repairer import SkillCandidateRepairer
from .intent import Intent
from .intent_execution import IntentExecution
from .skill import SkillLibrary
from .skill_candidate import promote
from .skill_candidate_generator import SkillCandidateGenerator
from .skill_retriever import SkillRetriever
from .skill_selector import SkillSelector
from .worker import Worker


class IntentExecutor:
    def __init__(
        self, retriever: SkillRetriever, selector: SkillSelector, worker: Worker,
        generator: SkillCandidateGenerator, critic: Critic, skill_library: SkillLibrary,
        repairer: SkillCandidateRepairer | None = None,
        semantic_repairer: SemanticRepairer | None = None,
    ) -> None:
        self.repairer = repairer if repairer is not None else SkillCandidateRepairer()
        # Off unless given: one more model call and one more run for every Critic rejection.
        self.semantic_repairer = semantic_repairer
        self.retriever = retriever
        self.selector = selector
        self.worker = worker
        self.generator = generator
        self.critic = critic
        self.skill_library = skill_library

    def execute(self, intent: Intent, k: int = 4) -> IntentExecution:
        if len(intent.dataset_ids) > 1 or (not intent.dataset_ids and not intent.service_ids and not (intent.requires_context and intent.previous_observations)):
            raise ValueError('At most one dataset_id or registered service_ids are required')
        skills = self.retriever.retrieve(intent, k)
        retrieved_ids = tuple(skill.id for skill in skills)
        selected = self.selector.select(intent, skills)
        selected_skill_critique = None
        attempts = []
        if selected is not None:
            observations = self.worker.execute_skill(intent, selected)
            attempts.append(self._attempt(selected.code, observations))
            if not isinstance(observations, ExecutionFailure):
                selected_skill_critique = self.critic.check(intent, observations)
            if selected_skill_critique is not None and selected_skill_critique.success:
                return IntentExecution(
                    observations, retrieved_ids, selected.id, None,
                    selected_skill_critique, selected_skill_critique,
                    attempts=tuple(attempts),
                )
        candidate = self.generator.generate(intent)
        candidate_attempts = []
        for repair_count in range(3):
            observations = self.worker.execute_candidate(intent, candidate)
            attempts.append(self._attempt(candidate.code, observations))
            candidate_attempts.append(attempts[-1])
            if not isinstance(observations, ExecutionFailure):
                break
            if repair_count == 2:
                return IntentExecution(
                    [], retrieved_ids, selected.id if selected else None, None,
                    Critique(False, observations.message), selected_skill_critique,
                    failure=observations, attempts=tuple(attempts),
                )
            candidate = self.repairer.repair(intent, candidate, observations,
                                             history=tuple(candidate_attempts))
        critique = self.critic.check(intent, observations)
        attempts[-1] = replace(attempts[-1], critique=critique)
        if not critique.success and self.semantic_repairer is not None:
            candidate, observations, critique = self._semantic_repair(
                intent, candidate, observations, critique, tuple(candidate_attempts), attempts)
        learned = None
        if critique.success:
            learned = promote(candidate)
            self.skill_library.add(learned)
            self.retriever.upsert(learned)
        return IntentExecution(
            observations, retrieved_ids, selected.id if selected else None,
            learned.id if learned else None, critique, selected_skill_critique,
            attempts=tuple(attempts),
        )

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
        result = self.worker.execute_candidate(intent, proposal.candidate)
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

    @staticmethod
    def _attempt(code: str, result: list | ExecutionFailure) -> ExecutionAttempt:
        if isinstance(result, ExecutionFailure):
            return ExecutionAttempt(code, [], result)
        return ExecutionAttempt(code, result, None)
