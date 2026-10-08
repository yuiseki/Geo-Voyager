from dataclasses import dataclass


@dataclass
class Hypothesis:
    text: str

    def __post_init__(self) -> None:
        if self.text == "":
            raise ValueError("Hypothesis text must not be empty")
