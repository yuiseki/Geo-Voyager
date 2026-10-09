"""Replay saved semantic-completion failures through the semantic repairer. No new benchmark.

    .venv/bin/python -m bench.replay_semantic --out DIR --results RESULTS.jsonl [RESULTS.jsonl ...]

Each case is a recorded step that ran and that the Critic rejected. The repairer gets the Intent, the
candidate, the observation, the Critic's reason and the previous observations. A proposal is run in the
same sandbox and judged by the same Critic setting the case was recorded with. Cases are replayed once.
"""
import argparse
import json
import os
from pathlib import Path
import time

from bench.goals import GOALS
from bench.infra import benchmark_environment
from bench.run_goals import logged_llm
from bench.semantic_replay_stats import categorize, output_keys, select_cases, summarize
from geo_voyager.critic import Critic
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.semantic_repairer import SemanticRepairer
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.worker import Worker


def build_intent(raw: dict) -> Intent:
    return Intent(raw['text'], tuple(raw['dataset_ids']), tuple(raw['service_ids']),
                  tuple(Observation(o['text']) for o in raw['previous_observations']),
                  raw['requires_context'], raw.get('target_name'))


def replay_case(case: dict, repairer: SemanticRepairer, worker: Worker, llm, judges: dict) -> dict:
    started = time.time()
    intent = build_intent(case['intent'])
    before = '\n'.join(case['observations'])
    candidate = SkillCandidate(case['code'], intent.text)
    proposal = repairer.repair(intent, candidate, [Observation(text) for text in case['observations']], case['reason'],
                               history=tuple(ExecutionAttempt(code, [], None) for code in case['history']))
    result = {'run': case['run'], 'source': case['source'], 'goal_id': case['goal_id'], 'step': case['step'],
              'status': proposal.status, 'hardcoded': list(proposal.hardcoded), 'executed': False,
              'execution_failed': False, 'execution_error': '', 'critic_success': None, 'critic_before': case['reason'],
              'critic_after': None, 'before': before, 'after': None, 'keys_removed': [], 'keys_added': [],
              'code_changed': proposal.candidate is not None and proposal.candidate.code.strip() != case['code'].strip(),
              'judge_before': None, 'judge_after': None}
    judge = judges.get(case['goal_id'])
    if judge and case['oracle'] is not None:
        result['judge_before'] = bool(judge(before, case['oracle']))
    if proposal.status == 'proposed':
        result['executed'] = True
        outcome = worker.execute_candidate(intent, proposal.candidate)
        if isinstance(outcome, ExecutionFailure):
            result['execution_failed'] = True
            result['execution_error'] = outcome.stderr.strip().splitlines()[-1][:200] if outcome.stderr.strip() else ''
            result['after'] = ''
        else:
            after = '\n'.join(observation.text for observation in outcome)
            result['after'] = after
            if outcome:
                verdict = Critic(llm, thinking=case['critic_thinking']).check(intent, outcome)
                result['critic_success'], result['critic_after'] = verdict.success, verdict.reason
            old_keys, new_keys = output_keys(before), output_keys(after)
            if old_keys is not None and new_keys is not None:
                result['keys_removed'], result['keys_added'] = sorted(old_keys - new_keys), sorted(new_keys - old_keys)
            if judge and case['oracle'] is not None and after:
                result['judge_after'] = bool(judge(after, case['oracle']))
    result['category'] = categorize(result)
    result['elapsed'] = round(time.time() - started, 1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--results', nargs='+', required=True)
    parser.add_argument('--limit', type=int, default=None, help='replay only the first N cases')
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    cases, skipped = [], {}
    for path in args.results:
        chosen, left_out = select_cases(Path(path).expanduser())
        cases += chosen
        for reason, count in left_out.items():
            skipped[reason] = skipped.get(reason, 0) + count
    cases = cases[:args.limit] if args.limit else cases
    (out / 'cases.json').write_text(json.dumps({'cases': len(cases), 'skipped': skipped}, ensure_ascii=False, indent=1))
    print(f'{len(cases)} cases, skipped {skipped}', flush=True)
    judges = {goal.id: goal.judge for goal in GOALS}
    llm = logged_llm(out / 'llm')
    repairer = SemanticRepairer(llm)
    results = []
    with benchmark_environment() as names:
        worker = Worker(names['internal'])
        for case in cases:
            result = replay_case(case, repairer, worker, llm, judges)
            results.append(result)
            with (out / 'replay.jsonl').open('a') as file:
                file.write(json.dumps(result, ensure_ascii=False) + '\n')
            print(result['run'], f"step{result['step']}", result['status'], '->', result['category'],
                  '| critic', result['critic_success'], '| judge', result['judge_before'], '->', result['judge_after'], flush=True)
    summary = summarize(results)
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
