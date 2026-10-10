import json
from pathlib import Path

from .goal_executor import AdaptiveGoalExecution
from .target_ref import TargetRef


class WorldGraph:
    """What exploration found out about the world, one finding per Goal that was answered, kept with its provenance.

    A finding is the model's observation, not a fact checked against an oracle: it records the Goal, the answer (the
    last Observation of a step that succeeded), the steps that led to it, the resources used, the final Critic's
    reason and the targets made known. It is kept apart from the oracle (YuisekinGeoSPARQL) and never written into it.
    Append-only JSON lines, so a run can be read while it goes on.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def record(self, result: AdaptiveGoalExecution, *, explored_at: str | None = None) -> dict | None:
        """Add the finding of an answered Goal and return it. A Goal that was not answered adds nothing."""
        succeeded = [entry for entry in result.history if entry.succeeded and entry.observations]
        if result.stop_reason != 'done' or not result.critique.success or not succeeded:
            return None
        targets, seen = [], set()
        for entry in succeeded:
            for target in entry.targets:
                if target.key not in seen:
                    seen.add(target.key)
                    targets.append({'name': target.name, 'id_type': target.id_type, 'id_value': target.id_value})
        finding = {
            'goal': result.goal,
            'answer': succeeded[-1].observations[0].text,
            'critic_reason': result.critique.reason,
            'steps': [{'intent': entry.intent.text, 'observation': entry.observations[0].text} for entry in succeeded],
            'resources': list(dict.fromkeys(resource for entry in succeeded
                                            for resource in entry.intent.dataset_ids + entry.intent.service_ids)),
            'targets': targets,
            'explored_at': explored_at,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a') as file:
            file.write(json.dumps(finding, ensure_ascii=False) + '\n')
        return finding

    def findings(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def targets(self) -> list[TargetRef]:
        """Every target the findings made known, once per stable id, under the name it was first known by."""
        known, seen = [], set()
        for finding in self.findings():
            for item in finding['targets']:
                target = TargetRef(**item)
                if target.key not in seen:
                    seen.add(target.key)
                    known.append(target)
        return known
