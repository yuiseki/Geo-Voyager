from dataclasses import dataclass


@dataclass
class Intent:
    text: str

    def __post_init__(self) -> None:
        if self.text == "":
            raise ValueError("Intent text must not be empty")
