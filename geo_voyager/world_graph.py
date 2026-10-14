import json
from pathlib import Path

from .goal_executor import AdaptiveGoalExecution
from .target_ref import TargetRef


class WorldGraph:
    """What exploration found out about the world, one finding per Goal that was answered, kept with its provenance.

    A finding is the model's observation, not a fact checked against an oracle: it records the Goal, the answer (the
    last Observation of a step that succeeded), the steps that led to it, the resources used and the targets made
    known. The final Critic's reason is not kept: no model's judgement is (ADR 0011). It is kept apart from the oracle
    (YuisekinGeoSPARQL) and never written into it.
    Append-only JSON lines, so a run can be read while it goes on.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def record(self, result: AdaptiveGoalExecution, *, explored_at: str | None = None) -> dict | None:
        """Add the finding of an answered Goal and return it. A Goal that was not answered adds nothing.
        result is the run or its log read back (geo_voyager.event_log.LoggedGoal). A Goal stops as done only when
        the final Critic found it answered."""
        if not self.answered(result):
            return None
        succeeded = [entry for entry in result.history if entry.succeeded and entry.observations]
        targets, seen = [], set()
        for entry in succeeded:
            for target in entry.targets:
                if target.key not in seen:
                    seen.add(target.key)
                    targets.append({'name': target.name, 'id_type': target.id_type, 'id_value': target.id_value})
        finding = {
            'goal': result.goal,
            'answer': succeeded[-1].observations[0].text,
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

    @staticmethod
    def answered(result) -> bool:
        """Whether the Goal has a finding: it stopped as done and a step that succeeded output something."""
        return result.stop_reason == 'done' and any(entry.succeeded and entry.observations for entry in result.history)

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
