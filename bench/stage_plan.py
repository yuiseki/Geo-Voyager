"""Stage 1 of a staged run: the Planner's first step for every Goal in a file, and nothing executed.

    .venv/bin/python -m bench.stage_plan --goals FILE --out DIR

Every model call is at temperature zero, so the same Goals give the same first steps until the Planner or its
prompt changes. A stage is fixed until its output is sound before the next one is run on it. The first step is
taken by GoalExecutor.execute_adaptive itself (a rejected reply is planned again, an Intent the executor would
refuse is a planner failure), stopped where the step would be executed. Needs the LLM only: no Docker, no
embedding. DIR/plans.jsonl gets one line per Goal; Goals already there are skipped, so a run can be continued.
"""
import argparse
import json
from pathlib import Path
import time

from bench.run_goals import logged_llm
from geo_voyager.critic import Critic
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.goal_history import PlannerFailure
from geo_voyager.intent import Intent
from geo_voyager.planner import Planner


class _Reached(Exception):
    def __init__(self, intent: Intent) -> None:
        super().__init__('the first step was reached')
        self.intent = intent


class _StopAtExecute:
    """An IntentExecutor that runs nothing: the first Intent handed to it ends the Goal."""

    def execute(self, intent: Intent):
        raise _Reached(intent)


def intent_record(intent: Intent) -> dict:
    return {'text': intent.text, 'dataset_ids': list(intent.dataset_ids), 'service_ids': list(intent.service_ids),
            'target': intent.target.to_dict() if intent.target is not None else None,
            'result_name': intent.result_name, 'inputs': list(intent.inputs) if intent.inputs is not None else None}


def first_step(goal: str, planner, critic) -> dict:
    """The Intent a full run would execute first, or how the run would stop before it, with the planner failures."""
    executor = GoalExecutor(planner, _StopAtExecute(), critic)
    seen = []
    original = executor._give_up

    def give_up(failures, limit):                 # the failures as they come, also when the Intent comes after them
        seen[:] = [failure.reason for failure in failures]
        return original(failures, limit)
    executor._give_up = give_up
    try:
        result = executor.execute_adaptive(goal)
    except _Reached as reached:
        return {'outcome': 'intent', 'intent': intent_record(reached.intent), 'planner_failures': seen}
    failures = [event.reason for event in result.events if isinstance(event, PlannerFailure)]
    return {'outcome': result.stop_reason, 'intent': None, 'planner_failures': failures, 'error': result.error}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--goals', required=True, help='a file of Goals, one per line')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    goals = [line.strip() for line in Path(args.goals).read_text().splitlines() if line.strip()]
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    plans = out / 'plans.jsonl'
    done = {json.loads(line)['number'] for line in plans.read_text().splitlines() if line.strip()} if plans.exists() else set()
    for number, goal in enumerate(goals, 1):
        if number in done:
            continue
        llm = logged_llm(out / f'{number:03d}')
        started = time.time()
        record = {'number': number, 'goal': goal, **first_step(goal, Planner(llm), Critic(llm)),
                  'llm_calls': llm.generate.call_count, 'elapsed': round(time.time() - started, 1)}
        with plans.open('a') as file:
            file.write(json.dumps(record, ensure_ascii=False) + '\n')
        intent = record['intent']
        print(number, '|', goal, '|', intent['text'] if intent else record['outcome'], '|', record['elapsed'], 's', flush=True)


if __name__ == '__main__':
    main()
