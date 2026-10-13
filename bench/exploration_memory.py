"""The record of an earlier exploration of a Goal, as the Planner reads it: each step's Intent and how it ended
(succeeded, a failed execution with its error, or a Critic's rejection with its reason and what was observed), the
replies the Planner had refused and the final judgements that failed. Raw: no failure is classified or judged here,
so an experiment can change only whether the Planner is given it.
"""
LIMIT = 2500


def _line(event: dict) -> str:
    if event['kind'] == 'planner_failure':
        return f"- 計画の失敗: {event['reason'][:250]}"
    if event['kind'] == 'final_critic_failure':
        return f"- 最終判定の失敗: {event['reason'][:250]}"
    head = f"- step {event['step']}「{event['intent'][:200]}」→ "
    if event['succeeded']:
        return head + f"成功（Observation: {event['observation'][:150]}）"
    if event['failure']:
        return head + f"実行の失敗（実行 {event['attempts']} 回）: {event['failure'][:250]}"
    return head + f"実行はできたが Critic が棄却: {event['critic_reason'][:250]}（Observation: {event['observation'][:150]}）"


def memory_of(trace: dict, stop_reason: str) -> str:
    """At most LIMIT characters: when longer, the earliest events are left out."""
    lines = [_line(event) for event in trace['events']]
    head, kept = f'止まり方: {stop_reason}\n', []
    for line in reversed(lines):
        if len(head) + sum(len(item) + 1 for item in kept) + len(line) + 1 + 10 > LIMIT:
            kept.append('- （これより前は略）')
            break
        kept.append(line)
    return head + '\n'.join(reversed(kept))


def memories_from(directory) -> dict[str, str]:
    """{Goal: memory} for each Goal an earlier run (bench/run_explore.py's --out) tried and did not answer."""
    import json
    from pathlib import Path
    directory = Path(directory).expanduser()
    memories = {}
    for line in (directory / 'exploration.jsonl').read_text().splitlines():
        if not line.strip():
            continue
        attempt = json.loads(line)
        trace = directory / f"{attempt['number']:03d}" / 'trace.json'
        if not attempt['success'] and trace.exists():
            memories[attempt['goal']] = memory_of(json.loads(trace.read_text()), attempt['stop_reason'])
    return memories
