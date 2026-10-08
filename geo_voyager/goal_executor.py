from dataclasses import dataclass, replace

from .critique import Critique
from .critic import Critic
from .intent import Intent
from .intent_execution import IntentExecution
from .intent_executor import IntentExecutor
from .planner import Planner


@dataclass(frozen=True)
class GoalExecution:
    intents: tuple[Intent, ...]
    executions: tuple[IntentExecution, ...]
    critique: Critique


class GoalExecutor:
    def __init__(self, planner: Planner, executor: IntentExecutor, critic: Critic) -> None:
        self.planner, self.executor, self.critic = planner, executor, critic

    def execute(self, goal: str) -> GoalExecution:
        intents = self.planner.plan(goal)
        previous, executions, executed_intents = [], [], []
        for intent in intents:
            current = replace(intent, previous_observations=tuple(previous))
            execution = self.executor.execute(current)
            executed_intents.append(current)
            executions.append(execution)
            if not execution.critique.success:
                return GoalExecution(tuple(executed_intents), tuple(executions), execution.critique)
            previous.extend(execution.observations)
        final = Intent(goal, dataset_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.dataset_ids)),
                       service_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.service_ids)))
        critique = self.critic.check(final, executions[-1].observations)
        return GoalExecution(tuple(executed_intents), tuple(executions), critique)
