from dataclasses import dataclass, replace

from .critique import Critique
from .critic import Critic
from .goal_history import FinalCriticFailure, GoalHistory, HistoryEntry, PlannerFailure
from .intent import Intent
from .intent_execution import IntentExecution
from .intent_executor import IntentExecutor
from .planner import Done, Planner, PlannerRejected


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
    # done | max_steps | repeated_intent | planner_failure | final_critic_failed | planner_error
    stop_reason: str
    critique: Critique
    error: str | None = None
    # Everything that happened, in order: executed steps, planner failures and final critic failures.
    events: tuple = ()


DEFAULT_MAX_STEPS = 8
DEFAULT_MAX_ATTEMPTS_PER_INTENT = 2
DEFAULT_MAX_PLANNER_FAILURES = 3
DEFAULT_MAX_FINAL_CRITIC_FAILURES = 3


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
                         max_attempts_per_intent: int = DEFAULT_MAX_ATTEMPTS_PER_INTENT,
                         max_planner_failures: int = DEFAULT_MAX_PLANNER_FAILURES,
                         max_final_critic_failures: int = DEFAULT_MAX_FINAL_CRITIC_FAILURES) -> AdaptiveGoalExecution:
        """Run a Goal one step at a time. After each step the Planner decides the next Intent, or DONE.

        The full plan is not used. Three kinds of setback do not end the Goal; each is recorded in the history so
        that the next call to the Planner can read it and plan again:
          - a step that fails (the Planner sees the failure),
          - a Planner reply that can not be used, or an Intent the executor refuses (a PlannerFailure),
          - a DONE after which the Critic finds the Goal not answered (a FinalCriticFailure, with its reason).
        Every pass of the loop executes a step, records a failure, or stops, and each of the three has a limit, so
        the loop ends. It stops early when the same failure comes back, or an Intent that already succeeded (or has
        already failed max_attempts_per_intent times) is planned again. A step receives the Observations of the steps
        that succeeded, and nothing else.
        """
        history, executions = GoalHistory(), []
        stop, error = 'max_steps', None
        critique = None
        while len(history) < max_steps:
            try:
                decision = self.planner.next(goal, history)
            except PlannerRejected as rejected:
                history.append(PlannerFailure(rejected.reason, rejected.reply, len(history)))
                if self._give_up(history.planner_failures(), max_planner_failures):
                    stop, error = 'planner_failure', rejected.reason
                    break
                continue
            except (ValueError, KeyError) as problem:
                stop, error = 'planner_error', f'{type(problem).__name__}: {problem}'
                break
            if isinstance(decision, Done):
                critique = self.critic.check(self._goal_intent(goal, history), history.observations())
                if critique.success:
                    stop = 'done'
                    break
                history.append(FinalCriticFailure(critique.reason, len(history)))
                if self._give_up(history.final_critic_failures(), max_final_critic_failures):
                    stop, error = 'final_critic_failed', critique.reason
                    break
                continue
            earlier = history.entries_for(decision)
            if any(entry.succeeded for entry in earlier) or len(earlier) >= max_attempts_per_intent:
                stop = 'repeated_intent'
                break
            current = replace(decision, previous_observations=history.observations())
            try:
                execution = self.executor.execute(current)
            except ValueError as problem:
                reason = f'ValueError: {problem}'
                history.append(PlannerFailure(reason, current.text, len(history)))
                if self._give_up(history.planner_failures(), max_planner_failures):
                    stop, error = 'planner_failure', reason
                    break
                continue
            executions.append(execution)
            history.append(HistoryEntry.from_execution(len(history) + 1, current, execution, history))
        if stop != 'done':
            critique = Critique(False, f'Goal を完了できなかった: {stop}' + (f'（{error}）' if error else ''))
        return AdaptiveGoalExecution(goal, history.entries, tuple(executions), stop, critique, error, history.events)

    @staticmethod
    def _give_up(failures: tuple, limit: int) -> bool:
        """Stop retrying after `limit` failures of a kind, or as soon as one repeats an earlier reason."""
        return len(failures) >= limit or failures[-1].reason in [failure.reason for failure in failures[:-1]]

    @staticmethod
    def _goal_intent(goal: str, history: GoalHistory) -> Intent:
        intents = [entry.intent for entry in history]
        return Intent(goal, dataset_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.dataset_ids)),
                      service_ids=tuple(dict.fromkeys(id for intent in intents for id in intent.service_ids)),
                      requires_context=True)
