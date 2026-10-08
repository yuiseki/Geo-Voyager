from dataclasses import dataclass


@dataclass
class Observation:
    text: str

    def __post_init__(self) -> None:
        if self.text == "":
            raise ValueError("Observation text must not be empty")
