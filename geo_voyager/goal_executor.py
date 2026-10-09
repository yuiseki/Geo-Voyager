from dataclasses import dataclass, replace

from .critique import Critique
from .critic import Critic
from .goal_history import GoalHistory, HistoryEntry
from .intent import Intent
from .intent_execution import IntentExecution
from .intent_executor import IntentExecutor
from .planner import DONE, Done, Planner


@dataclass(frozen=True)
class GoalExecution:
    intents: tuple[Intent, ...]
    executions: tuple[IntentExecution, ...]
    critique: Critique


@dataclass(frozen=True)
class AdaptiveGoalExecution:
    goal: str
    history: tuple[HistoryEntry, ...]
    executions: tuple[IntentExecution, ...]
    # done | max_steps | repeated_intent | planner_error
    stop_reason: str
    critique: Critique
    error: str | None = None


DEFAULT_MAX_STEPS = 8
DEFAULT_MAX_ATTEMPTS_PER_INTENT = 2


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
        critique = self.critic.check(final, previous)
        return GoalExecution(tuple(executed_intents), tuple(executions), critique)

    def execute_adaptive(self, goal: str, *, max_steps: int = DEFAULT_MAX_STEPS,
                         max_attempts_per_intent: int = DEFAULT_MAX_ATTEMPTS_PER_INTENT) -> AdaptiveGoalExecution:
        """Run a Goal one step at a time. After each step the Planner decides the next Intent, or DONE.

        The full plan is not used. A step that fails does not end the Goal: the Planner sees the failure and
        plans again. Three things stop the loop short of DONE: the step limit, an Intent that already succeeded
        (or has already failed max_attempts_per_intent times) being planned again, and a plan that can not be
        made or run. A step receives the Observations of the steps that succeeded, and nothing else.
        """
        history, executions = GoalHistory(), []
        stop, error = 'max_steps', None
        for step in range(1, max_steps + 1):
            try:
                decision = self.planner.next(goal, history)
            except (ValueError, KeyError) as problem:
                stop, error = 'planner_error', f'{type(problem).__name__}: {problem}'
                break
            if isinstance(decision, Done):
                stop = 'done'
                break
            earlier = history.entries_for(decision)
            if any(entry.succeeded for entry in earlier) or len(earlier) >= max_attempts_per_intent:
                stop = 'repeated_intent'
                break
            current = replace(decision, previous_observations=history.observations())
            try:
                execution = self.executor.execute(current)
            except ValueError as problem:
                stop, error = 'planner_error', f'ValueError: {problem}'
                break
            executions.append(execution)
            history.append(HistoryEntry.from_execution(step, current, execution, history))
        if stop == 'done':
            critique = self.critic.check(self._goal_intent(goal, history), history.observations())
        else:
            critique = Critique(False, f'Goal を完了できなかった: {stop}' + (f'（{error}）' if error else ''))
        return AdaptiveGoalExecution(goal, history.entries, tuple(executions), stop, critique, error)

    @staticmethod
    def _goal_intent(goal: str, history: GoalHistory) -> Intent:
        intents = [entry.intent for entry in history]
        return Intent(goal, dataset_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.dataset_ids)),
                      service_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.service_ids)),
                      requires_context=True)
