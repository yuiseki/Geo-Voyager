from dataclasses import dataclass


@dataclass
class Intent:
    text: str
    dataset_id: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Intent text must not be empty")
        if not self.dataset_id.strip():
            raise ValueError("Intent dataset_id must not be empty")

    @classmethod
    def from_block(cls, block: str) -> "Intent":
        lines = block.strip().splitlines()
        if (
            len(lines) != 2
            or not lines[0].startswith("調査項目:")
            or not lines[1].startswith("利用データセット:")
        ):
            raise ValueError("Intent block must contain 調査項目: and 利用データセット: in two lines")
        return cls(
            text=lines[0].removeprefix("調査項目:").strip(),
            dataset_id=lines[1].removeprefix("利用データセット:").strip(),
        )
