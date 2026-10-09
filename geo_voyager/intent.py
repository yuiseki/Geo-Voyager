from dataclasses import dataclass

from .observation import Observation
from .target_ref import TargetRef


@dataclass
class Intent:
    text: str
    dataset_ids: tuple[str, ...] = ()
    service_ids: tuple[str, ...] = ()
    previous_observations: tuple[Observation, ...] = ()
    requires_context: bool = False
    # The one target this Intent is about, by its stable id when that is known. Never a list position.
    target: TargetRef | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Intent text must not be empty")
        if (not self.dataset_ids and not self.service_ids and not self.requires_context) or any(not item.strip() for item in self.dataset_ids):
            raise ValueError("Intent requires dataset_ids or service_ids with non-empty ids")
        if self.target is not None and not isinstance(self.target, TargetRef):
            raise TypeError("Intent target must be a TargetRef")
        if any(not item.strip() for item in self.service_ids):
            raise ValueError("Intent service_ids must contain non-empty ids")

    @property
    def target_name(self) -> str | None:
        """The target's name, for display."""
        return self.target.name if self.target is not None else None

    @classmethod
    def from_block(cls, block: str) -> "Intent":
        lines = block.strip().splitlines()
        if (
            len(lines) < 3
            or not lines[0].startswith("調査項目:")
            or lines[1] != "利用データセット:"
            or any(not line.startswith("  - ") for line in lines[2:])
        ):
            raise ValueError("Intent block must contain 調査項目: and 利用データセット: with a list")
        return cls(
            text=lines[0].removeprefix("調査項目:").strip(),
            dataset_ids=tuple(line.removeprefix("  - ").strip() for line in lines[2:]),
        )
