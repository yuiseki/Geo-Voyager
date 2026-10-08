from dataclasses import dataclass

from .observation import Observation


@dataclass
class Intent:
    text: str
    dataset_ids: tuple[str, ...] = ()
    service_ids: tuple[str, ...] = ()
    previous_observations: tuple[Observation, ...] = ()
    requires_context: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Intent text must not be empty")
        if (not self.dataset_ids and not self.service_ids and not self.requires_context) or any(not item.strip() for item in self.dataset_ids):
            raise ValueError("Intent requires dataset_ids or service_ids with non-empty ids")
        if any(not item.strip() for item in self.service_ids):
            raise ValueError("Intent service_ids must contain non-empty ids")

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
