"""Focused end-to-end runs of the step-by-step route. A few Goals, not a benchmark.

    .venv/bin/python -m bench.run_adaptive --out DIR hospital_minato hospital_minato:inject cafe_shibuya_vs_shinjuku:max=2

Each argument is a Goal id, optionally followed by :inject (the first step is made to fail, to see the
Planner plan again) and/or :max=N (a step limit). Each run starts from an empty Skill Library that
the steps of that run fill, so a Skill learned in one step can be reused in a later one.
"""
import argparse
import json
import os
from pathlib import Path
import time

from bench.adaptive_trace import render_trace, trace_events, trace_steps
from bench.goals import GOALS
from bench.infra import WORKER_IMAGE, benchmark_environment
from bench.run_goals import logged_llm, run_oracle
from geo_voyager.critic import Critic
from geo_voyager.critique import Critique
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_executor import DEFAULT_MAX_STEPS, GoalExecutor
from geo_voyager.goal_history import FinalCriticFailure, PlannerFailure
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.planner import Planner
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from geo_voyager.worker import Worker


class FirstStepFails:
    """Wraps an IntentExecutor and fails its first execution, as if every attempt of that Intent crashed.

    This is a deliberate fault injection, recorded as such in the trace. It stands in for a failure that
    can not be waited for, so the replanning after a failure can be seen.
    """

    def __init__(self, executor: IntentExecutor) -> None:
        self.executor, self.calls = executor, 0

    def execute(self, intent):
        self.calls += 1
        if self.calls > 1:
            return self.executor.execute(intent)
        failure = ExecutionFailure('Generated Python execution failed (injected)', '',
                                   'Traceback (most recent call last):\n  File "<candidate>", line 3, in <module>\n'
                                   'RuntimeError: injected failure for the first step', 73)
        attempts = tuple(ExecutionAttempt('(injected)', [], failure) for _ in range(3))
        return IntentExecution([], (), None, None, Critique(False, failure.message), None, failure=failure, attempts=attempts)


def parse_spec(spec: str) -> dict:
    goal_id, *options = spec.split(':')
    parsed = {'goal_id': goal_id, 'inject': False, 'max_steps': DEFAULT_MAX_STEPS}
    for option in options:
        if option == 'inject':
            parsed['inject'] = True
        elif option.startswith('max='):
            parsed['max_steps'] = int(option[4:])
        else:
            raise SystemExit(f'unknown option {option!r} in {spec!r}')
    return parsed


def run_one(spec: str, names, directory: Path, embedding: EmbeddingClient) -> dict:
    options = parse_spec(spec)
    goal = next(goal for goal in GOALS if goal.id == options['goal_id'])
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'skill_library').mkdir()
    library = SkillLibrary(directory / 'skill_library')
    llm = logged_llm(directory)
    critic = Critic(llm)
    executor = IntentExecutor(SkillRetriever(library, embedding), SkillSelector(llm), Worker(names['internal']),
                              SkillCandidateGenerator(llm), critic, library, SkillCandidateRepairer(llm))
    if options['inject']:
        executor = FirstStepFails(executor)
    started = time.time()
    result = GoalExecutor(Planner(llm), executor, critic).execute_adaptive(goal.text, max_steps=options['max_steps'])
    row = {'spec': spec, 'id': goal.id, 'goal': goal.text, 'stop_reason': result.stop_reason, 'error': result.error,
           'critique': {'success': result.critique.success, 'reason': result.critique.reason},
           'max_steps': options['max_steps'], 'injected_first_failure': options['inject'],
           'steps': trace_steps(result, injected={1} if options['inject'] else set()),
           'events': trace_events(result, injected={1} if options['inject'] else set()),
           'planner_calls': sum(1 for name in os.listdir(directory)
                                if name.endswith('_prompt.txt') and (directory / name).read_text().startswith('Goal を達成するために、次に実行する Intent')),
           'planner_failures': sum(1 for event in result.events if isinstance(event, PlannerFailure)),
           'final_critic_failures': sum(1 for event in result.events if isinstance(event, FinalCriticFailure)),
           'elapsed': round(time.time() - started, 1)}
    answers = [entry.observations[0].text for entry in result.history if entry.succeeded and entry.observations]
    row['final_observation'] = answers[-1][:1500] if answers else ''
    try:
        row['oracle'] = run_oracle(goal.oracle_code, names['internal'])
        row['correct'] = bool(row['final_observation']) and bool(goal.judge(row['final_observation'], row['oracle']))
    except Exception as problem:
        row['oracle_error'] = f'{type(problem).__name__}: {problem}'
        row['correct'] = None
    (directory / 'trace.md').write_text(render_trace(row))
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('specs', nargs='+')
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'], os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    with benchmark_environment() as names:
        for number, spec in enumerate(args.specs, start=1):
            row = run_one(spec, names, out / f'{number:02d}_{spec.replace(":", "_").replace("=", "")}', embedding)
            with (out / 'results.jsonl').open('a') as file:
                file.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(spec, '| stop', row['stop_reason'], '| steps', len(row['steps']), '| goal critic', row['critique']['success'],
                  '| matches oracle', row['correct'], '|', row['elapsed'], 's', flush=True)


if __name__ == '__main__':
    main()
