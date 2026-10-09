"""Replay exhausted repair chains with a controlled repair prompt.

    .venv/bin/python -m bench.replay_repair --out DIR --runs RUN_DIR [RUN_DIR ...] [--repeat 3]

For each recorded chain whose attempts all failed, start from its first candidate and its
first failure, then let the Repairer try at most twice, exactly as IntentExecutor does.
Variants differ only in what the Repairer is given: v0 = nothing beyond the last failure,
v1 = the failing line and the attempt history, v2 = v1 and a resample when the code is unchanged. Success means the code ran without an
exception and, when the run's Goal has an oracle row, that the Goal judge accepts it.
"""
import argparse
import json
import os
from pathlib import Path

from bench.goals import GOALS
from bench.infra import benchmark_environment
from bench.run_goals import logged_llm
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.repair_stats import classify_failure
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.worker import Worker


def exhausted_chains(run_dir: Path) -> list[dict]:
    report = json.loads((run_dir / 'goal_report.json').read_text())
    goal_id = run_dir.name.split('.')[0]
    chains = []
    for number, (intent, execution) in enumerate(zip(report['intents'], report['executions'])):
        attempts = execution['attempts']
        if attempts and all(a['failure'] for a in attempts):
            chains.append({'run': run_dir.name, 'goal_id': goal_id, 'step': number,
                           'intent': intent, 'attempts': attempts})
    return chains


def build_intent(raw: dict) -> Intent:
    return Intent(raw['text'], tuple(raw['dataset_ids']), tuple(raw['service_ids']),
                  tuple(Observation(o['text']) for o in raw['previous_observations']),
                  raw['requires_context'])


def replay(chain: dict, variant: str, repairer: SkillCandidateRepairer, worker: Worker,
           oracle: dict | None, judge) -> dict:
    intent = build_intent(chain['intent'])
    first = chain['attempts'][0]
    candidate = SkillCandidate(first['code'], intent.text)
    history = [ExecutionAttempt(first['code'], [], ExecutionFailure(**first['failure']))]
    failure = history[0].failure
    outcome, errors, codes = None, [classify_failure(failure)], [candidate.code]
    final_text = ''
    for repair_number in (1, 2):
        candidate = repairer.repair(intent, candidate, failure,
                                    history=tuple(history) if variant != 'v0' else ())
        result = worker.execute_candidate(intent, candidate)
        codes.append(candidate.code)
        if isinstance(result, ExecutionFailure):
            failure = result
            history.append(ExecutionAttempt(candidate.code, [], failure))
            errors.append(classify_failure(failure))
            continue
        final_text = result[0].text if result else ''
        outcome = repair_number
        break
    correct = None
    if outcome is not None and oracle is not None:
        correct = bool(final_text) and judge(final_text, oracle)
    return {'run': chain['run'], 'step': chain['step'], 'variant': variant, 'outcome_at': outcome,
            'errors': errors, 'distinct_codes': len(set(codes)), 'correct': correct,
            'final_observation': final_text[:300]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--runs', nargs='+', required=True)
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--variants', default='v0,v1')
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    chains = [c for run in args.runs for c in exhausted_chains(Path(run).expanduser())]
    goals = {goal.id: goal for goal in GOALS}
    oracles = {}  # goal id -> oracle, from the recorded result rows next to each run
    for run in args.runs:
        for results in Path(run).expanduser().parent.glob('results*.jsonl'):
            for line in results.read_text().splitlines():
                row = json.loads(line)
                if row.get('oracle'):
                    oracles[row['id']] = row['oracle']
    llm = logged_llm(out / 'llm')
    # v0: last failure only. v1: + failing line and attempt history. v2: v1 + resample unchanged code.
    repairers = {'v0': SkillCandidateRepairer(llm), 'v1': SkillCandidateRepairer(llm),
                 'v2': SkillCandidateRepairer(llm, max_resamples=2)}
    print(f'{len(chains)} exhausted chains', flush=True)
    with benchmark_environment() as names:
        worker = Worker(names['internal'])
        for round_number in range(args.repeat):
            for chain in chains:
                for variant in args.variants.split(','):
                    goal = goals[chain['goal_id']]
                    row = replay(chain, variant, repairers[variant], worker, oracles.get(goal.id), goal.judge)
                    row['round'] = round_number
                    with (out / 'replay.jsonl').open('a') as file:
                        file.write(json.dumps(row, ensure_ascii=False) + '\n')
                    print(row['run'], row['variant'], 'outcome', row['outcome_at'], 'correct', row['correct'],
                          row['errors'], flush=True)


if __name__ == '__main__':
    main()
