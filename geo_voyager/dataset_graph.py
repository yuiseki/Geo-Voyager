from .dataset import Dataset


class DatasetGraph:
    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> None:
        self._datasets[dataset.id] = dataset

    def get(self, dataset_id: str) -> Dataset:
        return self._datasets[dataset_id]

    def all(self) -> list[Dataset]:
        return list(self._datasets.values())
