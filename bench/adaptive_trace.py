"""Turn a step-by-step Goal run into rows and text a person can read."""
from geo_voyager.goal_executor import AdaptiveGoalExecution
from geo_voyager.goal_history import FinalCriticFailure, PlannerFailure
from geo_voyager.repair_stats import error_line

OBSERVATION_SHOWN = 300


def trace_steps(result: AdaptiveGoalExecution, injected: set[int] | None = None) -> list[dict]:
    injected = injected or set()
    known: list = []
    steps = []
    for entry, execution in zip(result.history, result.executions):
        intent = entry.intent
        steps.append({
            'step': entry.step, 'intent': intent.text, 'target': intent.target_name,
            'target_ref': intent.target.to_dict() if intent.target else None,
            'resources': list(intent.service_ids + intent.dataset_ids), 'local': intent.requires_context,
            'known_before': [target.to_dict() for target in known], 'succeeded': entry.succeeded,
            'critic_success': entry.critique.success if entry.critique else None,
            'critic_reason': entry.critique.reason if entry.critique else None,
            'failure': (error_line(entry.failure) or entry.failure.message) if entry.failure else '',
            'observation': (entry.observations[0].text[:OBSERVATION_SHOWN] if entry.observations else ''),
            'attempts': len([a for a in execution.attempts if a.route == 'runtime']),
            'called_skills': list(entry.called_skills),
            'learned_skill': entry.learned_skill,
            'new_targets': [target.to_dict() for target in entry.targets], 'injected': entry.step in injected,
        })
        known.extend(target for target in entry.targets if target.key not in {k.key for k in known})
    return steps


def trace_events(result: AdaptiveGoalExecution, injected: set[int] | None = None) -> list[dict]:
    """Every event in the order it happened: steps, planner failures and final critic failures."""
    steps = {step['step']: step for step in trace_steps(result, injected)}
    events = []
    for event in result.events or result.history:
        if isinstance(event, PlannerFailure):
            events.append({'kind': 'planner_failure', 'reason': event.reason, 'reply': event.reply, 'after_step': event.after_step})
        elif isinstance(event, FinalCriticFailure):
            events.append({'kind': 'final_critic_failure', 'reason': event.reason, 'after_step': event.after_step})
        else:
            events.append({'kind': 'step', **steps[event.step]})
    return events


def _shown(ref: dict | None, name: str | None) -> str:
    if ref and ref.get('id_value') is not None:
        return f"{ref['name']} ({ref['id_type']}={ref['id_value']})"
    return name or 'なし'


def _render_step(step: dict) -> list[str]:
    status = '成功' if step['succeeded'] else ('実行失敗' if step['failure'] else 'Critic 失敗')
    lines = ['', f"step {step['step']}: {step['intent']}",
             f"- 対象: {_shown(step.get('target_ref'), step['target'])} / リソース: {', '.join(step['resources']) or 'なし（前段の集計）'}"
             + (' / 失敗を注入した step' if step['injected'] else ''),
             f"- この step の前に判明していた対象: {step['known_before'] or 'なし'}",
             f"- 結果: {status}（実行 {step['attempts']} 回）" + (f"、失敗: {step['failure']}" if step['failure'] else ''),
             f"- Critic: {step['critic_reason']}"]
    if step['observation']:
        lines.append(f"- Observation: {step['observation']}")
    if step['new_targets']:
        lines.append(f"- この step で初めて判明した対象: {step['new_targets']}")
    if step.get('called_skills'):
        lines.append(f"- 呼んだ Skill: {', '.join(step['called_skills'])}")
    if step['learned_skill']:
        lines.append(f"- 学習した Skill: {step['learned_skill']}")
    return lines


def _render_failure(event: dict) -> list[str]:
    if event['kind'] == 'planner_failure':
        lines = ['', f"計画の失敗（step {event['after_step']} の後）: {event['reason']}"]
        if event['reply']:
            lines.append('- Planner の応答: ' + ' / '.join(event['reply'].split('\n'))[:400])
        return lines
    return ['', f"Goal の最終判定が未達（step {event['after_step']} の後）: {event['reason']}"]


def render_trace(row: dict) -> str:
    lines = [f"### {row['id']}" + (' (1 回目の失敗を注入)' if row.get('injected_first_failure') else '')
             + (' (最初の件数の後に DONE を注入)' if row.get('injected_early_done') else '')
             + (' (対象: が 2 行の応答を注入)' if row.get('injected_two_targets') else '')
             + (f" (最大 {row['max_steps']} step)" if row.get('max_steps') is not None else ''),
             f"Goal: {row['goal']}", '',
             f"stop: {row['stop_reason']} / Goal の Critic: {'成功' if row['critique']['success'] else '失敗'}"
             f"（{row['critique']['reason']}）" + (f" / oracle との一致: {row['correct']}" if row.get('correct') is not None else '')]
    for event in row.get('events') or [{'kind': 'step', **step} for step in row['steps']]:
        lines += _render_step(event) if event['kind'] == 'step' else _render_failure(event)
    return '\n'.join(lines)
