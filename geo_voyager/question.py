from dataclasses import dataclass


@dataclass
class Question:
    text: str

    def __post_init__(self) -> None:
        if self.text == "":
            raise ValueError("Question text must not be empty")
