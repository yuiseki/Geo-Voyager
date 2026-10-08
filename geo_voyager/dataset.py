from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    id: str
    description: str
    url: str
    license: str
    formats: tuple[str, ...]
    spatial_coverage: str
    temporal_coverage: str
    contents: tuple[str, ...]
    data_url: str | None = None

    def __post_init__(self) -> None:
        if self.id == "":
            raise ValueError("Dataset id must not be empty")
