from .critic import Critic
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
    ) -> None:
        self.retriever = retriever
        self.selector = selector
        self.worker = worker
        self.generator = generator
        self.critic = critic
        self.skill_library = skill_library

    def execute(self, intent: Intent, k: int = 4) -> IntentExecution:
        if len(intent.dataset_ids) > 1 or (not intent.dataset_ids and not intent.service_ids):
            raise ValueError('At most one dataset_id or registered service_ids are required')
        skills = self.retriever.retrieve(intent, k)
        retrieved_ids = tuple(skill.id for skill in skills)
        selected = self.selector.select(intent, skills)
        selected_skill_critique = None
        if selected is not None:
            observations = self.worker.execute_skill(intent, selected)
            selected_skill_critique = self.critic.check(intent, observations)
            if selected_skill_critique.success:
                return IntentExecution(
                    observations, retrieved_ids, selected.id, None,
                    selected_skill_critique, selected_skill_critique,
                )
        candidate = self.generator.generate(intent)
        observations = self.worker.execute_candidate(intent, candidate)
        critique = self.critic.check(intent, observations)
        learned = None
        if critique.success:
            learned = promote(candidate)
            self.skill_library.add(learned)
            self.retriever.upsert(learned)
        return IntentExecution(
            observations, retrieved_ids, selected.id if selected else None,
            learned.id if learned else None, critique, selected_skill_critique,
        )
