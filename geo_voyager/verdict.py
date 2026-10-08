from dataclasses import dataclass


@dataclass
class Verdict:
    text: str

    def __post_init__(self) -> None:
        if self.text == "":
            raise ValueError("Verdict text must not be empty")
