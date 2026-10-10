"""Focused end-to-end runs of the step-by-step route. A few Goals, not a benchmark.

    .venv/bin/python -m bench.run_adaptive --out DIR hospital_minato hospital_minato:inject cafe_shibuya_vs_shinjuku:max=2

Each argument is a Goal id, optionally followed by :inject (the first step is made to fail, to see the
Planner plan again), :earlydone (the Planner is made to say DONE after the first count, too early), :twotargets=N (the Nth Planner call gets a
reply with two 対象 lines) and/or :max=N. Each run starts from an empty Skill Library that
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
from geo_voyager.planner import DONE, Planner
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_retriever import SkillRetriever
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
        return IntentExecution([], (), (), None, Critique(False, failure.message), failure=failure, attempts=attempts)


class EarlyDone:
    """Wraps a Planner. After the first step that produced a count it answers DONE, without asking the model.

    This is a deliberate injection, recorded as such in the trace. It stands in for a Planner that stops too early,
    which can not be waited for, so the return to the Planner after a final Critic failure can be seen. For a Goal
    that needs two counts it makes the DONE premature.
    """

    def __init__(self, planner: Planner) -> None:
        self.planner, self.injected = planner, False

    def next(self, goal, history):
        if not self.injected and any('"count"' in observation.text for observation in history.observations()):
            self.injected = True
            return DONE
        return self.planner.next(goal, history)


TWO_TARGET_REPLY = '''調査項目: 渋谷区と新宿区の amenity=cafe の地物数
利用データセット: []
利用サービス:
  - overpass
対象: 渋谷区
対象: 新宿区'''
PLANNER_PROMPT_START = 'Goal を達成するために、次に実行する Intent'


class BadPlannerReply:
    """Wraps the model client. The chosen Planner call gets a fixed, unusable reply instead of the model's.

    The reply is the one a model wrote in an earlier run: one Intent with two 対象 lines. It goes through the real
    parser, so the rejection, the history entry and the replanning are all real. Recorded as an injection.
    """

    def __init__(self, llm, call_number: int, reply: str = TWO_TARGET_REPLY) -> None:
        self.llm, self.call_number, self.reply, self.calls, self.injected = llm, call_number, reply, 0, False

    def generate(self, prompt, **kwargs):
        if prompt.startswith(PLANNER_PROMPT_START):
            self.calls += 1
            if self.calls == self.call_number:
                self.injected = True
                return self.reply
        return self.llm.generate(prompt, **kwargs)


def parse_spec(spec: str) -> dict:
    goal_id, *options = spec.split(':')
    parsed = {'goal_id': goal_id, 'inject': False, 'max_steps': DEFAULT_MAX_STEPS, 'earlydone': False,
              'twotargets': None}
    for option in options:
        if option == 'inject':
            parsed['inject'] = True
        elif option == 'earlydone':
            parsed['earlydone'] = True
        elif option.startswith('twotargets='):
            parsed['twotargets'] = int(option[len('twotargets='):])
        elif option.startswith('max='):
            parsed['max_steps'] = int(option[4:])
        else:
            raise SystemExit(f'unknown option {option!r} in {spec!r}')
    return parsed


def run_one(spec: str, names, directory: Path, embedding: EmbeddingClient, shared: Path | None = None) -> dict:
    options = parse_spec(spec)
    goal = next(goal for goal in GOALS if goal.id == options['goal_id'])
    directory.mkdir(parents=True, exist_ok=False)
    if shared is None:
        (directory / 'skill_library').mkdir()
    library = SkillLibrary(shared if shared is not None else directory / 'skill_library')
    llm = logged_llm(directory)
    critic = Critic(llm)
    repairer = SkillCandidateRepairer(llm)
    executor = IntentExecutor(SkillRetriever(library, embedding), Worker(names['internal']),
                              SkillCandidateGenerator(llm), critic, library, repairer)
    if options['inject']:
        executor = FirstStepFails(executor)
    started = time.time()
    planner_llm = BadPlannerReply(llm, options['twotargets']) if options['twotargets'] else llm
    planner = EarlyDone(Planner(planner_llm)) if options['earlydone'] else Planner(planner_llm)
    result = GoalExecutor(planner, executor, critic).execute_adaptive(goal.text, max_steps=options['max_steps'])
    row = {'spec': spec, 'id': goal.id, 'goal': goal.text, 'stop_reason': result.stop_reason, 'error': result.error,
           'critique': {'success': result.critique.success, 'reason': result.critique.reason},
           'max_steps': options['max_steps'], 'injected_first_failure': options['inject'],
           'injected_early_done': options['earlydone'] and planner.injected,
           'injected_two_targets': bool(options['twotargets']) and planner_llm.injected,
           'steps': trace_steps(result, injected={1} if options['inject'] else set()),
           'events': trace_events(result, injected={1} if options['inject'] else set()),
           'planner_calls': sum(1 for name in os.listdir(directory)
                                if name.endswith('_prompt.txt') and (directory / name).read_text().startswith('Goal を達成するために、次に実行する Intent')),
           'rejected_fallbacks': repairer.rejected_fallbacks,
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
    parser.add_argument('--library', help='one Skill library for all runs, carried from Goal to Goal. Made from the '
                                          "repository's seed Skills when it does not exist yet")
    parser.add_argument('specs', nargs='+')
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    shared = Path(args.library).expanduser() if args.library else None
    if shared is not None and not shared.exists():
        import shutil
        shutil.copytree(Path(__file__).resolve().parents[1] / 'skill_library', shared,
                        ignore=shutil.ignore_patterns('embedding.json'))
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'], os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    with benchmark_environment() as names:
        for number, spec in enumerate(args.specs, start=1):
            row = run_one(spec, names, out / f'{number:02d}_{spec.replace(":", "_").replace("=", "")}', embedding, shared)
            with (out / 'results.jsonl').open('a') as file:
                file.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(spec, '| stop', row['stop_reason'], '| steps', len(row['steps']), '| goal critic', row['critique']['success'],
                  '| matches oracle', row['correct'], '|', row['elapsed'], 's', flush=True)


if __name__ == '__main__':
    main()
