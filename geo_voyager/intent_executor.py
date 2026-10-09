from .critic import Critic
from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
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
    ) -> None:
        self.repairer = repairer if repairer is not None else SkillCandidateRepairer()
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

    @staticmethod
    def _attempt(code: str, result: list | ExecutionFailure) -> ExecutionAttempt:
        if isinstance(result, ExecutionFailure):
            return ExecutionAttempt(code, [], result)
        return ExecutionAttempt(code, result, None)
