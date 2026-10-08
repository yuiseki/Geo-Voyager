from .critic import Critic
from .intent import Intent
from .intent_execution import IntentExecution
from .skill import SkillLibrary
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
        if len(intent.dataset_ids) != 1:
            raise ValueError('Exactly one dataset_id is required')
        skills = self.retriever.retrieve(intent, k)
        retrieved_ids = tuple(skill.id for skill in skills)
        selected = self.selector.select(intent, skills)
        if selected is not None:
            observations = self.worker.execute_skill(intent, selected)
            return IntentExecution(observations, retrieved_ids, selected.id, None)
        candidate = self.generator.generate(intent)
        observations, critique, learned = self.worker.execute_candidate(
            intent, candidate, self.critic, self.skill_library,
        )
        return IntentExecution(
            observations, retrieved_ids, None, learned.id if learned else None, critique,
        )
