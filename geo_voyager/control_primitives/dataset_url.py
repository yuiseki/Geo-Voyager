def dataset_url(dataset_id: str) -> str:
    if dataset_id != "yuiseki/jp-admin-2026-09":
        raise ValueError("Only the administrative dataset is supported")
    return f"http://gateway:8000/datasets/{dataset_id}"
